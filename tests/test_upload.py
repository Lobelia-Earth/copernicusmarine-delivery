import glob
import json
import os
import random

from click.testing import CliRunner
from freezegun import freeze_time

from pusher.command_line_interface import cli
from pusher.core_functions.core_functions import upload

MOCK_FILES = ["tests/resources/file1.txt", "tests/resources/file2.txt"]
ABS_MOCK_FILES = [os.path.abspath(f) for f in MOCK_FILES]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"


@freeze_time("2012-01-14 12:00:01")
def test_upload_python_interface(snapshot, glo_mercator_bucket, set_env):
    random.seed(42)

    response = upload(
        pushing_entity_id=PUSHING_ENTITY_ID,
        files=MOCK_FILES,
        dataset_id="dataset1",
        product_id="product1",
        max_concurrent_uploads=10,
    )
    result = response.model_dump(exclude_none=True)
    result["files"] = sorted(result.get("files", []))
    result["files_uploaded"] = sorted(result.get("files_uploaded", []))
    result["files_failed"] = sorted(result.get("files_failed", []))
    result["files_invalid"] = sorted(result.get("files_invalid", []))
    for op in result.get("manifest", {}).get("operations", []):
        op["files"] = sorted(op["files"], key=lambda f: f["s3_path"])
    assert result == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_upload_cli(glo_mercator_bucket, cli_env, snapshot):
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
def test_upload_cli_save_delivery_json(glo_mercator_bucket, cli_env, snapshot):
    random.seed(42)
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "upload",
                "--pushing-entity-id",
                PUSHING_ENTITY_ID,
                "--source",
                ABS_MOCK_FILES[0],
                "--source",
                ABS_MOCK_FILES[1],
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
        with open(json_files[0]) as f:
            delivery = json.load(f)
        assert delivery == snapshot


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
