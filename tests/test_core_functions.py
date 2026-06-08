from datetime import date
from pathlib import Path

import pytest
from freezegun import freeze_time

from pusher.domain.core_functions import (
    get_bucket_keys_from_local_files,
    get_manifest_destination_key,
)
from pusher.domain.manifests_helper import (
    create_manifest,
    create_manifest_files,
    create_manifest_id,
)
from pusher.domain.models import S3File


@freeze_time("2024-03-15")
def test_get_bucket_keys_from_local_files():
    result = get_bucket_keys_from_local_files(
        today=date.today(),
        list_of_files=["path/to/file.nc"],
        bucket_name="mdl-ing-test",
        manifest_id="20240315T000000-dataset1-1234",
        product_id="product1",
        dataset_id="dataset1",
    )
    assert result == {
        Path(
            "path/to/file.nc"
        ): "data/20240315T000000-dataset1-1234/product1/dataset1/2024/03/file.nc"
    }


@freeze_time("2024-03-15")
def test_get_bucket_keys_multiple_files():
    result = get_bucket_keys_from_local_files(
        today=date.today(),
        list_of_files=["a/file1.nc", "b/file2.nc"],
        bucket_name="mdl-ing-test",
        manifest_id="20240315T000000-dataset1-1234",
        product_id="product1",
        dataset_id="dataset1",
    )
    assert len(result) == 2
    assert Path("a/file1.nc") in result
    assert Path("b/file2.nc") in result


@freeze_time("2024-03-15")
def test_get_manifest_destination_key():
    key = get_manifest_destination_key(date.today(), "20240315T000000-dataset1-1234")
    assert key == "manifests/new/2024/03/15/20240315T000000-dataset1-1234.json"


@freeze_time("2024-03-15 12:00:01")
def test_create_manifest_id_format():
    manifest_id = create_manifest_id("dataset1")
    assert manifest_id.startswith("20240315T120001-dataset1-")
    suffix = manifest_id.split("-")[-1]
    assert suffix.isdigit() and 1000 <= int(suffix) <= 9999


def test_create_manifest_files_upload(tmp_path):
    f = tmp_path / "file.nc"
    f.write_bytes(b"x" * 1024)
    files = [S3File(local_path=str(f), s3_path="data/key/file.nc", e_tag="abc-1")]
    result = create_manifest_files(files, "upload")
    assert result[0].s3_path == "data/key/file.nc"
    assert result[0].checksum == "abc-1"
    assert result[0].file_size == 0  # < 1 MB rounds to 0


def test_create_manifest_files_delete():
    files = [
        S3File(local_path="/irrelevant", s3_path="data/key/file.nc", e_tag="abc-1")
    ]
    result = create_manifest_files(files, "delete")
    assert result[0].file_size is None


def test_create_manifest_files_upload_missing_file():
    files = [
        S3File(
            local_path="/nonexistent/file.nc", s3_path="data/key/file.nc", e_tag="abc-1"
        )
    ]
    with pytest.raises(AssertionError):
        create_manifest_files(files, "upload")


@freeze_time("2024-03-15 12:00:01")
def test_create_manifest(tmp_path):
    f = tmp_path / "file.nc"
    f.write_bytes(b"x" * 1024)
    files = [S3File(local_path=str(f), s3_path="data/key/file.nc", e_tag="abc-1")]
    manifest = create_manifest(
        pushing_entity_id="TEST-FR",
        product_id="product1",
        dataset_id="dataset1",
        operation_files_mapping={"upload": files},
    )
    assert manifest.pushing_entity_id == "TEST-FR"
    assert len(manifest.operations) == 1
    assert manifest.operations[0].operation == "upload"
    assert manifest.operations[0].files[0].checksum == "abc-1"
