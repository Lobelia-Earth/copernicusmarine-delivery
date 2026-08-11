from datetime import datetime
from random import randint

from delivery_common.domain import Delivery, Operation
from pusher.environment_variables import INGESTION_SERVICE_URL
from pusher.http_client import http_client
from pusher.logger import logger


def create_delivery(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    operations: list[Operation],
    delivery_id: str,
) -> Delivery:
    return Delivery(
        delivery_id=delivery_id,
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=operations,
    )


def create_delivery_id(product_id: str) -> str:
    timestamp_format = "%Y%m%dT%H%M%S"
    iso_timestamp_with_seconds = datetime.now().strftime(timestamp_format)
    random_number = randint(1000, 9999)
    return f"{iso_timestamp_with_seconds}-{product_id}-{random_number}"


def create_and_upload_delivery(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    operations: list[Operation],
    dry_run: bool,
    delivery_id: str | None = None,
) -> Delivery:
    if not delivery_id:
        delivery_id = create_delivery_id(product_id)
    delivery = create_delivery(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=operations,
        delivery_id=delivery_id,
    )
    if not dry_run:
        logger.debug(
            f"POSTing delivery to ingestion service at {INGESTION_SERVICE_URL}/delivery"
        )
        response = http_client.post(
            f"{INGESTION_SERVICE_URL}/delivery",
            json=delivery.model_dump(by_alias=True),
        )
        response.raise_for_status()

    return delivery


def get_delivery(
    delivery_id: str,
    pushing_entity_id: str,
) -> Delivery:
    response = http_client.get(
        f"{INGESTION_SERVICE_URL}/delivery",
        params={
            "pushing_entity_id": pushing_entity_id,
        },
    )
    response.raise_for_status()
    for delivery_data in response.json()["deliveries"]:
        if delivery_data["delivery_id"] == delivery_id:
            return Delivery(**delivery_data)

    raise ValueError(
        f"Delivery with id {delivery_id} not found for pushing entity {pushing_entity_id}."
    )
