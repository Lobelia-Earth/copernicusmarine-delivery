from pathlib import Path
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
from pusher.core_functions.core_functions import delivery as delivery_function
from pusher.core_functions.domain import ResponseUpload
from pusher.core_functions.utils import megabytes_to_bytes
from pusher.python_interface import Delete, Delivery, Upload
from pusher.s3_client import S3Client

MOCK_FILES = [
    "tests/resources/dataset1/file1.txt",
    "tests/resources/dataset1/file2.txt",
]
MOCK_FILES_ABS = [str(Path(f).resolve()) for f in MOCK_FILES]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"
PRODUCT_ID = "GLOBAL_ANALYSISFORECAST_BGC_001_028"
DATASET_ID = "cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m_202311"


@freeze_time("2012-01-14 12:00:01")
def test_delivery_python_interface(
    snapshot,
    glo_mercator_bucket,
    set_env,
    skip_delivery_ids_validation,
    ingestion_service,
):

    response, delivery = delivery_function(
        operations=[
            Delete(files=MOCK_FILES),
            Upload(files=MOCK_FILES, anchor="dataset1"),
        ],
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
    assert delivery is not None
    assert delivery.model_dump_json(indent=2) == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delivery_early_exit_with_validation_error(
    glo_mercator_bucket, set_env, skip_delivery_ids_validation, ingestion_service
):
    with pytest.raises(InvalidFilesError) as exc_info:
        delivery_function(
            operations=[
                Delete(files=MOCK_FILES),
                Upload(files=MOCK_FILES + ["extra_file.txt"], anchor="dataset1"),
            ],
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
    snapshot,
    glo_mercator_bucket,
    cli_env,
    skip_delivery_ids_validation,
    ingestion_service,
):
    delivery_file_example = "tests/resources/delivery_file.yaml"

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
    monkeypatch,
    glo_mercator_bucket,
    set_env,
    skip_delivery_ids_validation,
    ingestion_service,
):
    mock_put = Mock()
    mock_upload_fileobj = Mock()
    monkeypatch.setattr(S3Client, "_put_with_os_error_retry", mock_put)
    monkeypatch.setattr(S3Client, "upload_fileobj", mock_upload_fileobj)

    response, delivery = delivery_function(
        operations=[
            Delete(files=MOCK_FILES),
            Upload(files=MOCK_FILES, anchor="dataset1"),
        ],
        pushing_entity_id=PUSHING_ENTITY_ID,
        dataset_id="dataset1",
        product_id="product1",
        raise_on_upload_error=False,
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        chunk_concurrency=CHUNK_CONCURRENCY,
        dry_run=True,
    )

    mock_put.assert_not_called()
    mock_upload_fileobj.assert_not_called()
    assert delivery is not None
    assert len(response.operations_responses) == 2


@freeze_time("2012-01-14 12:00:01")
@pytest.mark.parametrize(
    "files, anchor, expected_suffixes",
    [
        pytest.param(
            MOCK_FILES,
            "tests",
            {"resources/dataset1/file1.txt", "resources/dataset1/file2.txt"},
            id="relative-explicit-anchor-overrides-dataset-id",
        ),
        pytest.param(
            MOCK_FILES_ABS,
            "tests",
            {"resources/dataset1/file1.txt", "resources/dataset1/file2.txt"},
            id="absolute-explicit-anchor-overrides-dataset-id",
        ),
    ],
)
def test_delivery_upload_anchor_strips_expected_s3_key(
    files,
    anchor,
    expected_suffixes,
    s3_client,
    glo_mercator_bucket,
    set_env,
    skip_delivery_ids_validation,
    ingestion_service,
):
    """The anchor only affects the local path used to build the S3 key.
    Check it end-to-end: the key returned in the response, and the object
    actually landing in S3 under that key, not just `strip_to_anchor` in isolation.
    Covers absolute local paths too."""
    response, delivery = delivery_function(
        operations=[Upload(files=files, anchor=anchor)],
        pushing_entity_id=PUSHING_ENTITY_ID,
        dataset_id="dataset1",
        product_id="product1",
        raise_on_upload_error=False,
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        chunk_concurrency=CHUNK_CONCURRENCY,
        dry_run=False,
    )

    upload_response = response.operations_responses[0]
    assert isinstance(upload_response, ResponseUpload)
    uploaded_suffixes = {suffix for _, suffix in upload_response.files_uploaded}
    assert uploaded_suffixes == {
        f"product1/dataset1/{suffix}" for suffix in expected_suffixes
    }

    for suffix in expected_suffixes:
        key = f"data/{delivery.delivery_id}/product1/dataset1/{suffix}"
        s3_client.head_object(Bucket=glo_mercator_bucket, Key=key)


def test_upload_one_file_cannot_be_uploaded_with_raise(
    monkeypatch, glo_mercator_bucket, ingestion_service
):
    def mock__put_with_os_error_retry(self, key, file, chunk_size, use_multipart=True):
        if "file1.txt" in key:
            raise Exception("Simulated upload failure for file1.txt")
        return {"e_tag": "mock-etag", "VersionId": "mock-version-id"}

    upload = Upload(files=MOCK_FILES, anchor="dataset1")
    delivery = Delivery(operations=[upload])
    monkeypatch.setattr(
        S3Client, "_put_with_os_error_retry", mock__put_with_os_error_retry
    )
    with pytest.raises(Exception) as exc_info:
        delivery.submit(
            pushing_entity_id=PUSHING_ENTITY_ID,
            dataset_id=DATASET_ID,
            product_id=PRODUCT_ID,
            raise_on_upload_error=True,
            max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
            chunk_size_mb=DEFAULT_CHUNK_SIZE_MB,
            chunk_concurrency=CHUNK_CONCURRENCY,
        )
    assert "Simulated upload failure for file1.txt" in str(exc_info.value)
