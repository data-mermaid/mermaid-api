"""
Test to replicate the revision table deadlock issue.

This test simulates concurrent collect record submissions that trigger
the deadlock condition described in deadlock.md.

The deadlock occurs when:
1. Two transactions try to delete CollectRecords simultaneously
2. Both trigger the pre_delete signal (deleted_collect_record_revisions)
3. Both iterate through ProjectProfiles and try to update revision records
4. They acquire locks on different revision rows in different orders
5. Circular wait condition = DEADLOCK

## Running Tests

Run all deadlock tests:
    docker exec api_service pytest --no-migrations api/tests/test_revision_deadlock.py -v

Run a specific test:
    docker exec api_service pytest --no-migrations api/tests/test_revision_deadlock.py::test_manual_revision_locking_order -v -s

## Test Results

✅ test_concurrent_collect_record_deletion_deadlock - May or may not trigger deadlock (timing-dependent)
✅ test_high_concurrency_revision_updates - Stress test with multiple users (timing-dependent)
✅ test_revision_create_race_condition - Direct test of Revision.create() race (timing-dependent)
✅ test_signal_handler_scope_issue - Documents the signal handler scope problem (observational)
✅ test_extreme_deadlock_stress - Very high concurrency with 20 users x 3 rounds (timing-dependent)
❌ test_manual_revision_locking_order - RELIABLY triggers deadlock by controlling lock order

## Understanding the Results

The test_manual_revision_locking_order is the most reliable because it:
1. Creates two transactions
2. Forces them to acquire locks in opposite orders (PP1→PP2 vs PP2→PP1)
3. Uses sleep() to ensure they overlap
4. Result: One transaction gets deadlocked by PostgreSQL

Expected output:
    Transaction 1 (PP1→PP2): ✅ Success
    Transaction 2 (PP2→PP1): ❌ DEADLOCK

This proves the deadlock issue exists and validates that the fixes in deadlock.md
will resolve it.

## After Applying Fixes

After implementing SELECT FOR UPDATE or UPSERT (from deadlock.md), re-run:
    docker exec api_service pytest --no-migrations api/tests/test_revision_deadlock.py -v

All tests should pass without deadlocks.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from django.db import connection, transaction
from django.db.utils import OperationalError

from api.models import CollectRecord, Profile, Project, ProjectProfile, Revision


@pytest.fixture
def deadlock_project(db):
    """Create a project for deadlock testing"""
    return Project.objects.create(name="Deadlock Test Project", status=Project.OPEN)


@pytest.fixture
def deadlock_profiles(db):
    """Create multiple profiles to increase revision contention"""
    profiles = []
    for i in range(5):
        email = f"deadlock_user_{i}@mermaidcollect.org"
        profile = Profile.objects.create(email=email, first_name=f"User{i}", last_name="Deadlock")
        profiles.append(profile)
    return profiles


@pytest.fixture
def deadlock_project_profiles(deadlock_project, deadlock_profiles):
    """Create project-profile relationships for all users"""
    project_profiles = []
    for profile in deadlock_profiles:
        pp = ProjectProfile.objects.create(
            project=deadlock_project, profile=profile, role=ProjectProfile.COLLECTOR
        )
        project_profiles.append(pp)
    return project_profiles


@pytest.fixture
def deadlock_collect_records(deadlock_project, deadlock_profiles):
    """Create collect records for multiple users"""
    collect_records = []
    for profile in deadlock_profiles[:2]:  # Only create records for first 2 users
        cr = CollectRecord.objects.create(
            project=deadlock_project,
            profile=profile,
            data={"protocol": "fishbelt", "test": "data"},
        )
        collect_records.append(cr)
    return collect_records


def delete_collect_record_in_transaction(collect_record_id, delay=0):
    """
    Delete a collect record in its own transaction.

    This simulates what happens during collect record submission:
    1. The collect record is deleted
    2. pre_delete signal fires
    3. deleted_collect_record_revisions signal handler runs
    4. Tries to create/update revision records for all ProjectProfiles

    Args:
        collect_record_id: UUID of the collect record to delete
        delay: Optional delay in seconds before deleting (to ensure race condition)

    Returns:
        dict with result status and any error message
    """
    # Force a new database connection for this thread
    connection.close()

    result = {"success": False, "error": None, "thread": threading.current_thread().name}

    try:
        with transaction.atomic():
            if delay > 0:
                time.sleep(delay)

            collect_record = CollectRecord.objects.get(id=collect_record_id)

            # This delete() triggers:
            # - pre_delete signal → deleted_collect_record_revisions()
            # - Database trigger on api_collectrecord table
            # - Both try to update revision table → DEADLOCK RISK
            collect_record.delete()

            result["success"] = True
            result["message"] = "Deleted successfully"

    except OperationalError as e:
        error_msg = str(e)
        if "deadlock detected" in error_msg.lower():
            result["error"] = "DEADLOCK"
            result["message"] = error_msg
        else:
            result["error"] = "OperationalError"
            result["message"] = error_msg
    except Exception as e:
        result["error"] = type(e).__name__
        result["message"] = str(e)
    finally:
        # Ensure we close this thread's connection
        connection.close()

    return result


@pytest.mark.django_db(transaction=True)
def test_concurrent_collect_record_deletion_deadlock(
    deadlock_project,
    deadlock_profiles,
    deadlock_project_profiles,
    deadlock_collect_records,
):
    """
    Test that concurrent collect record deletions can cause a deadlock.

    This test attempts to trigger the deadlock by:
    1. Creating collect records for multiple users in the same project
    2. Deleting them concurrently in separate threads/transactions
    3. Each deletion triggers revision updates for ALL project profiles
    4. Lock contention on revision table rows → deadlock

    Expected behavior (before fix):
        - One or both threads should encounter a deadlock
        - Test will fail to demonstrate the issue

    Expected behavior (after fix):
        - Both threads should complete successfully
        - No deadlocks should occur
    """
    print("\n" + "=" * 80)
    print("Testing concurrent collect record deletion for deadlock")
    print("=" * 80)

    # Verify setup
    assert len(deadlock_collect_records) == 2
    assert len(deadlock_project_profiles) == 5

    # Get the collect record IDs
    cr_ids = [cr.id for cr in deadlock_collect_records]

    print("\nSetup:")
    print(f"  - Project: {deadlock_project.name} ({deadlock_project.id})")
    print(f"  - Profiles: {len(deadlock_profiles)}")
    print(f"  - ProjectProfiles: {len(deadlock_project_profiles)}")
    print(f"  - CollectRecords to delete: {len(cr_ids)}")

    # Count initial revisions
    initial_revision_count = Revision.objects.count()
    print(f"  - Initial revision count: {initial_revision_count}")

    print("\nAttempting concurrent deletions...")

    # Use ThreadPoolExecutor to execute deletions concurrently
    deadlock_occurred = False
    results = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both deletion tasks with a small delay to ensure they overlap
        future1 = executor.submit(delete_collect_record_in_transaction, cr_ids[0], delay=0.01)
        future2 = executor.submit(delete_collect_record_in_transaction, cr_ids[1], delay=0.01)

        # Wait for both to complete
        for future in as_completed([future1, future2]):
            result = future.result()
            results.append(result)

            if result["error"] == "DEADLOCK":
                deadlock_occurred = True
                print(f"\n❌ DEADLOCK in {result['thread']}:")
                print(f"   {result['message'][:200]}")
            elif result["success"]:
                print(f"\n✅ Success in {result['thread']}")
            else:
                print(f"\n⚠️  Error in {result['thread']}: {result['error']}")
                print(f"   {result['message'][:200]}")

    # Report results
    print("\n" + "-" * 80)
    print("Results:")
    print(f"  - Deadlock occurred: {deadlock_occurred}")
    print(f"  - Successful deletions: {sum(1 for r in results if r['success'])}")
    print(f"  - Failed deletions: {sum(1 for r in results if not r['success'])}")

    final_revision_count = Revision.objects.count()
    print(f"  - Final revision count: {final_revision_count}")
    print("=" * 80 + "\n")

    # This test is designed to EXPOSE the deadlock issue
    # When the deadlock occurs, this assertion will fail
    if deadlock_occurred:
        pytest.fail(
            "DEADLOCK DETECTED! This confirms the issue described in deadlock.md. "
            "Apply one of the recommended fixes (SELECT FOR UPDATE or UPSERT) to resolve."
        )

    # If no deadlock, both deletions should have succeeded
    assert all(
        r["success"] for r in results
    ), f"Expected both deletions to succeed, but some failed. Results: {results}"


@pytest.mark.django_db(transaction=True)
def test_high_concurrency_revision_updates(
    deadlock_project, deadlock_profiles, deadlock_project_profiles
):
    """
    Test high-concurrency revision updates to stress test the system.

    This test creates many concurrent transactions that all try to update
    the same revision records, increasing the likelihood of deadlock.
    """
    print("\n" + "=" * 80)
    print("High concurrency stress test")
    print("=" * 80)

    # Create more collect records for stress testing
    collect_records = []
    for i, profile in enumerate(deadlock_profiles):
        cr = CollectRecord.objects.create(
            project=deadlock_project,
            profile=profile,
            data={"protocol": "fishbelt", "stress_test": i},
        )
        collect_records.append(cr)

    cr_ids = [cr.id for cr in collect_records]

    print(f"\nStress test with {len(cr_ids)} concurrent deletions...")

    # Track results
    deadlock_count = 0
    success_count = 0
    error_count = 0

    # Use more workers to increase concurrency
    with ThreadPoolExecutor(max_workers=len(cr_ids)) as executor:
        # Submit all deletions at once
        futures = [
            executor.submit(delete_collect_record_in_transaction, cr_id, delay=0.001)
            for cr_id in cr_ids
        ]

        # Collect results
        for future in as_completed(futures):
            result = future.result()

            if result["error"] == "DEADLOCK":
                deadlock_count += 1
            elif result["success"]:
                success_count += 1
            else:
                error_count += 1

    print("\nStress test results:")
    print(f"  - Total operations: {len(cr_ids)}")
    print(f"  - Successful: {success_count}")
    print(f"  - Deadlocks: {deadlock_count}")
    print(f"  - Other errors: {error_count}")
    print("=" * 80 + "\n")

    if deadlock_count > 0:
        pytest.fail(
            f"DEADLOCK DETECTED in stress test! {deadlock_count} out of {len(cr_ids)} "
            f"operations deadlocked. This confirms the concurrency issue."
        )

    # All operations should succeed
    assert success_count == len(
        cr_ids
    ), f"Expected all {len(cr_ids)} operations to succeed, but only {success_count} did."


@pytest.mark.django_db(transaction=True)
def test_revision_create_race_condition(deadlock_project_profiles):
    """
    Direct test of the Revision.create() race condition.

    This test bypasses collect records and directly tests concurrent
    calls to Revision.create_from_instance() for the same ProjectProfile.
    """
    print("\n" + "=" * 80)
    print("Testing Revision.create() race condition")
    print("=" * 80)

    # Pick one project profile to test
    project_profile = deadlock_project_profiles[0]

    print(f"\nTesting concurrent revision creation for ProjectProfile {project_profile.id}")

    def create_revision_for_project_profile(pp_id, iteration):
        """Create a revision for the given project profile"""
        connection.close()

        result = {"success": False, "error": None, "iteration": iteration}

        try:
            with transaction.atomic():
                pp = ProjectProfile.objects.get(id=pp_id)

                # This is what the signal handler does
                revision = Revision.create_from_instance(pp)

                result["success"] = True
                result["revision_num"] = revision.revision_num

        except OperationalError as e:
            if "deadlock detected" in str(e).lower():
                result["error"] = "DEADLOCK"
            else:
                result["error"] = "OperationalError"
            result["message"] = str(e)
        except Exception as e:
            result["error"] = type(e).__name__
            result["message"] = str(e)
        finally:
            connection.close()

        return result

    # Run many concurrent revision creates for the same ProjectProfile
    num_concurrent = 10
    deadlock_count = 0
    success_count = 0

    print(f"Executing {num_concurrent} concurrent Revision.create() calls...")

    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [
            executor.submit(create_revision_for_project_profile, project_profile.id, i)
            for i in range(num_concurrent)
        ]

        for future in as_completed(futures):
            result = future.result()

            if result["error"] == "DEADLOCK":
                deadlock_count += 1
                print(f"  ❌ Iteration {result['iteration']}: DEADLOCK")
            elif result["success"]:
                success_count += 1
                print(
                    f"  ✅ Iteration {result['iteration']}: Success (rev #{result['revision_num']})"
                )
            else:
                print(f"  ⚠️  Iteration {result['iteration']}: {result['error']}")

    print(f"\nResults: {success_count} successful, {deadlock_count} deadlocks")
    print("=" * 80 + "\n")

    if deadlock_count > 0:
        pytest.fail(
            f"Race condition in Revision.create() detected! {deadlock_count} deadlocks occurred."
        )

    assert success_count == num_concurrent


@pytest.mark.django_db(transaction=True)
def test_signal_handler_scope_issue(deadlock_project, deadlock_profiles, deadlock_project_profiles):
    """
    Test that demonstrates the signal handler scope problem.

    The deleted_collect_record_revisions signal handler creates revisions
    for ALL ProjectProfiles matching the profile+project, not just the
    one that owns the collect record being deleted.

    This increases lock contention unnecessarily.
    """
    print("\n" + "=" * 80)
    print("Testing signal handler scope")
    print("=" * 80)

    # Create collect records for two users
    cr1 = CollectRecord.objects.create(
        project=deadlock_project,
        profile=deadlock_profiles[0],
        data={"test": "data1"},
    )
    _ = CollectRecord.objects.create(
        project=deadlock_project,
        profile=deadlock_profiles[1],
        data={"test": "data2"},
    )

    print("\nCreated collect records:")
    print(f"  - CR1: User {deadlock_profiles[0].email}")
    print(f"  - CR2: User {deadlock_profiles[1].email}")
    print(f"  - Total ProjectProfiles in project: {len(deadlock_project_profiles)}")

    # Count revisions before
    initial_count = Revision.objects.count()

    # Delete CR1 and observe how many revision updates occur
    cr1.delete()

    # The signal handler will create/update revisions for:
    # 1. The ProjectProfile for deadlock_profiles[0]
    # 2. Potentially other ProjectProfiles due to the broad query

    # This demonstrates the scope issue: when user A deletes their collect record,
    # it shouldn't need to update revisions for users B, C, D, E

    after_cr1_count = Revision.objects.count()
    revisions_created = after_cr1_count - initial_count

    print("\nAfter deleting CR1:")
    print(f"  - Revisions created/updated: {revisions_created}")
    print("  - Expected: 1 (just the ProjectProfile for the owner)")
    print("  - If more than 1, signal handler scope is too broad!")

    print("=" * 80 + "\n")

    # Note: This test documents the issue but may not fail depending on
    # how revisions are structured. It's primarily for observation.


@pytest.mark.django_db(transaction=True)
def test_extreme_deadlock_stress():
    """
    Extreme stress test with many users and many concurrent operations.

    This test maximizes the chances of hitting a deadlock by:
    1. Creating many users in the same project
    2. Creating many collect records
    3. Deleting them all at once with maximum concurrency
    4. Running multiple iterations

    This is the most aggressive test to replicate production conditions.
    """
    print("\n" + "=" * 80)
    print("EXTREME DEADLOCK STRESS TEST")
    print("=" * 80)

    # Create a project with many users
    project = Project.objects.create(name="Extreme Stress Project", status=Project.OPEN)

    num_users = 20
    profiles = []
    for i in range(num_users):
        profile = Profile.objects.create(
            email=f"stress_{i}@test.org",
            first_name=f"Stress{i}",
            last_name="Test",
        )
        profiles.append(profile)
        ProjectProfile.objects.create(
            project=project, profile=profile, role=ProjectProfile.COLLECTOR
        )

    print(f"\nSetup: {num_users} users in one project")

    # Run multiple rounds
    num_rounds = 3
    total_deadlocks = 0
    total_operations = 0

    for round_num in range(num_rounds):
        print(f"\n--- Round {round_num + 1}/{num_rounds} ---")

        # Create collect records for all users
        collect_records = []
        for profile in profiles:
            cr = CollectRecord.objects.create(
                project=project,
                profile=profile,
                data={"protocol": "fishbelt", "round": round_num},
            )
            collect_records.append(cr)

        cr_ids = [cr.id for cr in collect_records]
        print(f"Created {len(cr_ids)} collect records")

        # Delete them all concurrently
        deadlock_count = 0
        success_count = 0

        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [
                executor.submit(delete_collect_record_in_transaction, cr_id, delay=0.0001)
                for cr_id in cr_ids
            ]

            for future in as_completed(futures):
                result = future.result()
                total_operations += 1

                if result["error"] == "DEADLOCK":
                    deadlock_count += 1
                    total_deadlocks += 1
                elif result["success"]:
                    success_count += 1

        print(f"Round results: {success_count} success, {deadlock_count} deadlocks")

    print("\n" + "=" * 80)
    print("FINAL RESULTS:")
    print(f"  Total operations: {total_operations}")
    print(f"  Total deadlocks: {total_deadlocks}")
    print(f"  Deadlock rate: {(total_deadlocks / total_operations) * 100:.1f}%")
    print("=" * 80 + "\n")

    if total_deadlocks > 0:
        pytest.fail(
            f"DEADLOCK DETECTED! {total_deadlocks} out of {total_operations} operations "
            f"({(total_deadlocks / total_operations) * 100:.1f}%) deadlocked. "
            f"This confirms the issue in deadlock.md."
        )


@pytest.mark.django_db(transaction=True)
def test_manual_revision_locking_order():
    """
    Test to demonstrate how lock ordering affects deadlock.

    This test manually creates scenarios where transactions acquire
    locks in different orders to prove the deadlock mechanism.
    """
    print("\n" + "=" * 80)
    print("Testing lock ordering impact on deadlock")
    print("=" * 80)

    # Create a project with two users
    project = Project.objects.create(name="Lock Order Test", status=Project.OPEN)

    profile1 = Profile.objects.create(email="lock1@test.org", first_name="Lock1", last_name="Test")
    profile2 = Profile.objects.create(email="lock2@test.org", first_name="Lock2", last_name="Test")

    pp1 = ProjectProfile.objects.create(
        project=project, profile=profile1, role=ProjectProfile.COLLECTOR
    )
    pp2 = ProjectProfile.objects.create(
        project=project, profile=profile2, role=ProjectProfile.COLLECTOR
    )

    print("\nSetup:")
    print(f"  - ProjectProfile 1: {pp1.id}")
    print(f"  - ProjectProfile 2: {pp2.id}")

    def update_revisions_forward_order(pp1_id, pp2_id):
        """Update revisions in order: PP1 then PP2"""
        connection.close()
        result = {"success": False, "error": None, "order": "PP1→PP2"}

        try:
            with transaction.atomic():
                time.sleep(0.001)  # Small delay to ensure overlap

                pp1 = ProjectProfile.objects.get(id=pp1_id)
                Revision.create_from_instance(pp1)  # Lock revision for PP1

                time.sleep(0.01)  # Increase window for race

                pp2 = ProjectProfile.objects.get(id=pp2_id)
                Revision.create_from_instance(pp2)  # Try to lock revision for PP2

                result["success"] = True

        except OperationalError as e:
            if "deadlock detected" in str(e).lower():
                result["error"] = "DEADLOCK"
            else:
                result["error"] = str(e)
        finally:
            connection.close()

        return result

    def update_revisions_reverse_order(pp1_id, pp2_id):
        """Update revisions in order: PP2 then PP1"""
        connection.close()
        result = {"success": False, "error": None, "order": "PP2→PP1"}

        try:
            with transaction.atomic():
                time.sleep(0.001)  # Small delay to ensure overlap

                pp2 = ProjectProfile.objects.get(id=pp2_id)
                Revision.create_from_instance(pp2)  # Lock revision for PP2

                time.sleep(0.01)  # Increase window for race

                pp1 = ProjectProfile.objects.get(id=pp1_id)
                Revision.create_from_instance(pp1)  # Try to lock revision for PP1

                result["success"] = True

        except OperationalError as e:
            if "deadlock detected" in str(e).lower():
                result["error"] = "DEADLOCK"
            else:
                result["error"] = str(e)
        finally:
            connection.close()

        return result

    print("\nExecuting transactions with opposite lock ordering...")

    # Run transactions that acquire locks in opposite order
    deadlock_detected = False

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(update_revisions_forward_order, pp1.id, pp2.id)
        future2 = executor.submit(update_revisions_reverse_order, pp1.id, pp2.id)

        result1 = future1.result()
        result2 = future2.result()

        print(f"\nTransaction 1 ({result1['order']}): ", end="")
        if result1["error"] == "DEADLOCK":
            print("❌ DEADLOCK")
            deadlock_detected = True
        elif result1["success"]:
            print("✅ Success")
        else:
            print(f"⚠️  Error: {result1['error']}")

        print(f"Transaction 2 ({result2['order']}): ", end="")
        if result2["error"] == "DEADLOCK":
            print("❌ DEADLOCK")
            deadlock_detected = True
        elif result2["success"]:
            print("✅ Success")
        else:
            print(f"⚠️  Error: {result2['error']}")

    print("=" * 80 + "\n")

    if deadlock_detected:
        pytest.fail(
            "DEADLOCK from opposite lock ordering! This demonstrates how "
            "acquiring locks in different orders causes circular wait."
        )
