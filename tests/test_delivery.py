import random

from click.testing import CliRunner
from freezegun import freeze_time

from pusher.command_line_interface import cli
from pusher.core_functions.core_functions import delivery

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
    )
    assert response.model_dump_json(indent=2) == snapshot
    assert manifest is not None
    assert manifest.model_dump_json(indent=2) == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delivery_early_exit_with_validation_error(
    snapshot, glo_mercator_bucket, set_env, skip_delivery_ids_validation
):
    random.seed(42)
    operations = [("delete", MOCK_FILES), ("upload", MOCK_FILES + ["extra_file.txt"])]

    response, manifest = delivery(
        operations=operations,  # type: ignore
        pushing_entity_id=PUSHING_ENTITY_ID,
        dataset_id="dataset1",
        product_id="product1",
    )
    assert response.model_dump_json(indent=2) == snapshot
    assert manifest is None


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
