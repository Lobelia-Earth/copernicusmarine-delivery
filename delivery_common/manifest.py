from datetime import datetime
from random import randint

from delivery_common.domain import Manifest, Operation, now_in_utc_isoformat


def create_manifest(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    operations: list[Operation],
    manifest_id: str,
) -> Manifest:
    return Manifest(
        manifest_id=manifest_id,
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=operations,
        creation_time=now_in_utc_isoformat(),
    )


def create_manifest_id(product_id: str) -> str:
    timestamp_format = "%Y%m%dT%H%M%S"
    iso_timestamp_with_seconds = datetime.now().strftime(timestamp_format)
    random_number = randint(1000, 9999)
    return f"{iso_timestamp_with_seconds}-{product_id}-{random_number}"
