NEW_DATA_BUCKET_PATH = "data/{manifest_id}/{product_id}/{dataset_id}/{file_name}"
NEW_MANIFESTS_PREFIX = "manifests/new/"
NEW_MANIFESTS_PATH = f"{NEW_MANIFESTS_PREFIX}{{manifest_id}}.json"
IN_PROGRESS_MANIFESTS_PREFIX = "manifests/in-progress/"
IN_PROGRESS_MANIFESTS_PATH = f"{IN_PROGRESS_MANIFESTS_PREFIX}{{manifest_id}}.json"
FAILED_MANIFESTS_PREFIX = "manifests/failed/"
FAILED_INVALID_SCHEMA_MANIFESTS_PATH = (
    f"{FAILED_MANIFESTS_PREFIX}invalid-manifests/{{file_name}}"
)
FAILED_MANIFESTS_PATH = (
    f"{FAILED_MANIFESTS_PREFIX}{{product_id}}/{{dataset_id}}/{{manifest_id}}.json"
)
DONE_MANIFESTS_PREFIX = "manifests/done/"
DONE_MANIFESTS_PATH = (
    f"{DONE_MANIFESTS_PREFIX}{{product_id}}/{{dataset_id}}/{{manifest_id}}.json"
)


PUSHING_ENTITIES_PATH = "pushing_entities.yml"

MAX_CONCURRENT_UPLOADS = 5
CHUNK_CONCURRENCY = 6
DEFAULT_CHUNK_SIZE_MB = 16
