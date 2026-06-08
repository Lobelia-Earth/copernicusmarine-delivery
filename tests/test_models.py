import pytest
from pydantic import ValidationError

from pusher.domain.models import Manifest, ManifestFile, Operation, ResponseUpload, S3File


def test_manifest_file_with_size():
    f = ManifestFile(s3_path="data/key/file.nc", file_size=10, checksum="abc123")
    assert f.file_size == 10


def test_manifest_file_none_file_size():
    f = ManifestFile(s3_path="data/key/file.nc", file_size=None, checksum="abc123")
    assert f.file_size is None


def test_operation_upload():
    op = Operation(
        operation="upload",
        files=[ManifestFile(s3_path="data/key/file.nc", file_size=1, checksum="abc")],
    )
    assert op.operation == "upload"
    assert len(op.files) == 1


def test_operation_invalid_literal():
    with pytest.raises(ValidationError):
        Operation(operation="copy", files=[])


def test_manifest_round_trip():
    manifest = Manifest(
        manifest_id="20240101T000000-dataset1-1234",
        pushing_entity_id="TEST-FR",
        product_id="product1",
        dataset_id="dataset1",
        operations=[],
        creation_time="2024-01-01T00:00:00+00:00",
    )
    dumped = manifest.model_dump()
    assert dumped["manifest_id"] == "20240101T000000-dataset1-1234"
    assert dumped["operations"] == []


def test_response_upload_no_errors():
    files = [S3File(local_path="/tmp/f.nc", s3_path="data/key/f.nc", e_tag="abc-1")]
    response = ResponseUpload(files=files, files_errored=[], manifest=Manifest(
        manifest_id="20240101T000000-dataset1-1234",
        pushing_entity_id="TEST-FR",
        product_id="product1",
        dataset_id="dataset1",
        operations=[],
        creation_time="2024-01-01T00:00:00+00:00",
    ))
    assert response.files_errored == []
    assert len(response.files) == 1
