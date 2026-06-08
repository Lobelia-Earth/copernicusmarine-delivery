"""Moslty aimed at having ingestion bucket paths constants. Ideally should be centralised so that
the OPDV can also use them"""

from pydantic_settings import BaseSettings, SettingsConfigDict


# FIXME -> How do we make this configurable? Should it leave in plain text in the toolbox?
# INGESTION_BUCKETS_ENDPOINT = "https://s3.waw3-1.cloudferro.com"
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    access_key_id: str
    secret_access_key: str
    environment: str = "dev"
    ingestion_buckets_endpoint: str = "http://localhost:4566"
    max_concurrent_uploads: int = 10


NEW_MANIFESTS_PREFIX = "manifests/new/{YYYY}/{MM}/{DD}/{manifest_id}.json"
NEW_DATA_BUCKET_PATH = (
    "data/{manifest_id}/{product_id}/{dataset_id}/{YYYY}/{MM}/{file_name}"
)
