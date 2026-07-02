from pathlib import Path

import pytest
from freezegun import freeze_time
from pydantic import ValidationError

from pusher.core_functions.core_functions import (
    get_manifest_destination_key,
    get_upload_bucket_keys_from_local_files,
)
from pusher.core_functions.manifests_helper import (
    create_manifest,
    create_manifest_id,
)
from pusher.core_functions.models import (
    Manifest,
    ManifestFile,
    Operation,
    ResponseUpload,
)

RESOURCES = Path("tests/resources")


# --- Models ---


def test_manifest_file_none_file_size():
    f = ManifestFile(
        file_path=Path("data/key/file.nc"), file_size=None, checksum="abc123"
    )
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
    assert response.files_uploaded == []


# --- Path generation ---


@freeze_time("2024-03-15")
def test_get_bucket_keys_from_local_files():
    result = get_upload_bucket_keys_from_local_files(
        list_of_files=[Path("path/to/file.nc")],
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
    key = get_manifest_destination_key("20240315T000000-dataset1-1234")
    assert "20240315T000000-dataset1-1234" in key


# --- Manifest creation ---


@freeze_time("2024-03-15 12:00:01")
def test_create_manifest_id_format():
    manifest_id = create_manifest_id("dataset1")
    assert manifest_id.startswith("20240315T120001-dataset1-")
    suffix = manifest_id.split("-")[-1]
    assert suffix.isdigit() and 1000 <= int(suffix) <= 9999


@freeze_time("2024-03-15 12:00:01")
def test_create_manifest(tmp_path):
    f = tmp_path / "file.nc"
    f.write_bytes(b"x" * 1024)
    manifest_id = create_manifest_id("product1")
    manifest = create_manifest(
        pushing_entity_id="TEST-FR",
        product_id="product1",
        dataset_id="dataset1",
        operations=[
            Operation(
                operation="upload",
                files=[ManifestFile(file_path=f, file_size=43, checksum="abc-1")],
            )
        ],
        manifest_id=manifest_id,
    )
    assert manifest.pushing_entity_id == "TEST-FR"
    assert manifest.operations[0].operation == "upload"
    assert manifest.operations[0].files[0].checksum == "abc-1"
