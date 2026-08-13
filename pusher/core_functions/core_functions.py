import os
from pathlib import Path

from delivery_common.domain import (
    DeleteFile,
    DeleteOperation,
    Delivery,
    FileToUpload,
    Operation,
    OperationNames,
    ToUploadOperation,
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
    NoSuccessfulUploadsError,
    PutFilesResult,
    ResponseDelete,
    ResponseDelivery,
    ResponseUpload,
)
from pusher.core_functions.utils import (
    get_ingestion_bucket_name,
    human_readable_size,
)
from pusher.logger import logger
from pusher.s3_client import S3Client, get_s3_ingestion_client


def get_local_path_s3_keys_mapping(
    list_of_files: list[str],
    delivery_id: str,
    product_id: str,
    dataset_id: str,
) -> dict[Path, str]:
    return {
        Path(file_path): NEW_DATA_BUCKET_PATH.format(
            delivery_id=delivery_id,
            product_id=product_id,
            dataset_id=dataset_id,
            file_name=file_path,
        )
        for file_path in list_of_files
    }


def upload(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
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

    pushing_entities = fetch_pushing_entities()
    validate_delivery_ids(pushing_entity_id, product_id, dataset_id, pushing_entities)

    to_upload_operation = create_and_validate_to_upload_operation(
        files,
    )

    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    s3_client = get_s3_ingestion_client(
        pushing_entity_id, ingestion_bucket_name, chunk_concurrency=chunk_concurrency
    )
    delivery_id = create_delivery_id(product_id)
    put_files_result, upload_operation = _put_files_to_ingestion_system(
        s3_client,
        delivery_id=delivery_id,
        product_id=product_id,
        dataset_id=dataset_id,
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
    pushing_entities = fetch_pushing_entities()
    validate_delivery_ids(pushing_entity_id, product_id, dataset_id, pushing_entities)

    delete_operation = create_and_validate_delete_operation(files)

    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    s3_client = get_s3_ingestion_client(pushing_entity_id, ingestion_bucket_name)

    delivery = create_and_upload_delivery(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=[delete_operation],
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
    operations: list[tuple[OperationNames, list[str]]],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    raise_on_upload_error: bool,
    max_concurrent_uploads: int,
    chunk_size_bytes: int,
    chunk_concurrency: int,
    dry_run: bool,
) -> tuple[ResponseDelivery, Delivery]:

    pushing_entities = fetch_pushing_entities()
    validate_delivery_ids(pushing_entity_id, product_id, dataset_id, pushing_entities)

    delivery_id = create_delivery_id(product_id)
    pending_operations: list[DeleteOperation | ToUploadOperation] = []
    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    s3_client = get_s3_ingestion_client(
        pushing_entity_id, ingestion_bucket_name, chunk_concurrency=chunk_concurrency
    )
    for operation_name, sources in operations:
        if operation_name == "delete":
            operation = create_and_validate_delete_operation(sources)
            pending_operations.append(operation)
        elif operation_name == "upload":
            to_upload_operation = create_and_validate_to_upload_operation(sources)
            pending_operations.append(to_upload_operation)
    all_operations: list[Operation] = []
    all_responses: list[ResponseUpload | ResponseDelete] = []
    for operation in pending_operations:
        if isinstance(operation, DeleteOperation):
            all_operations.append(operation)
            all_responses.append(
                ResponseDelete.create(
                    delivery_id=delivery_id, files_to_delete=operation.files
                )
            )
        else:
            put_files_result, upload_operation = _put_files_to_ingestion_system(
                s3_client,
                delivery_id=delivery_id,
                product_id=product_id,
                dataset_id=dataset_id,
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
) -> ToUploadOperation:
    validate_upload_files(files)
    return ToUploadOperation(
        files=[
            FileToUpload(
                key_suffix=file,
                file_size_mb=os.path.getsize(file) // (1024 * 1024),
            )
            for file in files
        ]
    )


def _put_files_to_ingestion_system(
    s3_client: S3Client,
    delivery_id: str,
    product_id: str,
    dataset_id: str,
    to_upload_operation: ToUploadOperation,
    raise_on_error: bool,
    chunk_size: int,
    max_concurrent_uploads: int,
    dry_run: bool,
) -> tuple[PutFilesResult, UploadOperation]:
    local_path_s3_keys_mapping = get_local_path_s3_keys_mapping(
        [file.key_suffix for file in to_upload_operation.files],
        delivery_id,
        product_id,
        dataset_id,
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
        to_upload_operation, put_files_result
    )

    total_size = operation.total_size()
    logger.info(
        f"{'[DRY RUN]: ' if dry_run else ''}Finished uploading {len(put_files_result.successful_files)} files"
        f"for a total size of {human_readable_size(total_size)}."
    )

    return put_files_result, operation


def build_upload_operation_from_put_results(
    to_upload_operation: ToUploadOperation, put_files_result: PutFilesResult
) -> UploadOperation:
    """
    TODO: add the possibility for users to abort the delivery if there are any errors. For now, we just log them and continue.

    Might be the default one.
    """
    successful_files_dict = {
        str(file.local_path): file for file in put_files_result.successful_files
    }
    upload_files = []
    for file_to_upload in to_upload_operation.files:
        successful_s3_file = successful_files_dict.get(file_to_upload.key_suffix)
        if successful_s3_file is None:
            logger.debug(
                f"Removing file {file_to_upload.key_suffix} from upload operation."
            )
            continue
        upload_files.append(
            UploadFile(
                key_suffix=file_to_upload.key_suffix,
                file_size_mb=file_to_upload.file_size_mb,
                checksum=successful_s3_file.e_tag,
                upload_start_time=successful_s3_file.upload_start_time,
                upload_end_time=successful_s3_file.upload_end_time,
            )
        )
    return UploadOperation(files=upload_files, operation="upload")
