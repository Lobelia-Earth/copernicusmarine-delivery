import random
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from freezegun import freeze_time

from pusher import InvalidFilesError
from pusher.command_line_interface import cli
from pusher.core_functions.constants import (
    CHUNK_CONCURRENCY,
    DEFAULT_CHUNK_SIZE_MB,
    MAX_CONCURRENT_UPLOADS,
)
from pusher.core_functions.core_functions import delivery
from pusher.core_functions.utils import megabytes_to_bytes
from pusher.python_interface import Delivery, Upload
from pusher.s3_client import S3Client

MOCK_FILES = ["tests/resources/file1.txt", "tests/resources/file2.txt"]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"


@freeze_time("2012-01-14 12:00:01")
def test_delivery_python_interface(
    snapshot, glo_mercator_bucket, set_env, skip_delivery_ids_validation
):
    random.seed(42)
    operations = [
        ("delete", MOCK_FILES),
        ("upload", MOCK_FILES),
    ]

    response, manifest = delivery(
        operations=operations,  # type: ignore
        pushing_entity_id=PUSHING_ENTITY_ID,
        dataset_id="dataset1",
        product_id="product1",
        raise_on_upload_error=False,
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        chunk_concurrency=CHUNK_CONCURRENCY,
        dry_run=False,
    )
    assert response.model_dump_json(indent=2) == snapshot
    assert manifest is not None
    assert manifest.model_dump_json(indent=2) == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delivery_early_exit_with_validation_error(
    glo_mercator_bucket, set_env, skip_delivery_ids_validation
):
    random.seed(42)
    operations = [("delete", MOCK_FILES), ("upload", MOCK_FILES + ["extra_file.txt"])]
    with pytest.raises(InvalidFilesError) as exc_info:
        delivery(
            operations=operations,  # type: ignore
            pushing_entity_id=PUSHING_ENTITY_ID,
            dataset_id="dataset1",
            product_id="product1",
            raise_on_upload_error=False,
            max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
            chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
            chunk_concurrency=CHUNK_CONCURRENCY,
            dry_run=False,
        )
    assert "Found 1 invalid files." in str(exc_info.value)


@freeze_time("2012-01-14 12:00:01")
def test_delivery_cli_with_delivery_file(
    snapshot, glo_mercator_bucket, cli_env, skip_delivery_ids_validation
):
    delivery_file_example = "tests/resources/delivery_file.yaml"

    random.seed(42)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "delivery",
            "--pushing-entity-id",
            PUSHING_ENTITY_ID,
            "--dataset-id",
            "dataset1",
            "--product-id",
            "product1",
            "--file",
            delivery_file_example,
        ],
    )

    assert result.exit_code == 0
    assert result.output.strip() == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delivery_dry_run_does_not_call_s3(
    monkeypatch, glo_mercator_bucket, set_env, skip_delivery_ids_validation
):
    random.seed(42)
    mock_put = Mock()
    mock_upload_fileobj = Mock()
    monkeypatch.setattr(S3Client, "_put_with_os_error_retry", mock_put)
    monkeypatch.setattr(S3Client, "upload_fileobj", mock_upload_fileobj)

    operations = [
        ("delete", MOCK_FILES),
        ("upload", MOCK_FILES),
    ]

    response, manifest = delivery(
        operations=operations,  # type: ignore
        pushing_entity_id=PUSHING_ENTITY_ID,
        dataset_id="dataset1",
        product_id="product1",
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        chunk_concurrency=CHUNK_CONCURRENCY,
        dry_run=True,
    )

    mock_put.assert_not_called()
    mock_upload_fileobj.assert_not_called()
    assert manifest is not None
    assert len(response.operations_responses) == 2


def test_upload_one_file_cannot_be_uploaded_with_raise(
    monkeypatch, glo_mercator_bucket
):
    def mock__put_with_os_error_retry(self, key, file, chunk_size, use_multipart=True):
        if "file1.txt" in key:
            raise Exception("Simulated upload failure for file1.txt")
        return {"e_tag": "mock-etag", "VersionId": "mock-version-id"}

    upload = Upload(files=MOCK_FILES)
    delivery = Delivery(operations=[upload])
    monkeypatch.setattr(
        S3Client, "_put_with_os_error_retry", mock__put_with_os_error_retry
    )
    with pytest.raises(Exception) as exc_info:
        delivery.submit(
            pushing_entity_id=PUSHING_ENTITY_ID,
            dataset_id="dataset1",
            product_id="product1",
            raise_on_upload_error=True,
            max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
            chunk_size_mb=DEFAULT_CHUNK_SIZE_MB,
            chunk_concurrency=CHUNK_CONCURRENCY,
        )
    assert "Simulated upload failure for file1.txt" in str(exc_info.value)
