# Database Deadlock Analysis - Revision System

## Executive Summary

The MERMAID API is experiencing database deadlocks in the `revision` table during concurrent collect record submissions. The deadlock occurs when two processes try to update the same `revision` records but acquire locks in different orders, resulting in a circular wait condition.

## Error Details

**Error Type**: `OperationalError: deadlock detected`

**Location**: `api/models/revisions.py:82` in `Revision.create()` method

**Context**: During `collect_record.delete()` in `api/submission/utils.py:122`

**Stacktrace Pattern**:
```
Process A waits for ShareLock on transaction X; blocked by process B
Process B waits for ShareLock on transaction Y; blocked by process A
```

**Table**: `revision` (specifically updating tuple in relation "revision")

## Root Cause Analysis

### 1. **Race Condition in Revision Creation**

The deadlock occurs in the `Revision.create()` method (`src/api/models/revisions.py:43-88`), specifically during the update operation at line 82:

```python
revision = Revision.objects.get_or_none(
    table_name=table_name,
    record_id=record_id,
    related_to_profile_id=related_to_profile_id,
)
# ...
revision.save()  # Line 82 - Deadlock occurs here
```

**Problem**: When two concurrent requests try to update the same revision record, they may:
1. Both read the same revision record (no lock yet)
2. Both acquire sequence numbers from `revision_seq_num`
3. Both try to UPDATE the same row, but in different transaction orders

### 2. **Signal Handler Cascade**

When a `CollectRecord` is deleted during submission (`api/submission/utils.py:122`), it triggers a cascade of signal handlers:

```python
collect_record.delete()  # Line 122
↓
pre_delete signal → deleted_collect_record_revisions (api/signals/revision.py:88-90)
↓
_create_project_profile_revisions (line 57-59)
↓
Loops through ALL ProjectProfile records for this profile+project
↓
Revision.create_from_instance(project_profile) for EACH
↓
Revision.create() → revision.save() [DEADLOCK HERE]
```

**Problem**: The signal handler at `api/signals/revision.py:89-90` creates revision records for ALL project profiles matching the user and project:

```python
def _create_project_profile_revisions(query_kwargs):
    for project_profile in ProjectProfile.objects.filter(**query_kwargs):
        Revision.create_from_instance(project_profile)
```

When two users submit collect records concurrently for the same project, both try to update overlapping `revision` records.

### 3. **Lack of Row-Level Locking**

The current implementation uses `get_or_none()` followed by `save()`, which doesn't acquire a lock during the read:

```python
revision = Revision.objects.get_or_none(  # No lock acquired
    table_name=table_name,
    record_id=record_id,
    related_to_profile_id=related_to_profile_id,
)
if revision is None:
    return Revision.objects.create(...)  # INSERT

# UPDATE path (no lock held from the read)
revision.revision_num = revision_num
revision.save()  # Tries to acquire lock here - DEADLOCK RISK
```

### 4. **Database Triggers Add Complexity**

The revision system has database triggers (`write_revision()` function in `revisions.py:188-261`) that automatically create/update revisions on many tables. This means:
- Database triggers fire AFTER INSERT/UPDATE/DELETE
- Django signals also fire on these operations
- Both are trying to update the `revision` table simultaneously
- Different code paths can create lock acquisition order issues

### 5. **Unique Constraint Contention**

The `revision` table has a unique constraint:
```sql
"revision_table_name_record_id_rel_bfa7fba5_uniq" UNIQUE CONSTRAINT,
btree (table_name, record_id, related_to_profile_id)
```

When multiple processes try to UPDATE the same record (identified by this composite key), they compete for locks on:
1. The primary key index
2. The unique constraint index
3. The row itself

If processes acquire these locks in different orders, a deadlock occurs.

## Deadlock Scenario Visualization

```
Time  Process A (User 1)                    Process B (User 2)
----  --------------------------------       --------------------------------
T1    Begin transaction                      Begin transaction
T2    Delete CollectRecord                   Delete CollectRecord
T3    Signal: deleted_collect_record_revisions
                                             Signal: deleted_collect_record_revisions
T4    Query ProjectProfile (profile=U1, project=P1)
                                             Query ProjectProfile (profile=U2, project=P1)
T5    Revision.create() for ProjectProfile A
      - Get revision record A
      - Get nextval('revision_seq_num')
                                             Revision.create() for ProjectProfile B
                                             - Get revision record B
                                             - Get nextval('revision_seq_num')
T6    Try to UPDATE revision A
      [Acquires lock on revision A]
                                             Try to UPDATE revision B
                                             [Acquires lock on revision B]
T7    Revision.create() for ProjectProfile B
      Try to UPDATE revision B
      [WAITS for Process B's lock on B]
                                             Revision.create() for ProjectProfile A
                                             Try to UPDATE revision A
                                             [WAITS for Process A's lock on A]
T8    ❌ DEADLOCK DETECTED ❌
```

## Affected Code Paths

1. **Primary Path**: `/v1/projects/{id}/collectrecords/submit/`
   - `api/resources/collect_record.py:164` → `submit_collect_records()`
   - `api/submission/utils.py:320` → `write_collect_record()`
   - `api/submission/utils.py:122` → `collect_record.delete()`
   - `api/signals/revision.py:89` → `deleted_collect_record_revisions()`
   - `api/models/revisions.py:82` → `revision.save()` ❌ DEADLOCK

2. **Concurrent Triggers**:
   - Database trigger `api_collectrecord_trigger` on `api_collectrecord` table
   - Django signal `pre_delete` on `CollectRecord`
   - Both trying to update `revision` table

## Potential Solutions

### Solution 1: Use SELECT FOR UPDATE (Recommended - High Priority)

**Description**: Acquire an exclusive row lock when reading the revision record, preventing concurrent updates.

**Implementation**:
```python
# In src/api/models/revisions.py, modify the create() method:

@classmethod
def create(cls, table_name, record_id, project_id=None, profile_id=None,
           deleted=False, related_to_profile_id=None):
    from django.db import transaction

    cursor = connection.cursor()
    try:
        sql = "SELECT nextval('revision_seq_num');"
        cursor.execute(sql)
        revision_num = cursor.fetchone()[0]

        # Use select_for_update() to acquire an exclusive lock
        with transaction.atomic():
            revision = Revision.objects.select_for_update().get_or_none(
                table_name=table_name,
                record_id=record_id,
                related_to_profile_id=related_to_profile_id,
            )

            if revision is None:
                return Revision.objects.create(
                    table_name=table_name,
                    record_id=record_id,
                    project_id=project_id,
                    profile_id=profile_id,
                    updated_on=timezone.now(),
                    deleted=deleted,
                    revision_num=revision_num,
                    related_to_profile_id=related_to_profile_id,
                )

            # Lock is already held from select_for_update()
            revision.project_id = project_id
            revision.profile_id = profile_id
            revision.updated_on = timezone.now()
            revision.deleted = deleted
            revision.revision_num = revision_num
            revision.related_to_profile_id = related_to_profile_id
            revision.save()

            return revision
    finally:
        if cursor:
            cursor.close()
```

**Pros**:
- Prevents concurrent updates to the same revision record
- Maintains existing API behavior
- Standard Django ORM pattern
- Blocks until lock is available (no deadlock, just queuing)

**Cons**:
- Slight performance impact (locks are held longer)
- May increase transaction duration

**Risk**: Low
**Effort**: Low
**Impact**: High

---

### Solution 2: Use PostgreSQL UPSERT with ON CONFLICT (Recommended - Medium Priority)

**Description**: Replace the get-or-create pattern with a single atomic `INSERT ... ON CONFLICT DO UPDATE` statement.

**Implementation**:
```python
# In src/api/models/revisions.py:

@classmethod
def create(cls, table_name, record_id, project_id=None, profile_id=None,
           deleted=False, related_to_profile_id=None):
    from django.db import connection

    cursor = connection.cursor()
    try:
        sql = "SELECT nextval('revision_seq_num');"
        cursor.execute(sql)
        revision_num = cursor.fetchone()[0]

        updated_on = timezone.now()

        # Use raw SQL for atomic upsert
        upsert_sql = """
            INSERT INTO revision (
                table_name, record_id, project_id, profile_id,
                revision_num, updated_on, deleted, related_to_profile_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (table_name, record_id, related_to_profile_id)
            DO UPDATE SET
                project_id = EXCLUDED.project_id,
                profile_id = EXCLUDED.profile_id,
                revision_num = EXCLUDED.revision_num,
                updated_on = EXCLUDED.updated_on,
                deleted = EXCLUDED.deleted
            RETURNING id;
        """

        cursor.execute(upsert_sql, [
            table_name, record_id, project_id, profile_id,
            revision_num, updated_on, deleted, related_to_profile_id
        ])

        revision_id = cursor.fetchone()[0]
        return cls.objects.get(id=revision_id)

    finally:
        if cursor:
            cursor.close()
```

**Pros**:
- Single atomic operation (no race condition possible)
- Better performance (one query instead of two)
- PostgreSQL handles concurrency internally
- Eliminates deadlock risk entirely

**Cons**:
- Uses raw SQL (less portable, but project is PostgreSQL-only)
- Need to test thoroughly with existing triggers

**Risk**: Medium (requires testing with database triggers)
**Effort**: Medium
**Impact**: High

---

### Solution 3: Reduce Signal Handler Scope (Recommended - High Priority)

**Description**: The signal handler creates revisions for ALL project profiles when a collect record is deleted. This is overly broad and causes unnecessary contention.

**Current Code** (`api/signals/revision.py:88-90`):
```python
@receiver(pre_delete, sender=CollectRecord)
def deleted_collect_record_revisions(sender, instance, *args, **kwargs):
    _create_project_profile_revisions({
        "profile": instance.profile,
        "project": instance.project
    })
```

**Problem**: This creates revision records for ALL users in the project, not just the user deleting their collect record.

**Proposed Fix**:
```python
@receiver(pre_delete, sender=CollectRecord)
def deleted_collect_record_revisions(sender, instance, *args, **kwargs):
    # Only create revision for the specific project-profile relationship
    try:
        project_profile = ProjectProfile.objects.get(
            profile=instance.profile,
            project=instance.project
        )
        Revision.create_from_instance(project_profile)
    except ProjectProfile.DoesNotExist:
        pass  # Collect record exists but user is no longer in project
```

**Pros**:
- Reduces number of revision records created
- Significantly reduces lock contention
- More accurate (only records change for affected user)
- Simple change

**Cons**:
- Need to verify this doesn't break sync logic
- May need to adjust related signal handlers similarly

**Risk**: Medium (need to test sync behavior)
**Effort**: Low
**Impact**: High

---

### Solution 4: Implement Consistent Lock Ordering

**Description**: Ensure all code paths acquire locks in the same order to prevent circular waits.

**Implementation**:
```python
# In api/signals/revision.py, modify _create_project_profile_revisions:

def _create_project_profile_revisions(query_kwargs):
    # Always process in a consistent order (e.g., by ID)
    project_profiles = ProjectProfile.objects.filter(**query_kwargs).order_by('id')
    for project_profile in project_profiles:
        Revision.create_from_instance(project_profile)
```

**Pros**:
- Standard deadlock prevention technique
- Minimal code changes

**Cons**:
- Doesn't eliminate the deadlock risk if other code paths don't follow the same ordering
- Hard to enforce across the entire codebase
- Database triggers may not respect this ordering

**Risk**: Medium
**Effort**: Low
**Impact**: Medium

---

### Solution 5: Use Advisory Locks (Alternative)

**Description**: Use PostgreSQL advisory locks to serialize access to revision creation for specific entities.

**Implementation**:
```python
from django.db import connection

@classmethod
def create(cls, table_name, record_id, project_id=None, profile_id=None,
           deleted=False, related_to_profile_id=None):
    cursor = connection.cursor()
    try:
        # Generate a numeric hash for the advisory lock key
        import hashlib
        lock_key = int(hashlib.md5(
            f"{table_name}:{record_id}:{related_to_profile_id}".encode()
        ).hexdigest()[:15], 16)

        # Acquire advisory lock
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_key])

        # Rest of the create logic...
        sql = "SELECT nextval('revision_seq_num');"
        cursor.execute(sql)
        revision_num = cursor.fetchone()[0]

        # ... (existing code)
    finally:
        if cursor:
            cursor.close()
        # Advisory lock is automatically released at transaction end
```

**Pros**:
- Very fine-grained control
- Doesn't require table-level locking
- Can be scoped to specific revision keys

**Cons**:
- More complex
- Advisory locks are PostgreSQL-specific
- Need to carefully manage lock keys

**Risk**: Medium
**Effort**: Medium
**Impact**: High

---

### Solution 6: Retry Logic with Exponential Backoff (Tactical - Low Priority)

**Description**: Catch deadlock exceptions and retry the operation after a brief delay.

**Implementation**:
```python
# In api/submission/utils.py:

from django.db.utils import OperationalError
import time
import random

def write_collect_record(collect_record, request, dry_run=False, max_retries=3):
    status = None
    result = None
    context = {"request": request}
    writer = get_writer(collect_record, context)

    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                sid = transaction.savepoint()
                try:
                    writer.write()
                    status = SUCCESS_STATUS
                except (ValidationError, DJValidationError) as ve:
                    result = format_serializer_errors(ve)
                    status = VALIDATION_ERROR_STATUS
                except Exception as err:
                    logger.exception("write_collect_record: {}".format(
                        getattr(collect_record, "id")
                    ))
                    result = format_exception_errors(err)
                    status = ERROR_STATUS
                finally:
                    if dry_run is True or status != SUCCESS_STATUS:
                        transaction.savepoint_rollback(sid)
                    else:
                        create_audit_record(
                            request.user.profile,
                            AuditRecord.SUBMIT_RECORD_EVENT_TYPE,
                            collect_record
                        )
                        collect_record_id = collect_record.id
                        collect_record.delete()
                        transaction.savepoint_commit(sid)

                        collect_record.id = collect_record_id
                        post_submit.send(
                            sender=collect_record.__class__,
                            instance=collect_record,
                        )

                        add_project_to_queue(collect_record.project_id)

            # Success - exit retry loop
            break

        except OperationalError as e:
            if "deadlock detected" in str(e) and attempt < max_retries - 1:
                # Exponential backoff with jitter
                delay = (2 ** attempt) * 0.1 + random.uniform(0, 0.1)
                logger.warning(
                    f"Deadlock detected, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
            else:
                # Final attempt failed or not a deadlock
                raise

    return status, result
```

**Pros**:
- Handles deadlocks gracefully
- Doesn't require changing the core logic
- Can be applied as a quick fix while working on root cause

**Cons**:
- Doesn't fix the root cause
- May hide the underlying issue
- Adds latency on retry
- Users may experience slower response times

**Risk**: Low
**Effort**: Low
**Impact**: Low (symptomatic treatment only)

---

### Solution 7: Batch Revision Updates (Long-term)

**Description**: Instead of creating/updating revisions immediately, batch them and process in a background worker.

**Implementation**:
```python
# Add a pending revisions queue
from django.core.cache import cache
import json

def queue_revision_update(table_name, record_id, project_id=None,
                         profile_id=None, deleted=False,
                         related_to_profile_id=None):
    key = f"pending_revisions:{project_id}"
    pending = cache.get(key, [])
    pending.append({
        'table_name': table_name,
        'record_id': record_id,
        'project_id': project_id,
        'profile_id': profile_id,
        'deleted': deleted,
        'related_to_profile_id': related_to_profile_id,
    })
    cache.set(key, pending, timeout=300)

# Background worker processes batches
def process_pending_revisions():
    # Process batches in order, with proper locking
    pass
```

**Pros**:
- Completely eliminates real-time contention
- Can optimize batch processing
- Better performance under high load

**Cons**:
- Significant architectural change
- Eventual consistency model (revisions not immediately available)
- May break sync logic if it depends on immediate revision updates
- Complex to implement and test

**Risk**: High
**Effort**: High
**Impact**: High (but requires extensive testing)

---

## Recommended Implementation Plan

### Phase 1: Immediate Fixes (Deploy ASAP)

1. **Implement Solution 3**: Reduce signal handler scope
   - File: `src/api/signals/revision.py:88-90`
   - Change `_create_project_profile_revisions()` to only affect the specific user
   - **Est. time**: 2 hours (including testing)
   - **Risk**: Medium

2. **Implement Solution 6**: Add retry logic
   - File: `src/api/submission/utils.py:97-132`
   - Add deadlock retry with exponential backoff
   - **Est. time**: 2 hours
   - **Risk**: Low

### Phase 2: Core Fix (Deploy within 1 week)

3. **Implement Solution 1**: Use SELECT FOR UPDATE
   - File: `src/api/models/revisions.py:43-88`
   - Add `select_for_update()` to prevent race conditions
   - **Est. time**: 4 hours (including testing)
   - **Risk**: Low

### Phase 3: Optimization (Deploy within 2 weeks)

4. **Implement Solution 2**: PostgreSQL UPSERT
   - File: `src/api/models/revisions.py:43-88`
   - Replace with atomic `INSERT ... ON CONFLICT DO UPDATE`
   - **Est. time**: 8 hours (including extensive testing with triggers)
   - **Risk**: Medium

5. **Implement Solution 4**: Consistent lock ordering
   - Files: All signal handlers in `src/api/signals/revision.py`
   - Add `.order_by('id')` to all revision queries
   - **Est. time**: 2 hours
   - **Risk**: Low

### Phase 4: Monitoring (Ongoing)

6. **Add monitoring and alerting**:
   - Log all deadlock occurrences with context
   - Add metrics for revision creation times
   - Alert on deadlock rate > threshold

## Testing Strategy

### Unit Tests

1. **Test concurrent revision creation**:
   ```python
   from threading import Thread

   def test_concurrent_revision_creation():
       # Create two threads that simultaneously create revisions
       # for the same project_profile
       # Should not deadlock
   ```

2. **Test collect record submission under load**:
   ```python
   def test_concurrent_collect_record_submission():
       # Multiple users submit collect records to same project
       # Should complete without deadlock
   ```

### Integration Tests

1. **Load test**: Use locust or similar to simulate 10+ concurrent submissions
2. **Database monitoring**: Enable PostgreSQL query logging to observe lock waits

### Rollback Plan

- Keep the retry logic (Solution 6) even after implementing core fixes
- Monitor deadlock metrics closely after each deployment
- Be prepared to roll back to previous version if deadlock rate increases

## Monitoring Queries

```sql
-- Check for current lock waits
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;

-- Check revision table statistics
SELECT
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE tablename = 'revision';

-- Check for deadlocks in PostgreSQL logs
-- (Enable deadlock_timeout and log_lock_waits in postgresql.conf)
```

## Additional Considerations

### Database Configuration

Consider adjusting PostgreSQL settings:

```conf
# postgresql.conf
deadlock_timeout = 1s          # How long to wait before checking for deadlock
log_lock_waits = on            # Log slow lock acquisition
lock_timeout = 30s             # Fail query if lock not acquired in 30s
statement_timeout = 60s        # Overall query timeout
```

### Index Optimization

The `revision` table has good indexes, but consider:
- Monitor index bloat
- Regular `VACUUM ANALYZE` on the revision table
- Consider partitioning if revision table grows very large

### Application-Level Connection Pooling

Ensure Django connection pooling is properly configured:
```python
# settings.py
DATABASES = {
    'default': {
        # ...
        'CONN_MAX_AGE': 600,  # Reuse connections for 10 minutes
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

## Related Issues

- Signal cascade on ProjectProfile changes may have similar issues
- Database trigger `write_revision()` may conflict with Django signals
- Consider reviewing all uses of `select_for_update()` in the codebase

## References

- Django transaction documentation: https://docs.djangoproject.com/en/3.2/topics/db/transactions/
- PostgreSQL deadlock detection: https://www.postgresql.org/docs/current/explicit-locking.html
- Django select_for_update: https://docs.djangoproject.com/en/3.2/ref/models/querysets/#select-for-update
- PostgreSQL UPSERT: https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT

## Appendix: Deadlock Detection in PostgreSQL

PostgreSQL uses a deadlock detection algorithm that periodically checks for cycles in the lock-wait graph. When detected:
1. PostgreSQL chooses one transaction as the "victim"
2. Rolls back that transaction
3. Returns the deadlock error to the application
4. The other transaction can proceed

The current deadlock is occurring because:
- Two transactions are updating different revision rows
- Each transaction acquires locks in a different order
- They end up waiting for each other's locks (circular dependency)

The fix is to either:
- Ensure consistent lock ordering (Solution 4)
- Use atomic operations that don't require multiple steps (Solution 2)
- Acquire exclusive locks early (Solution 1)
- Serialize access using advisory locks (Solution 5)
