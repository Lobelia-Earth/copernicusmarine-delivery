import os
from pathlib import Path
from typing import Sequence

from delivery_common.domain import (
    DeleteFile,
    DeleteOperation,
    Delivery,
    Operation,
    OperationNames,
    UploadFile,
    UploadOperation,
)
from delivery_common.validation import validate_delivery_ids
from pusher.core_functions.constants import (
    NEW_DATA_BUCKET_PATH,
)
from pusher.core_functions.delivery import (
    create_and_upload_delivery,
    create_delivery_id,
)
from pusher.core_functions.delivery_validator import (
    fetch_pushing_entities,
    validate_delete_files,
    validate_upload_files,
)
from pusher.core_functions.domain import (
    Delete,
    FileToUpload,
    NoSuccessfulUploadsError,
    PutFilesResult,
    ResponseDelete,
    ResponseDelivery,
    ResponseUpload,
    ToUploadOperation,
    Upload,
)
from pusher.core_functions.utils import (
    get_ingestion_bucket_name,
    human_readable_size,
)
from pusher.environment_variables import (
    COPERNICUSMARINE_PASSWORD,
    COPERNICUSMARINE_USERNAME,
    INGESTION_SERVICE_URL,
)
from pusher.http_client import http_client
from pusher.logger import logger
from pusher.s3_client import S3Client, get_s3_ingestion_client


def strip_to_anchor(local_path: str, anchor: str | None = None) -> str:
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


def get_local_path_s3_keys_mapping(
    list_of_files: list[str],
    delivery_id: str,
    product_id: str,
    dataset_id: str,
    anchor: str | None,
) -> dict[Path, str]:
    return {
        Path(file_path): NEW_DATA_BUCKET_PATH.format(
            delivery_id=delivery_id,
            product_id=product_id,
            dataset_id=dataset_id,
            file_name=strip_to_anchor(file_path, anchor),
        )
        for file_path in list_of_files
    }


def upload(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
    anchor: str | None,
    raise_on_upload_error: bool,
    max_concurrent_uploads: int,
    chunk_size_bytes: int,
    chunk_concurrency: int,
    dry_run: bool,
) -> tuple[ResponseUpload, Delivery]:
    """
    1. Quick-validate all files, keep track of invalid files. If no valid files, return early.
    2. Try and upload all files given. Keep track of errored files. If no successful uploads, return early.
    3. Create Delivery with successful ones (in the future there might be a flag to abort if errors). Use ETag as checksum.
    """

    logger.debug(
        f"Creating delivery for:\n\tPU: {pushing_entity_id}\n\tProduct ID: {product_id}\n\tDataset ID: {dataset_id}"
        f"\n\tFiles: {[Path(file).name for file in files]}"
    )
    token = login()

    pushing_entities = fetch_pushing_entities()
    validate_delivery_ids(pushing_entity_id, product_id, dataset_id, pushing_entities)

    to_upload_operation = create_and_validate_to_upload_operation(
        files,
        dataset_id,
        product_id,
        anchor,
    )

    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    s3_client = get_s3_ingestion_client(
        pushing_entity_id,
        ingestion_bucket_name,
        token=token,
        chunk_concurrency=chunk_concurrency,
    )
    delivery_id = create_delivery_id(product_id)
    put_files_result, upload_operation = _put_files_to_ingestion_system(
        s3_client,
        delivery_id=delivery_id,
        product_id=product_id,
        dataset_id=dataset_id,
        anchor=anchor,
        to_upload_operation=to_upload_operation,
        raise_on_error=raise_on_upload_error,
        chunk_size=chunk_size_bytes,
        max_concurrent_uploads=max_concurrent_uploads,
        dry_run=dry_run,
    )

    delivery = create_and_upload_delivery(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=[upload_operation],
        delivery_id=delivery_id,
        token=token,
        dry_run=dry_run,
    )

    return (
        ResponseUpload.create(
            delivery_id=delivery.delivery_id,
            result_upload=put_files_result,
        ),
        delivery,
    )


def delete(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
    dry_run: bool,
) -> tuple[ResponseDelete, Delivery]:
    """
    Create delivery with deletes and push it. Deletes happen in main S3; toolbox has no direct access.
    """
    logger.debug(
        f"Creating delivery for:\n\tPU: {pushing_entity_id}\n\tProduct ID: {product_id}\n\tDataset ID: {dataset_id}"
        f"\n\tFiles: {files}"
    )
    token = login()
    pushing_entities = fetch_pushing_entities()
    validate_delivery_ids(pushing_entity_id, product_id, dataset_id, pushing_entities)

    delete_operation = create_and_validate_delete_operation(files)

    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    s3_client = get_s3_ingestion_client(
        pushing_entity_id, ingestion_bucket_name, token=token
    )

    delivery = create_and_upload_delivery(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=[delete_operation],
        token=token,
        dry_run=dry_run,
    )
    return (
        ResponseDelete.create(
            delivery_id=delivery.delivery_id, files_to_delete=delete_operation.files
        ),
        delivery,
    )


def create_and_validate_delete_operation(
    files: list[str],
) -> DeleteOperation:
    validate_delete_files(files)
    return DeleteOperation(
        files=[DeleteFile(key_suffix=file) for file in files],
    )


def delivery(
    operations: Sequence[Upload | Delete],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    raise_on_upload_error: bool,
    max_concurrent_uploads: int,
    chunk_size_bytes: int,
    chunk_concurrency: int,
    dry_run: bool,
) -> tuple[ResponseDelivery, Delivery]:
    token = login()

    pushing_entities = fetch_pushing_entities()
    validate_delivery_ids(pushing_entity_id, product_id, dataset_id, pushing_entities)

    delivery_id = create_delivery_id(product_id)
    pending_operations: list[DeleteOperation | ToUploadOperation] = []
    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    s3_client = get_s3_ingestion_client(
        pushing_entity_id,
        ingestion_bucket_name,
        chunk_concurrency=chunk_concurrency,
        token=token,
    )
    for operation in operations:
        match operation:
            case Delete():
                operation = create_and_validate_delete_operation(operation.files)
                pending_operations.append(operation)
            case Upload():
                to_upload_operation = create_and_validate_to_upload_operation(
                    operation.files, dataset_id, product_id, operation.anchor
                )
                pending_operations.append(to_upload_operation)
    all_operations: list[Operation] = []
    all_responses: list[ResponseUpload | ResponseDelete] = []
    for operation in pending_operations:
        match operation:
            case DeleteOperation():
                all_operations.append(operation)
                all_responses.append(
                    ResponseDelete.create(
                        delivery_id=delivery_id, files_to_delete=operation.files
                    )
                )
            case ToUploadOperation():
                put_files_result, upload_operation = _put_files_to_ingestion_system(
                    s3_client,
                    delivery_id=delivery_id,
                    product_id=product_id,
                    dataset_id=dataset_id,
                    anchor=operation.anchor,
                    to_upload_operation=operation,
                    raise_on_error=raise_on_upload_error,
                    chunk_size=chunk_size_bytes,
                    max_concurrent_uploads=max_concurrent_uploads,
                    dry_run=dry_run,
                )
                all_operations.append(upload_operation)
                all_responses.append(
                    ResponseUpload.create(
                        delivery_id=delivery_id,
                        result_upload=put_files_result,
                    )
                )

    delivery = create_and_upload_delivery(
        pushing_entity_id,
        product_id,
        dataset_id,
        all_operations,
        dry_run,
        token=token,
        delivery_id=delivery_id,
    )
    return (
        ResponseDelivery.create(
            delivery_id=delivery_id, operations_responses=all_responses
        ),
        delivery,
    )


def create_and_validate_to_upload_operation(
    files: list[str],
    dataset_id: str,
    product_id: str,
    anchor: str | None,
) -> ToUploadOperation:
    validate_upload_files(files, dataset_id, product_id, anchor)
    return ToUploadOperation(
        files=[
            FileToUpload(
                local_path=file,
                file_size_mb=os.path.getsize(file) // (1024 * 1024),
            )
            for file in files
        ],
        anchor=anchor,
    )


def _put_files_to_ingestion_system(
    s3_client: S3Client,
    delivery_id: str,
    product_id: str,
    dataset_id: str,
    anchor: str | None,
    to_upload_operation: ToUploadOperation,
    raise_on_error: bool,
    chunk_size: int,
    max_concurrent_uploads: int,
    dry_run: bool,
) -> tuple[PutFilesResult, UploadOperation]:
    local_path_s3_keys_mapping = get_local_path_s3_keys_mapping(
        [file.local_path for file in to_upload_operation.files],
        delivery_id,
        product_id,
        dataset_id,
        anchor,
    )
    put_files_result = s3_client.upload_multiple_files(
        local_path_s3_keys_mapping,
        raise_on_error=raise_on_error,
        chunk_size=chunk_size,
        max_concurrent_uploads=max_concurrent_uploads,
        dry_run=dry_run,
    )
    if not put_files_result.successful_files:
        raise NoSuccessfulUploadsError(put_files_result.errored_files)

    operation = build_upload_operation_from_put_results(
        to_upload_operation, put_files_result, dataset_id
    )

    total_size = operation.total_size()
    logger.info(
        f"{'[DRY RUN]: ' if dry_run else ''}Finished uploading {len(put_files_result.successful_files)} files"
        f"for a total size of {human_readable_size(total_size)}."
    )

    return put_files_result, operation


def build_upload_operation_from_put_results(
    to_upload_operation: ToUploadOperation,
    put_files_result: PutFilesResult,
    dataset_id: str,
) -> UploadOperation:
    """
    TODO: add the possibility for users to abort the delivery if there are any errors. For now, we just log them and continue.

    Might be the default one.

    `dataset_id` is used as an anchor on the S3 Path returned by `put_files_result` to trim up to the file name.
    The S3 Path in the ingestion bucket is a temporary one (files will be removed from there once uploaded to MDS).
    Such S3 Path then would not add much relevant information to the user.
    """
    successful_files_dict = {
        str(file.local_path): file for file in put_files_result.successful_files
    }
    upload_files = []
    for file_to_upload in to_upload_operation.files:
        successful_s3_file = successful_files_dict.get(file_to_upload.local_path)
        if successful_s3_file is None:
            logger.debug(
                f"Removing file {file_to_upload.local_path} from upload operation."
            )
            continue
        upload_files.append(
            UploadFile(
                key_suffix=strip_to_anchor(
                    successful_s3_file.ingestion_system_s3_path, anchor=dataset_id
                ),
                file_size_mb=file_to_upload.file_size_mb,
                checksum=successful_s3_file.e_tag,
                upload_start_time=successful_s3_file.upload_start_time,
                upload_end_time=successful_s3_file.upload_end_time,
            )
        )
    return UploadOperation(files=upload_files, operation=OperationNames.upload)


def login() -> str:
    config_response = http_client.get(f"{INGESTION_SERVICE_URL}/.well-known/config")

    config_response.raise_for_status()

    config = config_response.json()
    oidc_provider_url = config["oidc_config"]["oidc_provider_url"]

    discovery_response = http_client.get(
        f"https://{oidc_provider_url}/.well-known/openid-configuration"
    )
    discovery_response.raise_for_status()

    token_endpoint = discovery_response.json()["token_endpoint"]
    token_response = http_client.post(
        token_endpoint,
        data={
            "grant_type": config["oidc_config"]["grant_type"],
            "client_id": config["oidc_config"]["oidc_client_id"],
            "username": COPERNICUSMARINE_USERNAME,
            "password": COPERNICUSMARINE_PASSWORD,
            "scope": config["oidc_config"]["scope"],
        },
    )
    token_response.raise_for_status()
    return token_response.json()["access_token"]
