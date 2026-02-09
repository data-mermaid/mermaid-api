# Demo Project Copy Process

When a user creates a demo project, MERMAID copies data from the template demo project to give them a realistic sandbox to explore. The result is that the user sees a new project with everything as it was in the original, as if they'd just been added as an admin to an existing project.

## What Gets Copied

1. **Project settings** - Name, tags, and configuration
2. **Project members** - All original project profiles (the new user is added as admin)
3. **Sites** - All survey locations
4. **Management Regimes** - Protected area designations
5. **Collect Records** - In-progress/draft survey data (with original profiles preserved)
6. **Submitted Data** - Finalized survey records including:
   - Sample Events (site visits)
   - Transects and quadrats
   - Observations (fish counts, benthic measurements, etc.)
   - Observers (original observer assignments preserved)
7. **Photo Quadrat Images** - S3 image files, thumbnails, and feature vectors are copied to the destination bucket; points and annotations are duplicated in the database

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| **Original profiles are preserved** on all copied records | User sees realistic data as it would appear in production |
| **Original observers are preserved** on all surveys | Maintains data integrity; shows realistic multi-user scenarios |
| **Site and management references are updated** in all records | Ensures data points to the user's copies, not the original |
| **All original project members are copied** | User can see how multi-user projects work |
| **New user is added as admin** | User has full control to explore and modify |
| **Photo quadrat images are copied to the test bucket** | Demo projects have TEST status, so images route to the test image bucket |

## Process Flow

```
1. Copy project shell (name, settings, is_demo=True → status=TEST)
2. Add new user as admin
3. Copy all project profiles (original members)
4. Copy sites → track old-to-new ID mapping
5. Copy management regimes → track old-to-new ID mapping
6. Determine destination image bucket from new project status (TEST → test bucket)
7. Copy collect records → update site/management references, preserve profiles
8. Copy sample events → update site/management references, preserve profiles
9. Copy transects → link to new sample events, preserve profiles
10. Copy survey methods (fish belt, benthic LIT, etc.)
11. Copy observations → preserve profiles
12. Copy observer records → preserve original observer assignments
13. For photo quadrat observations with images:
    - Copy S3 files (image + thumbnail + feature vector) from source to dest bucket
    - Create new Image record with image_bucket set to dest bucket
    - Copy points and annotations
    - Regenerate annotations CSV file
```

If any S3 copy fails, the database transaction rolls back and all successfully copied S3 files are cleaned up by `S3CopyTracker`.

## Test-Project Image Bucket Routing

Images are stored in different S3 buckets depending on whether their project has TEST status.

### How It Works

Each `Image` record has an `image_bucket` field that records which S3 bucket holds its files. This determines:

- **Which bucket to read/write from** at runtime (via per-instance storage override on Django `FieldFile` objects)
- **Which AWS credentials to use** (the test bucket may use different credentials than the production image bucket)
- **Which S3 key prefix to use** (e.g. `mermaid/` vs `mermaid-production-test/`)

### Bucket Assignment

| Scenario | Bucket | Set by |
|----------|--------|--------|
| Image uploaded to a TEST project | `IMAGE_PROCESSING_BUCKET_TEST` | `ImageViewSet.create()` |
| Image uploaded to an OPEN/LOCKED project | `IMAGE_PROCESSING_BUCKET` | `ImageViewSet.create()` |
| Demo project copy | Test bucket (demo → TEST status) | `_copy_image()` in `project.py` |
| Project status changes to/from TEST | Images move between buckets async | `Project.save()` queues SQS job |

### Credential Model

In **production**, the two buckets use different AWS credentials:

- **Production image bucket** (`coral-reef-training`): Uses `IMAGE_BUCKET_AWS_ACCESS_KEY_ID` / `IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY` (separate AWS account)
- **Test image bucket** (`mermaid-image-processing`): Uses `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (main account, same as the dev environment's bucket)

In **dev/local**, both settings point to the same bucket and same credentials, so there is no separation.

The `get_image_storage_config(bucket)` function returns the correct credentials and prefix for any given bucket. It uses the guard `bucket != IMAGE_PROCESSING_BUCKET` to distinguish test from production, ensuring that in dev (where both point to the same bucket) the production credential path is always used.

### Per-Instance Storage Override

Django `FieldFile` objects get their storage backend from the field definition at class level (`storage=select_image_storage`). To support per-image bucket routing without changing the class-level default:

1. `Image.__init__` calls `_apply_storage()` when `image_bucket` is set, overriding `field_file.storage` on each file field
2. The `pre_image_save` signal re-applies storage after `save_normalized_imagefile()` replaces `instance.image` with a new `ContentFile` (which creates a new `FieldFile` with the default storage)
3. `get_storage()` returns an `S3Storage` (or `FileSystemStorage` locally) configured for the image's specific bucket

### Image Migration on Status Change

When a project's status changes (e.g. TEST -> OPEN or OPEN -> TEST), `Project.save()` detects the change and, if the old and new buckets differ, queues an async SQS job via `queue_image_migration()`. The job:

1. Finds all images for the project (via both `CollectRecord` and `ObsBenthicPhotoQuadrat` paths)
2. For each image, moves all file fields (image, thumbnail, annotations_file, feature_vector_file) using `move_file_cross_account()` (download from source with source creds, upload to dest with dest creds)
3. Updates the `image_bucket` field on each migrated image

### Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `IMAGE_PROCESSING_BUCKET` | (required) | Primary image bucket |
| `IMAGE_PROCESSING_BUCKET_TEST` | Falls back to `IMAGE_PROCESSING_BUCKET` | Bucket for test-project images |
| `IMAGE_S3_PATH` | `mermaid/` | Key prefix in the primary bucket |
| `IMAGE_S3_PATH_TEST` | Falls back to `IMAGE_S3_PATH` | Key prefix in the test bucket |

### Management Command

**`backfill_image_bucket`** handles both the DB backfill and the S3 file moves in two phases:

1. Set `image_bucket` on all non-test images to the production bucket (DB only, fast).
2. For test-project images, move S3 files to the test bucket and set `image_bucket`.

Flags:

| Flag | Effect |
|------|--------|
| `--dry-run` | Preview what would happen without making any changes |
| `--db-only` | Only update `image_bucket` in the database; skip S3 file moves |
| `--skip-delete` | Copy files to the test bucket without deleting from the production bucket |

### Deployment Sequence

1. **Infrastructure**: Set `IMAGE_PROCESSING_BUCKET_TEST` and `IMAGE_S3_PATH_TEST` env vars on ECS. Grant cross-account bucket access.
2. **Code + schema migration** (0101): Deploy app. Adds `image_bucket` field. New images route correctly. Old images fall back to production bucket (empty `image_bucket`).
3. **Backfill**: Run manually:
   ```
   python manage.py backfill_image_bucket --dry-run          # preview
   python manage.py backfill_image_bucket --skip-delete       # copy files, set DB
   python manage.py backfill_image_bucket                     # copy + delete originals
   ```
