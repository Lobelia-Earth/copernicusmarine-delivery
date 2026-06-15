import os

## Constants to be decided where they'll go or how they'll be set
NEW_MANIFESTS_PREFIX = "manifests/new/{manifest_id}.json"
NEW_DATA_BUCKET_PATH = "data/{manifest_id}/{product_id}/{dataset_id}/{file_name}"

_REQUIRED_ENV_VARS = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"}

_ENV_VARS_WITH_DEFAULTS = {
    "ENVIRONMENT": "prod",
    "INGESTION_BUCKETS_ENDPOINT": "http://localhost:4566",
}


def __getattr__(name: str) -> str:
    if name in _REQUIRED_ENV_VARS or name in _ENV_VARS_WITH_DEFAULTS:
        value = os.getenv(name, _ENV_VARS_WITH_DEFAULTS.get(name, ""))
        if not value:
            raise ValueError(f"{name} environment variable is not set.")
        return value
    raise ValueError(f"{name} is not a valid environment variable.")
