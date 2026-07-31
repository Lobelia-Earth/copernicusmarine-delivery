from delivery_common.domain import PushingEntities
from pusher.core_functions.domain import NoIngestionBucketError


def get_ingestion_bucket_name(
    pushing_entity_id: str, pushing_entities: PushingEntities
) -> str:
    bucket = next(
        (
            pu.bucket
            for pu in pushing_entities.pushing_entities
            if pu.name == pushing_entity_id
        ),
        None,
    )
    if bucket is None:
        raise NoIngestionBucketError(pushing_entity_id)
    return bucket


def megabytes_to_bytes(megabytes: int) -> int:
    return megabytes * 1024 * 1024


def human_readable_size(megabytes: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size_bytes = megabytes * 1024 * 1024
    index = 0

    while size_bytes >= 1024 and index < len(units) - 1:
        size_bytes /= 1024.0
        index += 1

    return f"{size_bytes:.2f} {units[index]}"
