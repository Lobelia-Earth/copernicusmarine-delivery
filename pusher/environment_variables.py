import os


def required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is not set.")
    return value


ALLOW_HTTP = bool(os.getenv("ALLOW_HTTP"))
INGESTION_BUCKETS_ENDPOINT = os.getenv(
    "INGESTION_BUCKETS_ENDPOINT", "http://localhost:4566"
)
MDL_METADATA_BUCKET = required_environment_variable("MDL_METADATA_BUCKET")
OPDV_S3_ENDPOINT = os.getenv("OPDV_S3_ENDPOINT", "http://localhost:4566")
OPDV_ACCESS_KEY_ID = required_environment_variable("OPDV_ACCESS_KEY_ID")
OPDV_SECRET_ACCESS_KEY = required_environment_variable("OPDV_SECRET_ACCESS_KEY")
