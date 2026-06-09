import os
from typing import Generator

import boto3
import pytest

from pusher.core_functions.settings import Settings
from pusher.s3_client import S3Client

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


@pytest.fixture(scope="session")
def settings(ministack_endpoint: str) -> Settings:
    return Settings(  # type: ignore[call-arg]
        access_key_id="test",
        secret_access_key="test",
        ingestion_buckets_endpoint=ministack_endpoint,
        environment="local",
    )


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
def service(ingestion_bucket: str, ministack_endpoint: str) -> S3Client:
    return S3Client(
        pushing_entity_id=_PUSHING_ENTITY_ID,
        access_key_id="test",
        secret_access_key="test",
        endpoint_url=ministack_endpoint,
        environment="local",
    )


@pytest.fixture
def cli_env(ministack_endpoint: str) -> dict:
    return {
        "ACCESS_KEY_ID": "test",
        "SECRET_ACCESS_KEY": "test",
        "INGESTION_BUCKETS_ENDPOINT": ministack_endpoint,
        "ENVIRONMENT": "local",
    }
