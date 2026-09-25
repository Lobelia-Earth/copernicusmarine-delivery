import glob
import json
import os

import pytest
import yaml
from click.testing import CliRunner
from freezegun import freeze_time

from copernicusmarine_delivery import InvalidDeliveryIdsError, Upload
from copernicusmarine_delivery.command_line_interface import cli
from copernicusmarine_delivery.core_functions.constants import (
    CHUNK_CONCURRENCY,
    DEFAULT_CHUNK_SIZE_MB,
    MAX_CONCURRENT_UPLOADS,
)
from copernicusmarine_delivery.core_functions.core_functions import upload
from copernicusmarine_delivery.core_functions.utils import megabytes_to_bytes
from copernicusmarine_delivery.s3_client import S3Client

MOCK_FILES = [
    "tests/resources/dataset1/file1.txt",
    "tests/resources/dataset1/file2.txt",
]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"
PRODUCT_ID = "GLOBAL_ANALYSISFORECAST_BGC_001_028"
DATASET_ID = "cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m_202311"

_UNKNOWN_ENTITY_YAML = yaml.dump(
    {
        "pushing-entities": [
            {
                "name": "OTHER-ENTITY",
                "bucket": "mdl-ing-other-entity",
                "products": [{"name": "product1", "datasets": ["dataset1"]}],
            }
        ]
    }
).encode()


@freeze_time("2012-01-14 12:00:01")
def test_upload_python_interface(
    snapshot,
    glo_mercator_bucket,
    skip_delivery_ids_validation,
    ingestion_service,
):
    response, delivery = upload(
        files=MOCK_FILES,
        dataset_id="dataset1",
        product_id="product1",
        anchor="dataset1",
        raise_on_upload_error=False,
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_concurrency=CHUNK_CONCURRENCY,
        chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        dry_run=False,
    )
    result = response.model_dump(exclude_none=True)
    result["files_uploaded"] = sorted(result.get("files_uploaded", []))
    result["files_failed"] = sorted(result.get("files_failed", []))
    result["files_invalid"] = sorted(result.get("files_invalid", []))
    assert delivery is not None
    assert result == snapshot
    assert delivery.model_dump_json(indent=2) == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_upload_cli(
    glo_mercator_bucket,
    snapshot,
    skip_delivery_ids_validation,
    ingestion_service,
):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--source",
            MOCK_FILES[0],
            "--source",
            MOCK_FILES[1],
            "--dataset-id",
            "dataset1",
            "--product-id",
            "product1",
            "--anchor",
            "dataset1",
        ],
    )
    assert result.exit_code == 0
    assert result.output.strip() == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_upload_cli_save_delivery_json(
    glo_mercator_bucket,
    snapshot,
    skip_delivery_ids_validation,
    ingestion_service,
):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--source",
            MOCK_FILES[0],
            "--source",
            MOCK_FILES[1],
            "--dataset-id",
            "dataset1",
            "--product-id",
            "product1",
            "--anchor",
            "dataset1",
            "--save-delivery-json",
        ],
    )
    assert result.exit_code == 0
    assert result.output.strip() == snapshot

    json_files = glob.glob("*.json")
    assert len(json_files) == 1
    try:
        with open(json_files[0]) as f:
            delivery = json.load(f)
        for op in delivery.get("operations", []):
            op["files"] = sorted(op["files"], key=lambda f: f["key_suffix"])
        assert delivery == snapshot
    finally:
        for jf in json_files:
            os.remove(jf)


def test_upload_cli_no_source_exits():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--dataset-id",
            "dataset1",
            "--product-id",
            "product1",
        ],
    )
    assert result.exit_code == 1


def test_upload_raises_on_invalid_delivery_ids(monkeypatch, ingestion_service):
    monkeypatch.setattr(
        S3Client, "get_file_stream", lambda self, **kwargs: _UNKNOWN_ENTITY_YAML
    )
    with pytest.raises(InvalidDeliveryIdsError) as exc_info:
        upload(
            files=MOCK_FILES,
            dataset_id=DATASET_ID,
            product_id="product1",
            anchor="dataset1",
            raise_on_upload_error=False,
            max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
            chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
            chunk_concurrency=CHUNK_CONCURRENCY,
            dry_run=False,
        )
    assert f"product1 is not a valid Product ID for {PUSHING_ENTITY_ID}" in str(
        exc_info.value
    )


@freeze_time("2012-01-14 12:00:01")
def test_upload_one_file_cannot_be_uploaded(
    monkeypatch, snapshot, glo_mercator_bucket, ingestion_service
):
    def mock__put_with_os_error_retry(self, key, file, chunk_size, use_multipart=True):
        if "file1.txt" in key:
            raise Exception("Simulated upload failure for file1.txt")
        return {"e_tag": "mock-etag", "VersionId": "mock-version-id"}

    monkeypatch.setattr(
        S3Client, "_put_with_os_error_retry", mock__put_with_os_error_retry
    )

    response, delivery = upload(
        files=MOCK_FILES,
        dataset_id=DATASET_ID,
        product_id=PRODUCT_ID,
        anchor="dataset1",
        raise_on_upload_error=False,
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        chunk_concurrency=CHUNK_CONCURRENCY,
        dry_run=False,
    )

    assert response.fatal_error is None
    assert delivery is not None
    assert len(response.files_uploaded) == 1
    assert str(response.files_uploaded[0][0]).endswith("file2.txt")
    assert len(response.files_failed) == 1
    assert str(response.files_failed[0].local_path).endswith("file1.txt")
    assert delivery.model_dump_json(indent=2) == snapshot


def test_upload_one_file_cannot_be_uploaded_with_raise(
    monkeypatch, glo_mercator_bucket, ingestion_service
):
    def mock__put_with_os_error_retry(self, key, file, chunk_size, use_multipart=True):
        if "file1.txt" in key:
            raise Exception("Simulated upload failure for file1.txt")
        return {"e_tag": "mock-etag", "VersionId": "mock-version-id"}

    upload = Upload(files=MOCK_FILES)
    monkeypatch.setattr(
        S3Client, "_put_with_os_error_retry", mock__put_with_os_error_retry
    )
    with pytest.raises(Exception) as exc_info:
        upload.submit(
            dataset_id=DATASET_ID,
            product_id=PRODUCT_ID,
            anchor="dataset1",
            raise_on_upload_error=True,
            max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
            chunk_size_mb=DEFAULT_CHUNK_SIZE_MB,
            chunk_concurrency=CHUNK_CONCURRENCY,
        )
    assert "Simulated upload failure for file1.txt" in str(exc_info.value)
