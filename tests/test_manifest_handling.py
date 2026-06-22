from datetime import date
from pathlib import Path

import pytest
from freezegun import freeze_time
from pydantic import ValidationError

from pusher.core_functions.core_functions import (
    get_upload_bucket_keys_from_local_files,
    get_manifest_destination_key,
)
from pusher.core_functions.manifests_helper import (
    create_manifest,
    create_manifest_files,
    create_manifest_id,
)
from pusher.core_functions.models import (
    Manifest,
    ManifestFile,
    Operation,
    ResponseUpload,
    S3File,
)

RESOURCES = Path("tests/resources")


# --- Models ---


def test_manifest_file_none_file_size():
    f = ManifestFile(s3_path="data/key/file.nc", file_size=None, checksum="abc123")
    assert f.file_size is None


def test_operation_invalid_literal():
    with pytest.raises(ValidationError):
        Operation(operation="copy", files=[])  # type: ignore


def test_manifest_round_trip():
    manifest = Manifest(
        manifest_id="20240101T000000-dataset1-1234",
        pushing_entity_id="TEST-FR",
        product_id="product1",
        dataset_id="dataset1",
        operations=[],
        creation_time="2024-01-01T00:00:00+00:00",
    )
    assert manifest.model_dump()["manifest_id"] == "20240101T000000-dataset1-1234"


def test_response_upload_error_no_manifest():
    response = ResponseUpload(fatal_error="No successful uploads - no data were sent.")
    assert response.delivery is None
    assert response.files_uploaded == []


# --- Path generation ---


@freeze_time("2024-03-15")
def test_get_bucket_keys_from_local_files():
    result = get_upload_bucket_keys_from_local_files(
        today=date.today(),
        list_of_files=[Path("path/to/file.nc")],
        bucket_name="mdl-ing-test",
        manifest_id="20240315T000000-dataset1-1234",
        product_id="product1",
        dataset_id="dataset1",
    )
    assert result == {
        Path(
            "path/to/file.nc"
        ): "data/20240315T000000-dataset1-1234/product1/dataset1/file.nc"
    }


@freeze_time("2024-03-15")
def test_get_manifest_destination_key():
    key = get_manifest_destination_key(date.today(), "20240315T000000-dataset1-1234")
    assert "20240315T000000-dataset1-1234" in key


# --- Manifest creation ---


@freeze_time("2024-03-15 12:00:01")
def test_create_manifest_id_format():
    manifest_id = create_manifest_id("dataset1")
    assert manifest_id.startswith("20240315T120001-dataset1-")
    suffix = manifest_id.split("-")[-1]
    assert suffix.isdigit() and 1000 <= int(suffix) <= 9999


def test_create_manifest_files_upload(tmp_path):
    f = tmp_path / "file.nc"
    f.write_bytes(b"x" * 1024)
    files = [S3File(local_path=f, s3_path="data/key/file.nc", e_tag="abc-1")]
    result = create_manifest_files(files, "upload")
    assert result[0].checksum == "abc-1"
    assert result[0].file_size == 0  # < 1 MB rounds to 0


def test_create_manifest_files_delete():
    files = [
        S3File(
            local_path=Path("/irrelevant"), s3_path="data/key/file.nc", e_tag="abc-1"
        )
    ]
    result = create_manifest_files(files, "delete")
    assert result[0].file_size is None


def test_create_manifest_files_upload_missing_file():
    files = [
        S3File(
            local_path=Path("/nonexistent/file.nc"),
            s3_path="data/key/file.nc",
            e_tag="abc-1",
        )
    ]
    with pytest.raises(AssertionError):
        create_manifest_files(files, "upload")


@freeze_time("2024-03-15 12:00:01")
def test_create_manifest(tmp_path):
    f = tmp_path / "file.nc"
    f.write_bytes(b"x" * 1024)
    files = [S3File(local_path=f, s3_path="data/key/file.nc", e_tag="abc-1")]
    manifest = create_manifest(
        pushing_entity_id="TEST-FR",
        product_id="product1",
        dataset_id="dataset1",
        operation_files_mapping={"upload": files},
    )
    assert manifest.pushing_entity_id == "TEST-FR"
    assert manifest.operations[0].operation == "upload"
    assert manifest.operations[0].files[0].checksum == "abc-1"
