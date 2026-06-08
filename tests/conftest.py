from typing import Generator
import os

import boto3
import pytest

from pusher.config.settings import Settings
from pusher.services.ingestion_bucket_service import IngestionBucketService

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
    )


@pytest.fixture
def s3_client(ministack_endpoint: str):
    return boto3.client("s3", endpoint_url=ministack_endpoint, **_BOTO_KWARGS)


@pytest.fixture
def ingestion_bucket(s3_client) -> Generator[str, None]:
    s3_client.create_bucket(Bucket=_BUCKET_NAME)
    yield _BUCKET_NAME
    objects = s3_client.list_objects_v2(Bucket=_BUCKET_NAME).get("Contents", [])
    for obj in objects:
        s3_client.delete_object(Bucket=_BUCKET_NAME, Key=obj["Key"])
    s3_client.delete_bucket(Bucket=_BUCKET_NAME)


@pytest.fixture
def test_ingestion_bucket_service(
    ingestion_bucket: str, ministack_endpoint: str
) -> IngestionBucketService:
    return IngestionBucketService.from_s3_credentials(
        pushing_entity_id=_PUSHING_ENTITY_ID,
        access_key_id="test",
        secret_access_key="test",
        endpoint_url=ministack_endpoint,
    )
