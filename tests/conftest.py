import os
from typing import Generator

import boto3
import pytest

from pusher.s3_client import S3Client, get_s3_ingestion_client

_PUSHING_ENTITY_ID = "TEST-ENTITY-FR"
_BUCKET_NAME = f"mdl-ing-{_PUSHING_ENTITY_ID.lower()}"
_BOTO_KWARGS = {
    "aws_access_key_id": "test",
    "aws_secret_access_key": "test",
    "region_name": "us-east-1",
}


@pytest.fixture(scope="session")
def ministack_endpoint() -> str:
    return os.environ.get("S3_ENDPOINT_URL", "http://localhost:4566")


@pytest.fixture
def s3_client(ministack_endpoint: str):
    return boto3.client("s3", endpoint_url=ministack_endpoint, **_BOTO_KWARGS)


@pytest.fixture
def ingestion_bucket(s3_client) -> Generator[str, None]:
    s3_client.create_bucket(Bucket=_BUCKET_NAME)
    yield _BUCKET_NAME
    _cleanup_bucket(s3_client, _BUCKET_NAME)


def _cleanup_bucket(s3_client, bucket: str) -> None:
    for obj in s3_client.list_objects_v2(Bucket=bucket).get("Contents", []):
        s3_client.delete_object(Bucket=bucket, Key=obj["Key"])
    s3_client.delete_bucket(Bucket=bucket)


@pytest.fixture
def glo_mercator_bucket(s3_client) -> Generator[str, None]:
    bucket = "mdl-ing-glo-mercator-toulouse-fr"
    s3_client.create_bucket(Bucket=bucket)
    yield bucket
    _cleanup_bucket(s3_client, bucket)


@pytest.fixture
def service(ingestion_bucket: str, ministack_endpoint: str, set_env) -> S3Client:
    return get_s3_ingestion_client(
        pushing_entity_id=_PUSHING_ENTITY_ID,
    )


@pytest.fixture
def cli_env(ministack_endpoint: str) -> dict:
    return {
        "OPDV_ACCESS_KEY_ID": "test",
        "OPDV_SECRET_ACCESS_KEY": "test",
        "INGESTION_BUCKETS_ENDPOINT": ministack_endpoint,
        "ENVIRONMENT": "local",
    }


@pytest.fixture(autouse=False)
def set_env(monkeypatch, cli_env):
    for key, value in cli_env.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def skip_delivery_ids_validation(monkeypatch):
    from pusher.core_functions import core_functions

    monkeypatch.setattr(core_functions, "validate_delivery_ids", lambda *a, **kw: None)
