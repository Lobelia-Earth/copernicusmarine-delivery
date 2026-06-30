from pathlib import Path

from pusher.core_functions.constants import PUSHING_ENTITIES_PATH
from pusher.core_functions.models import (
    InvalidDeliveryIds,
    InvalidFile,
    PushingEntities,
    ValidateResult,
)
from pusher.logger import logger
from pusher.s3_client import get_s3_metadata_client

SUPPORTED_FILE_EXTENTIONS = {".txt", ".shp", ".zip", ".nc"}


def file_exists(file_path: Path) -> bool:
    return file_path.exists()


def file_not_empty(file_path: Path) -> bool:
    return file_path.stat().st_size > 0


def file_type_supported(file_path: Path) -> bool:
    return file_path.suffix in SUPPORTED_FILE_EXTENTIONS


def validate_upload_file_requirements(files: list[Path]) -> ValidateResult:
    valid_files = []
    invalid_files = []
    for file in files:
        if not file_exists(file):
            invalid_files.append(
                InvalidFile(path=file, reason="File path does not exist.")
            )
            continue
        if not file_not_empty(file):
            invalid_files.append(InvalidFile(path=file, reason="File is empty."))
            continue
        if not file_type_supported(file):
            # Just a warning for now
            logger.warning(
                "File extension is not supported. There might be some issues downstream. "
                f"Supported file extensions are: {SUPPORTED_FILE_EXTENTIONS}"
            )
            # invalid_files.append(
            #     InvalidFile(
            #         path=file,
            #         reason=f"File extension not supported. Supported extensions are: {SUPPORTED_FILE_EXTENTIONS}",
            #     )
            # )
            # continue
        valid_files.append(file)
    return ValidateResult(files_valid=valid_files, files_invalid=invalid_files)


def validate_delivery_ids(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    pushing_entities: PushingEntities | None = None,
) -> InvalidDeliveryIds | None:
    if not pushing_entities:
        # TODO Should we cache this somehow?
        metadata_s3_client = get_s3_metadata_client()
        pushing_entities_raw = metadata_s3_client.get_file(
            path_to_file=PUSHING_ENTITIES_PATH
        )
        pushing_entities = PushingEntities.from_stream(pushing_entities_raw)

    valid_pushing_entity = next(
        (e for e in pushing_entities.pushing_entities if e.name == pushing_entity_id),
        None,
    )
    if not valid_pushing_entity:
        return InvalidDeliveryIds(
            reason=f"{pushing_entity_id} is not a valid registered Pushing Entity"
        )
    valid_product = next(
        (
            product
            for product in valid_pushing_entity.products
            if product.product_id == product_id
        ),
        None,
    )
    if not valid_product:
        return InvalidDeliveryIds(
            reason=f"{product_id} is not a valid Product ID for {pushing_entity_id}"
        )
    if dataset_id not in valid_product.datasets:
        return InvalidDeliveryIds(
            reason=f"{dataset_id} is not a valid Dataset ID for any Product for {pushing_entity_id}"
        )
