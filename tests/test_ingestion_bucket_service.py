import json
from pathlib import Path

import pytest

from pusher.domain.models import ErrorPutFile, S3File
from pusher.infrastructure.obstore_s3_client import (
    NoSuchBucketException,
    ObstoreS3ClientConnection,
)
from pusher.services.ingestion_bucket_service import IngestionBucketService

RESOURCES = Path("tests/resources")


def test_put_file_success(
    test_ingestion_bucket_service: IngestionBucketService,
    s3_client,
    ingestion_bucket: str,
):
    key = "data/test/file1.txt"
    result = test_ingestion_bucket_service.put_file(RESOURCES / "file1.txt", key)
    assert isinstance(result, S3File)
    assert result.s3_path == key
    assert result.e_tag
    s3_client.head_object(Bucket=ingestion_bucket, Key=key)


def test_put_file_nonexistent_returns_error(
    test_ingestion_bucket_service: IngestionBucketService, ingestion_bucket: str
):
    result = test_ingestion_bucket_service.put_file(
        Path("nonexistent/file.nc"), "data/test/missing.nc"
    )
    assert isinstance(result, ErrorPutFile)
    assert result.local_path == "nonexistent/file.nc"


def test_put_multiple_files(
    test_ingestion_bucket_service: IngestionBucketService,
    settings,
    s3_client,
    ingestion_bucket: str,
):
    mapping = {
        RESOURCES / "file1.txt": "data/test/file1.txt",
        RESOURCES / "file2.txt": "data/test/file2.txt",
    }
    result = test_ingestion_bucket_service.put_multiple_files(mapping, settings)
    assert len(result.success) == 2
    assert len(result.error) == 0
    for f in result.success:
        s3_client.head_object(Bucket=ingestion_bucket, Key=f.s3_path)


def test_put_multiple_files_partial_failure(
    test_ingestion_bucket_service: IngestionBucketService,
    settings,
    ingestion_bucket: str,
):
    mapping = {
        RESOURCES / "file1.txt": "data/test/file1.txt",
        Path("nonexistent/file.nc"): "data/test/missing.nc",
    }
    result = test_ingestion_bucket_service.put_multiple_files(mapping, settings)
    assert len(result.success) == 1
    assert len(result.error) == 1
    assert result.success[0].s3_path == "data/test/file1.txt"


def test_put_manifest(
    test_ingestion_bucket_service: IngestionBucketService,
    s3_client,
    ingestion_bucket: str,
):
    manifest = {"manifest_id": "test-123", "operations": []}
    key = "manifests/new/2024/01/01/test-123.json"
    test_ingestion_bucket_service.put_manifest(manifest, key)
    body = json.loads(
        s3_client.get_object(Bucket=ingestion_bucket, Key=key)["Body"].read()
    )
    assert body == manifest


def test_no_such_bucket_raises(ministack_endpoint: str):
    with pytest.raises(NoSuchBucketException):
        ObstoreS3ClientConnection(
            pushing_entity_id="NONEXISTENT-ENTITY-ZZ",
            access_key_id="test",
            secret_access_key="test",
            endpoint_url=ministack_endpoint,
        )
