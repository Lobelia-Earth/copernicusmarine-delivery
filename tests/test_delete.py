import glob
import json
import random

import pytest
from click.testing import CliRunner
from freezegun import freeze_time

from pusher.command_line_interface import cli
from pusher.core_functions.core_functions import delete

pytestmark = pytest.mark.usefixtures("skip_delivery_ids_validation")

MOCK_FILES = ["tests/resources/file1.txt", "tests/resources/file2.txt"]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"


@freeze_time("2012-01-14 12:00:01")
def test_delete_python_interface(snapshot, glo_mercator_bucket, set_env):
    random.seed(42)

    response = delete(
        pushing_entity_id=PUSHING_ENTITY_ID,
        files=MOCK_FILES,
        dataset_id="dataset1",
        product_id="product1",
    )
    assert response == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delete_cli(glo_mercator_bucket, cli_env, snapshot):
    random.seed(42)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "delete",
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
    assert "delivery" not in output
    assert output == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delete_cli_save_delivery_json(glo_mercator_bucket, cli_env, snapshot):
    random.seed(42)
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "delete",
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
        with open(json_files[0]) as f:
            delivery = json.load(f)
        assert delivery == snapshot


def test_delete_cli_no_source_exits(cli_env):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "delete",
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
