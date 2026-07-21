import glob
import json
import os
import random

import yaml
from click.testing import CliRunner
from freezegun import freeze_time

from pusher.command_line_interface import cli
from pusher.core_functions.constants import (
    CHUNK_CONCURRENCY,
    DEFAULT_CHUNK_SIZE_MB,
    MAX_CONCURRENT_UPLOADS,
)
from pusher.core_functions.core_functions import upload
from pusher.core_functions.utils import megabytes_to_bytes
from pusher.s3_client import S3Client

MOCK_FILES = ["tests/resources/file1.txt", "tests/resources/file2.txt"]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"

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
    snapshot, glo_mercator_bucket, set_env, skip_delivery_ids_validation
):
    random.seed(42)

    response, manifest = upload(
        pushing_entity_id=PUSHING_ENTITY_ID,
        files=MOCK_FILES,
        dataset_id="dataset1",
        product_id="product1",
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_concurrency=CHUNK_CONCURRENCY,
        chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
    )
    result = response.model_dump(exclude_none=True)
    result["files_uploaded"] = sorted(result.get("files_uploaded", []))
    result["files_failed"] = sorted(result.get("files_failed", []))
    result["files_invalid"] = sorted(result.get("files_invalid", []))
    assert manifest is not None
    for op in manifest.operations:
        op.files = sorted(op.files, key=lambda f: f.key_suffix)
    assert result == snapshot
    assert manifest.model_dump_json(indent=2) == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_upload_cli(
    glo_mercator_bucket, cli_env, snapshot, skip_delivery_ids_validation
):
    random.seed(42)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--pushing-entity-id",
            PUSHING_ENTITY_ID,
            "--source",
            MOCK_FILES[0],
            "--source",
            MOCK_FILES[1],
            "--dataset-id",
            "dataset1",
            "--product-id",
            "product1",
        ],
        env=cli_env,
    )
    assert result.exit_code == 0
    output = json.loads(result.output)
    output["files_uploaded"] = sorted(output.get("files_uploaded", []))
    for op in output.get("manifest", {}).get("operations", []):
        op["files"] = sorted(op["files"], key=lambda f: f["s3_path"])
    assert output == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_upload_cli_save_delivery_json(
    glo_mercator_bucket, cli_env, snapshot, skip_delivery_ids_validation
):
    random.seed(42)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--pushing-entity-id",
            PUSHING_ENTITY_ID,
            "--source",
            MOCK_FILES[0],
            "--source",
            MOCK_FILES[1],
            "--dataset-id",
            "dataset1",
            "--product-id",
            "product1",
            "--save-delivery-json",
        ],
        env=cli_env,
    )
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert "delivery" not in output

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


def test_upload_cli_no_source_exits(cli_env):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--pushing-entity-id",
            PUSHING_ENTITY_ID,
            "--dataset-id",
            "dataset1",
            "--product-id",
            "product1",
        ],
        env=cli_env,
    )
    assert result.exit_code == 1


def test_upload_returns_fatal_error_on_invalid_delivery_ids(monkeypatch):
    monkeypatch.setattr(
        S3Client, "get_file_stream", lambda self, **kwargs: _UNKNOWN_ENTITY_YAML
    )

    response, manifest = upload(
        pushing_entity_id=PUSHING_ENTITY_ID,
        files=MOCK_FILES,
        dataset_id="dataset1",
        product_id="product1",
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        chunk_concurrency=CHUNK_CONCURRENCY,
    )
    assert (
        response.fatal_error
        == f"{PUSHING_ENTITY_ID} is not a valid registered Pushing Entity"
    )
    assert manifest is None
