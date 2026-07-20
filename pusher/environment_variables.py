import os


def required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is not set.")
    return value


ALLOW_HTTP = bool(os.getenv("ALLOW_HTTP"))
MDL_METADATA_BUCKET = os.getenv("MDL_METADATA_BUCKET", "mdl-metadata")
MDL_METADATA_ENDPOINT = os.getenv(
    "MDL_METADATA_ENDPOINT", "https://s3.waw3-1.cloudferro.com"
)
OPDV_S3_ENDPOINT = os.getenv("OPDV_S3_ENDPOINT", "http://localhost:4566")
OPDV_ACCESS_KEY_ID = required_environment_variable("OPDV_ACCESS_KEY_ID")
OPDV_SECRET_ACCESS_KEY = required_environment_variable("OPDV_SECRET_ACCESS_KEY")
