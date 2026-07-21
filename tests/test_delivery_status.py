import json
import random

from click.testing import CliRunner
from freezegun import freeze_time

from pusher.command_line_interface import cli
from pusher.core_functions.constants import (
    CHUNK_CONCURRENCY,
    CHUNK_SIZE,
    MAX_CONCURRENT_UPLOADS,
)
from pusher.core_functions.core_functions import upload
from pusher.python_interface import delivery_status

MOCK_FILES = ["tests/resources/file1.txt", "tests/resources/file2.txt"]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"


@freeze_time("2012-01-14 12:00:01")
def test_delivery_status_python_interface(
    snapshot, glo_mercator_bucket, set_env, skip_delivery_ids_validation
):
    random.seed(42)

    _, manifest = upload(
        pushing_entity_id=PUSHING_ENTITY_ID,
        files=MOCK_FILES,
        dataset_id="dataset1",
        product_id="product1",
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_size_bytes=CHUNK_SIZE,
        chunk_concurrency=CHUNK_CONCURRENCY,
    )
    assert manifest is not None

    result = delivery_status(
        delivery_id=manifest.manifest_id,
        pushing_entity_id=PUSHING_ENTITY_ID,
        product_id="product1",
        dataset_id="dataset1",
    )
    assert result.model_dump_json(indent=2) == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delivery_status_cli(
    glo_mercator_bucket, cli_env, snapshot, skip_delivery_ids_validation
):
    random.seed(42)
    runner = CliRunner()

    # First, upload files to create a delivery
    upload_result = runner.invoke(
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
    assert upload_result.exit_code == 0
    upload_output = json.loads(upload_result.output)
    delivery_id = upload_output["delivery_id"]

    # Now check the delivery status
    result = runner.invoke(
        cli,
        [
            "status",
            "--delivery-id",
            delivery_id,
            "--pushing-entity-id",
            PUSHING_ENTITY_ID,
            "--product-id",
            "product1",
            "--dataset-id",
            "dataset1",
        ],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output.strip()
    assert result.output.strip() == snapshot
