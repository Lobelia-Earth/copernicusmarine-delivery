from pathlib import Path

from copernicusmarine_delivery.core_functions.domain import NoIngestionBucketError
from delivery_common.domain import PushingEntities


def local_path_to_key_suffix(local_path: str, anchor: str | None = None) -> str:
    """Anchor is not enforced. If it is None, the logic does not check whether local path is absolute
    because these are rejected if no anchor is given in the validation.
    If `anchor` is set, it has already been checked for containment in `validate_upload_files`, so indexing is safe.
    """
    if anchor is None:
        return local_path
    parts = Path(local_path).parts
    idx = parts.index(anchor)
    stripped_path = str(Path(*parts[idx + 1 :]))
    return stripped_path


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
