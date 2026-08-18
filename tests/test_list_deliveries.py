import json

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
from pusher.python_interface import list_deliveries

MOCK_FILES = ["tests/resources/file1.txt", "tests/resources/file2.txt"]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"


def _upload(files: list[str], dataset_id: str, product_id: str):
    return upload(
        pushing_entity_id=PUSHING_ENTITY_ID,
        files=files,
        dataset_id=dataset_id,
        product_id=product_id,
        raise_on_upload_error=False,
        max_concurrent_uploads=MAX_CONCURRENT_UPLOADS,
        chunk_size_bytes=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        chunk_concurrency=CHUNK_CONCURRENCY,
        dry_run=False,
    )


@freeze_time("2012-01-14 12:00:01")
def test_list_deliveries_python_interface(
    snapshot,
    glo_mercator_bucket,
    set_env,
    skip_delivery_ids_validation,
    ingestion_service,
):
    # Create several deliveries for the same pushing entity.
    _upload([MOCK_FILES[0]], dataset_id="dataset1", product_id="product1")
    _upload([MOCK_FILES[1]], dataset_id="dataset2", product_id="product1")
    _upload(MOCK_FILES, dataset_id="dataset1", product_id="product1")

    deliveries = list_deliveries(pushing_entity_id=PUSHING_ENTITY_ID)

    assert len(deliveries) == 3
    dumped = json.dumps(
        [delivery.model_dump(by_alias=True) for delivery in deliveries],
        indent=2,
    )
    assert dumped == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_list_deliveries_cli(
    glo_mercator_bucket,
    cli_env,
    snapshot,
    skip_delivery_ids_validation,
    ingestion_service,
):
    runner = CliRunner()

    # Create several deliveries for the same pushing entity.
    uploads = [
        ([MOCK_FILES[0]], "dataset1"),
        ([MOCK_FILES[1]], "dataset2"),
        (MOCK_FILES, "dataset1"),
    ]
    for sources, dataset_id in uploads:
        args = ["upload", "--pushing-entity-id", PUSHING_ENTITY_ID]
        for source in sources:
            args += ["--source", source]
        args += ["--dataset-id", dataset_id, "--product-id", "product1"]
        upload_result = runner.invoke(cli, args, env=cli_env)
        assert upload_result.exit_code == 0, upload_result.output

    result = runner.invoke(
        cli,
        ["list-deliveries", "--pushing-entity-id", PUSHING_ENTITY_ID],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output.strip()
    assert result.output.strip() == snapshot
