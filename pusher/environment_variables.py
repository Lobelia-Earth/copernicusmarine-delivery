import os

_REQUIRED_ENV_VARS = {"OPDV_ACCESS_KEY_ID", "OPDV_SECRET_ACCESS_KEY"}

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
