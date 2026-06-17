import random

from click.testing import CliRunner
from freezegun import freeze_time

from pusher.command_line_interface import cli
from pusher.core_functions.core_functions import upload

MOCK_FILES = ["tests/resources/file1.txt", "tests/resources/file2.txt"]
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
    assert result.output == snapshot


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
