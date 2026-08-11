import glob
import json
import random

import pytest
import yaml
from click.testing import CliRunner
from freezegun import freeze_time

from pusher import InvalidDeliveryIdsError
from pusher.command_line_interface import cli
from pusher.core_functions.core_functions import delete
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
def test_delete_python_interface(
    snapshot,
    glo_mercator_bucket,
    set_env,
    skip_delivery_ids_validation,
    ingestion_service,
):
    random.seed(42)

    response, delivery = delete(
        pushing_entity_id=PUSHING_ENTITY_ID,
        files=MOCK_FILES,
        dataset_id="dataset1",
        product_id="product1",
        dry_run=False,
    )
    assert response.model_dump_json(indent=2) == snapshot
    assert delivery is not None
    assert delivery.model_dump_json(indent=2) == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delete_cli(
    glo_mercator_bucket,
    cli_env,
    snapshot,
    skip_delivery_ids_validation,
    ingestion_service,
):
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
    assert result.output.strip() == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delete_cli_save_delivery_json(
    glo_mercator_bucket,
    cli_env,
    snapshot,
    skip_delivery_ids_validation,
    ingestion_service,
):
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
        assert result.output.strip() == snapshot

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


def test_delete_raises_on_invalid_delivery_ids(monkeypatch):
    monkeypatch.setattr(
        S3Client, "get_file_stream", lambda self, **kwargs: _UNKNOWN_ENTITY_YAML
    )

    with pytest.raises(InvalidDeliveryIdsError) as exc_info:
        delete(
            pushing_entity_id=PUSHING_ENTITY_ID,
            files=MOCK_FILES,
            dataset_id="dataset1",
            product_id="product1",
            dry_run=False,
        )
    assert f"{PUSHING_ENTITY_ID} is not a valid registered Pushing Entity" in str(
        exc_info.value
    )
