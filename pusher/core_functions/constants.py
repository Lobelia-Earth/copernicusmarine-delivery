NEW_DATA_BUCKET_PATH = "data/{manifest_id}/{product_id}/{dataset_id}/{file_name}"

NEW_MANIFESTS_PREFIX = "manifests/new/"
NEW_MANIFESTS_PATH = f"{NEW_MANIFESTS_PREFIX}{{manifest_id}}.json"
IN_PROGRESS_MANIFESTS_PREFIX = "manifests/in-progress/"
IN_PROGRESS_MANIFESTS_PATH = f"{IN_PROGRESS_MANIFESTS_PREFIX}{{manifest_id}}.json"
FAILED_MANIFESTS_PATH = "manifests/failed/{product_id}/{dataset_id}/{manifest_id}.json"
DONE_MANIFESTS_PATH = "manifests/done/{product_id}/{dataset_id}/{manifest_id}.json"
