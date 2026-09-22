from pathlib import Path

import yaml
from freezegun import freeze_time

from copernicusmarine_delivery.core_functions.delivery import (
    create_delivery,
    create_delivery_id,
)
from copernicusmarine_delivery.core_functions.domain import ResponseUpload
from delivery_common.domain import (
    DeleteFile,
    DeleteOperation,
    Delivery,
    OperationNames,
    UploadFile,
    UploadOperation,
)

RESOURCES = Path("tests/resources")


# --- Models ---


def test_delivery_round_trip():
    delivery = Delivery(
        delivery_id="20240101T000000-dataset1-1234",
        pushing_entity_id="TEST-FR",
        product_id="product1",
        dataset_id="dataset1",
        operations=[],
    )
    assert delivery.model_dump()["delivery_id"] == "20240101T000000-dataset1-1234"


def test_response_upload_error_no_delivery():
    response = ResponseUpload(fatal_error="No successful uploads - no data were sent.")
    assert response.files_uploaded == []


# --- Delivery creation ---


@freeze_time("2024-03-15 12:00:01")
def test_create_delivery_id_format():
    delivery_id = create_delivery_id("dataset1")
    assert delivery_id.startswith("20240315T120001-dataset1-")
    suffix = delivery_id.split("-")[-1]
    assert suffix.isdigit() and 1000 <= int(suffix) <= 9999


@freeze_time("2024-03-15 12:00:01")
def test_create_delivery(tmp_path):
    f = tmp_path / "file.nc"
    f.write_bytes(b"x" * 1024)
    delivery_id = create_delivery_id("product1")
    delivery = create_delivery(
        pushing_entity_id="TEST-FR",
        product_id="product1",
        dataset_id="dataset1",
        operations=[
            UploadOperation(
                operation=OperationNames.upload,
                files=[
                    UploadFile(
                        key_suffix=str(f),
                        file_size_mb=43,
                        checksum="abc-1",
                        upload_start_time="2024-03-15T12:00:01+00:00",
                        upload_end_time="2024-03-15T12:00:02+00:00",
                    )
                ],
            )
        ],
        delivery_id=delivery_id,
    )
    assert delivery.pushing_entity_id == "TEST-FR"
    assert delivery.operations[0].operation == "upload"
    assert isinstance(delivery.operations[0], UploadOperation)
    assert delivery.operations[0].files[0].checksum == "abc-1"


@freeze_time("2024-03-15 12:00:01")
def test_save_delivery_and_load(tmp_path, snapshot):
    delivery_id = create_delivery_id("product1")
    delivery = create_delivery(
        pushing_entity_id="TEST-FR",
        product_id="product1",
        dataset_id="dataset1",
        operations=[
            UploadOperation(
                operation=OperationNames.upload,
                files=[
                    UploadFile(
                        key_suffix="file.nc",
                        file_size_mb=43,
                        checksum="abc-1",
                        upload_start_time="2024-03-15T12:00:01Z",
                        upload_end_time="2024-03-15T12:00:02Z",
                    )
                ],
            ),
            DeleteOperation(
                operation=OperationNames.delete,
                files=[
                    DeleteFile(
                        key_suffix="file2.nc",
                    )
                ],
            ),
        ],
        delivery_id=delivery_id,
    )
    delivery_path = tmp_path / "delivery.yaml"
    # dump
    with open(delivery_path, "w") as f:
        yaml.dump(delivery.model_dump(mode="json"), f)

    # load
    with open(delivery_path, "r") as f:
        loaded_delivery_data = yaml.safe_load(f)
    loaded_delivery = Delivery.model_validate(loaded_delivery_data)
    assert loaded_delivery.model_dump_json(indent=2) == snapshot
