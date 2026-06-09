"""Moslty aimed at having ingestion bucket paths constants. Ideally should be centralised so that
the OPDV can also use them"""

from pydantic_settings import BaseSettings, SettingsConfigDict


# FIXME -> Should the buckets endpoint live hardcoded here?
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    access_key_id: str
    secret_access_key: str
    environment: str = "prod"
    ingestion_buckets_endpoint: str = "http://localhost:4566"
    max_concurrent_uploads: int = 10


NEW_MANIFESTS_PREFIX = "manifests/new/{manifest_id}.json"
NEW_DATA_BUCKET_PATH = (
    "data/{manifest_id}/{product_id}/{dataset_id}/{YYYY}/{MM}/{file_name}"
)
