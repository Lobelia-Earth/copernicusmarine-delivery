import os
from pathlib import Path

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

    upload_operation = create_and_validate_upload_operation(
        files,
    )

    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    s3_client = get_s3_ingestion_client(
        pushing_entity_id, ingestion_bucket_name, chunk_concurrency=chunk_concurrency
    )
    delivery_id = create_delivery_id(product_id)
    put_files_result = _put_files_to_ingestion_system(
        s3_client,
        delivery_id=delivery_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operation=upload_operation,
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
    all_operations: list[Operation] = []
    ingestion_bucket_name = get_ingestion_bucket_name(
        pushing_entity_id, pushing_entities
    )
    s3_client = get_s3_ingestion_client(
        pushing_entity_id, ingestion_bucket_name, chunk_concurrency=chunk_concurrency
    )
    for operation_name, sources in operations:
        if operation_name == "delete":
            operation = create_and_validate_delete_operation(sources)
            all_operations.append(operation)
        elif operation_name == "upload":
            operation = create_and_validate_upload_operation(sources)
            all_operations.append(operation)
    all_responses: list[ResponseUpload | ResponseDelete] = []
    for operation in all_operations:
        if isinstance(operation, UploadOperation):
            put_files_result = _put_files_to_ingestion_system(
                s3_client,
                delivery_id=delivery_id,
                product_id=product_id,
                dataset_id=dataset_id,
                operation=operation,
                raise_on_error=raise_on_upload_error,
                chunk_size=chunk_size_bytes,
                max_concurrent_uploads=max_concurrent_uploads,
                dry_run=dry_run,
            )
            all_responses.append(
                ResponseUpload.create(
                    delivery_id=delivery_id,
                    result_upload=put_files_result,
                )
            )
        elif isinstance(operation, DeleteOperation):
            all_responses.append(
                ResponseDelete.create(
                    delivery_id=delivery_id, files_to_delete=operation.files
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


def create_and_validate_upload_operation(
    files: list[str],
) -> UploadOperation:
    validate_upload_files(files)
    return UploadOperation(
        files=[
            UploadFile(
                key_suffix=file,
                file_size_mb=os.path.getsize(file) // (1024 * 1024),
                checksum=None,  # ETag will be filled in after upload
                upload_start_time=None,  # will be filled in after upload
                upload_end_time=None,  # will be filled in after upload
            )
            for file in files
        ],
        operation="upload",
    )


def _put_files_to_ingestion_system(
    s3_client: S3Client,
    delivery_id: str,
    product_id: str,
    dataset_id: str,
    operation: UploadOperation,
    raise_on_error: bool,
    chunk_size: int,
    max_concurrent_uploads: int,
    dry_run: bool,
) -> PutFilesResult:
    local_path_s3_keys_mapping = get_local_path_s3_keys_mapping(
        [file.key_suffix for file in operation.files],
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

    _update_operation_with_put_results(operation, put_files_result)

    total_size = operation.total_size()
    logger.info(
        f"{'[DRY RUN]: ' if dry_run else ''}Finished uploading {len(put_files_result.successful_files)} files"
        f"for a total size of {human_readable_size(total_size)}."
    )

    return put_files_result


def _update_operation_with_put_results(
    operation: UploadOperation, put_files_result: PutFilesResult
) -> None:
    """
    TODO: add the possibility for users to abort the delivery if there are any errors. For now, we just log them and continue.

    Might be the default one.
    """
    successful_files_dict = {
        str(file.local_path): file for file in put_files_result.successful_files
    }
    errored_files_dict = {
        str(file.local_path): file for file in put_files_result.errored_files
    }
    index_files_to_remove = []
    for i, delivery_file in enumerate(operation.files):
        if delivery_file.key_suffix in successful_files_dict:
            successful_s3_file = successful_files_dict[delivery_file.key_suffix]
            delivery_file.checksum = successful_s3_file.e_tag
            delivery_file.upload_start_time = successful_s3_file.upload_start_time
            delivery_file.upload_end_time = successful_s3_file.upload_end_time
        elif delivery_file.key_suffix in errored_files_dict:
            logger.debug(
                f"Removing file {delivery_file.key_suffix} from upload operation."
            )
            index_files_to_remove.append(i)
    for index in reversed(index_files_to_remove):
        del operation.files[index]
