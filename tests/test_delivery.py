import random

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
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        chunk_concurrency=CHUNK_CONCURRENCY,
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
            max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
            chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
            chunk_concurrency=CHUNK_CONCURRENCY,
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
