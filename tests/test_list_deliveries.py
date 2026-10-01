import json

import httpx
from click.testing import CliRunner
from freezegun import freeze_time

from copernicusmarine_delivery.command_line_interface import cli
from copernicusmarine_delivery.core_functions import delivery as delivery_module
from copernicusmarine_delivery.core_functions.constants import (
    CHUNK_CONCURRENCY,
    DEFAULT_CHUNK_SIZE_MB,
    MAX_CONCURRENT_UPLOADS,
)
from copernicusmarine_delivery.core_functions.core_functions import upload
from copernicusmarine_delivery.core_functions.delivery import get_deliveries
from copernicusmarine_delivery.core_functions.utils import megabytes_to_bytes
from copernicusmarine_delivery.python_interface import list_deliveries

MOCK_FILES = [
    "tests/resources/dataset1/file1.txt",
    "tests/resources/dataset1/file2.txt",
]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"


def _upload(files: list[str], dataset_id: str, product_id: str, anchor: str | None):
    return upload(
        files=files,
        dataset_id=dataset_id,
        product_id=product_id,
        anchor=anchor,
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
    skip_delivery_ids_validation,
    ingestion_service,
):
    # Create several deliveries for the same pushing entity.
    _upload(
        [MOCK_FILES[0]], dataset_id="dataset1", product_id="product1", anchor="dataset1"
    )
    _upload(
        [MOCK_FILES[1]], dataset_id="dataset2", product_id="product1", anchor="dataset1"
    )
    _upload(MOCK_FILES, dataset_id="dataset1", product_id="product1", anchor="dataset1")

    deliveries = list_deliveries()

    assert len(deliveries) == 3
    dumped = json.dumps(
        [delivery.model_dump(by_alias=True) for delivery in deliveries],
        indent=2,
    )
    assert dumped == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_list_deliveries_cli(
    glo_mercator_bucket,
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
        args = ["upload"]
        for source in sources:
            args += ["--source", source]
        args += [
            "--dataset-id",
            dataset_id,
            "--product-id",
            "product1",
            "--anchor",
            "dataset1",
        ]
        upload_result = runner.invoke(cli, args)
        assert upload_result.exit_code == 0, upload_result.output

    result = runner.invoke(
        cli,
        ["list-deliveries"],
    )
    assert result.exit_code == 0, result.output.strip()
    assert result.output.strip() == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_get_deliveries_sends_timeframe_as_created_after_param(monkeypatch):
    """The timeframe must be translated into a `created_after` query param so the
    API performs the filtering."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"deliveries": []})

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(delivery_module, "http_client", mock_client)
    monkeypatch.setattr(
        delivery_module, "fetch_keycloak_token", lambda config: "test-token"
    )

    get_deliveries(config=None, timeframe="w")  # type: ignore[arg-type]

    # now (frozen) minus one week, in ISO 8601 UTC.
    assert captured["params"] == {"created_after": "2012-01-07T12:00:01Z"}
