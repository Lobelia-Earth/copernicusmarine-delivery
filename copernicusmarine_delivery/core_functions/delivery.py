from __future__ import annotations

from datetime import datetime, timedelta, timezone
from random import randint
from typing import TYPE_CHECKING, Literal

from copernicusmarine_delivery.auth import fetch_keycloak_token
from copernicusmarine_delivery.http_client import http_client
from copernicusmarine_delivery.logger import logger
from delivery_common.domain import Delivery, Operation, datetime_to_iso_format

if TYPE_CHECKING:
    from copernicusmarine_delivery.context import ServiceContext

TIMEFRAME_MAPPING = {
    "s": timedelta(seconds=1),
    "m": timedelta(minutes=1),
    "h": timedelta(hours=1),
    "d": timedelta(days=1),
    "w": timedelta(weeks=1),
    "mo": timedelta(days=30),
    "y": timedelta(days=365),
}

TimeframeLiteral = Literal["s", "m", "h", "d", "w", "mo", "y", "all"]


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
    ctx: ServiceContext,
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
        logger.debug(f"POSTing delivery to ingestion service at {ctx.ingestion_service_url}/delivery")
        response = http_client.post(
            f"{ctx.ingestion_service_url}/delivery",
            json=delivery.model_dump(by_alias=True),
            headers={"Authorization": f"Bearer {fetch_keycloak_token(ctx)}"},
        )
        response.raise_for_status()

    return delivery


def get_deliveries(
    ctx: ServiceContext,
    delivery_id: str | None = None,
    timeframe: TimeframeLiteral | None = None,
) -> list[Delivery]:
    params = {}
    if delivery_id:
        params["delivery_id"] = delivery_id
    if timeframe and (create_after := _timeframe_to_created_after(timeframe)):
        params["created_after"] = create_after
    if ctx.on_behalf_of:
        params["on_behalf_of"] = ctx.on_behalf_of

    response = http_client.get(
        f"{ctx.ingestion_service_url}/delivery",
        headers={"Authorization": f"Bearer {fetch_keycloak_token(ctx)}"},
        params=params,
    )
    response.raise_for_status()

    return sorted(
        [Delivery(**delivery_data) for delivery_data in response.json()["deliveries"]],
        key=lambda d: d.delivery_id,
        reverse=True,
    )


def _timeframe_to_created_after(timeframe: TimeframeLiteral) -> str | None:
    now = datetime.now(tz=timezone.utc)
    if timeframe == "all":
        return None
    elif timeframe in TIMEFRAME_MAPPING:
        created_after = now - TIMEFRAME_MAPPING[timeframe]
    else:
        raise ValueError(
            f"Unsupported timeframe: {timeframe}. Available options are: {list(TIMEFRAME_MAPPING.keys()) + ['all']}"
        )
    return datetime_to_iso_format(created_after)
