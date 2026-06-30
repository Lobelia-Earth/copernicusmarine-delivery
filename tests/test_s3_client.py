from pathlib import Path

import pytest

from pusher.core_functions.exceptions import NoSuchBucketException
from pusher.core_functions.models import ErrorFile, S3File
from pusher.s3_client import S3Client, get_s3_ingestion_client

RESOURCES = Path("tests/resources")


def test_no_such_bucket_raises(ministack_endpoint: str, set_env):
    with pytest.raises(NoSuchBucketException):
        get_s3_ingestion_client(pushing_entity_id="NONEXISTENT-ENTITY-ZZ")


def test_upload_file_success(service: S3Client, s3_client, ingestion_bucket: str):
    key = "data/test/file1.txt"
    result = service.upload_file(key=key, file=RESOURCES / "file1.txt")
    assert isinstance(result, S3File)
    assert result.s3_path == key
    assert result.e_tag
    s3_client.head_object(Bucket=ingestion_bucket, Key=key)


def test_upload_file_nonexistent_returns_error(
    service: S3Client, ingestion_bucket: str
):
    result = service.upload_file(
        key="data/test/missing.nc", file=Path("nonexistent/file.nc")
    )
    assert isinstance(result, ErrorFile)


def test_upload_multiple_files(
    service: S3Client,
    s3_client,
    ingestion_bucket: str,
):
    mapping = {
        RESOURCES / "file1.txt": "data/test/file1.txt",
        RESOURCES / "file2.txt": "data/test/file2.txt",
    }
    result = service.upload_multiple_files(mapping, 10)
    assert len(result.successful_files) == 2
    assert len(result.errored_files) == 0
    for f in result.successful_files:
        s3_client.head_object(Bucket=ingestion_bucket, Key=f.s3_path)


def test_upload_multiple_files_partial_failure(
    service: S3Client, ingestion_bucket: str
):
    mapping = {
        RESOURCES / "file1.txt": "data/test/file1.txt",
        Path("nonexistent/file.nc"): "data/test/missing.nc",
    }
    result = service.upload_multiple_files(mapping, 10)
    assert len(result.successful_files) == 1
    assert len(result.errored_files) == 1
    assert result.successful_files[0].s3_path == "data/test/file1.txt"
