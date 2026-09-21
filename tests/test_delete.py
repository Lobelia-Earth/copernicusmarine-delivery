import glob
import json

import pytest
import yaml
from click.testing import CliRunner
from freezegun import freeze_time

from pusher import InvalidDeliveryIdsError
from pusher.command_line_interface import cli
from pusher.core_functions.core_functions import delete

MOCK_FILES = ["tests/resources/file1.txt", "tests/resources/file2.txt"]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"
PRODUCT_ID = "GLOBAL_ANALYSISFORECAST_BGC_001_028"
DATASET_ID = "cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m_202311"

_UNKNOWN_ENTITY_YAML = yaml.dump(
    {
        "pushing-entities": [
            {
                "name": "OTHER-ENTITY",
                "bucket": "mdl-ing-other-entity",
                "products": [{"name": "product1", "datasets": [DATASET_ID]}],
            }
        ]
    }
).encode()


@freeze_time("2012-01-14 12:00:01")
def test_delete_python_interface(
    snapshot,
    glo_mercator_bucket,
    skip_delivery_ids_validation,
    ingestion_service,
):

    response, delivery = delete(
        pushing_entity_id=PUSHING_ENTITY_ID,
        files=MOCK_FILES,
        dataset_id=DATASET_ID,
        product_id=PRODUCT_ID,
        dry_run=False,
    )
    assert response.model_dump_json(indent=2) == snapshot
    assert delivery is not None
    assert delivery.model_dump_json(indent=2) == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delete_cli(
    glo_mercator_bucket,
    snapshot,
    skip_delivery_ids_validation,
    ingestion_service,
):
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
            DATASET_ID,
            "--product-id",
            PRODUCT_ID,
        ],
    )
    assert result.exit_code == 0
    assert result.output.strip() == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delete_cli_save_delivery_json(
    glo_mercator_bucket,
    snapshot,
    skip_delivery_ids_validation,
    ingestion_service,
):
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
                DATASET_ID,
                "--product-id",
                PRODUCT_ID,
                "--save-delivery-json",
            ],
        )
        assert result.exit_code == 0
        assert result.output.strip() == snapshot

        json_files = glob.glob("*.json")
        assert len(json_files) == 1
        with open(json_files[0]) as f:
            delivery = json.load(f)
        assert delivery == snapshot


def test_delete_cli_no_source_exits():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "delete",
            "--pushing-entity-id",
            PUSHING_ENTITY_ID,
            "--dataset-id",
            DATASET_ID,
            "--product-id",
            PRODUCT_ID,
        ],
    )
    assert result.exit_code == 1


def test_delete_raises_on_invalid_delivery_ids(monkeypatch, ingestion_service):

    with pytest.raises(InvalidDeliveryIdsError) as exc_info:
        delete(
            pushing_entity_id=PUSHING_ENTITY_ID,
            files=MOCK_FILES,
            dataset_id=DATASET_ID,
            product_id="Made-Up-Product-Id",
            dry_run=False,
        )
    assert (
        f"Made-Up-Product-Id is not a valid Product ID for {PUSHING_ENTITY_ID}"
        in str(exc_info.value)
    )
