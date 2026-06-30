import os
from pathlib import Path

from pusher.core_functions.constants import NEW_DATA_BUCKET_PATH, NEW_MANIFESTS_PATH
from pusher.core_functions.delivery_validator import (
    upload_files_validation,
    validate_delivery_ids,
)
from pusher.core_functions.manifests_helper import create_manifest, create_manifest_id
from pusher.core_functions.models import (
    Manifest,
    ManifestFile,
    Operation,
    OperationNames,
    PutFilesResult,
    ResponseDelete,
    ResponseDelivery,
    ResponseUpload,
    UploadValidationResult,
)
from pusher.logger import logger
from pusher.s3_client import S3Client, get_s3_ingestion_client


def get_upload_bucket_keys_from_local_files(
    list_of_files: list[Path],
    manifest_id: str,
    product_id: str,
    dataset_id: str,
) -> dict[Path, str]:
    return {
        Path(file_path): NEW_DATA_BUCKET_PATH.format(
            manifest_id=manifest_id,
            product_id=product_id,
            dataset_id=dataset_id,
            file_name=file_path.name,
        )
        for file_path in list_of_files
    }


def get_manifest_destination_key(manifest_id: str) -> str:
    return NEW_MANIFESTS_PATH.format(manifest_id=manifest_id)


def upload(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
    max_concurrent_uploads: int,
) -> tuple[ResponseUpload, Manifest | None]:
    """
    1. Quick-validate all files, keep track of invalid files. If no valid files, return early.
    2. Try and upload all files given. Keep track of errored files. If no successful uploads, return early.
    3. Create Manifest with successful ones (in the future there might be a flag to abort if errors). Use ETag as checksum.
    """

    logger.debug(
        f"Creating release for:\n\tPU: {pushing_entity_id}\n\tProduct ID: {product_id}\n\tDataset ID: {dataset_id}"
        f"\n\tFiles: {[Path(file).name for file in files]}"
    )

    invalid_delivery_ids_response = validate_delivery_ids(
        pushing_entity_id, product_id, dataset_id
    )
    if invalid_delivery_ids_response:
        logger.error(
            "The ids provided for this delivery did not match our records, "
            f"see: {invalid_delivery_ids_response.reason}"
        )
        return (
            ResponseUpload.create_from_fatal_error(
                invalid_delivery_ids_response.reason
            ),
            None,
        )

    upload_operation, validation_result = create_upload_operation(
        [Path(file_) for file_ in files]
    )

    if not validation_result.files_valid:
        no_valid_files_fatal_error_response = (
            "No file passed the validation. No manifest will be created."
        )
        logger.error(no_valid_files_fatal_error_response)
        return (
            ResponseUpload.create_from_fatal_error(no_valid_files_fatal_error_response),
            None,
        )

    s3_client = get_s3_ingestion_client(pushing_entity_id)
    manifest_id = create_manifest_id(product_id)
    put_files_result = _put_files_to_ingestion_system(
        s3_client,
        manifest_id=manifest_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operation=upload_operation,
        max_concurrent_uploads=max_concurrent_uploads,
    )

    if not put_files_result.successful_files:
        no_valid_files_fatal_error_response = (
            "No successful uploads - no data were sent."
        )
        logger.error(no_valid_files_fatal_error_response)
        return (
            ResponseUpload.create_from_fatal_error(no_valid_files_fatal_error_response),
            None,
        )
    _update_operation_with_put_results(upload_operation, put_files_result)

    manifest = _create_and_upload_manifest(
        s3_client,
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=[upload_operation],
        manifest_id=manifest_id,
    )

    return (
        ResponseUpload.create(
            delivery_id=manifest.manifest_id,
            result_validation=validation_result,
            result_upload=put_files_result,
        ),
        manifest,
    )


def delete(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
) -> tuple[ResponseDelete, Manifest | None]:
    """
    Create manifest with deletes and push it. Deletes happen in main S3; toolbox has no direct access.
    """
    logger.debug(
        f"Creating release for:\n\tPU: {pushing_entity_id}\n\tProduct ID: {product_id}\n\tDataset ID: {dataset_id}"
        f"\n\tFiles: {files}"
    )
    invalid_delivery_ids_response = validate_delivery_ids(
        pushing_entity_id, product_id, dataset_id
    )
    if invalid_delivery_ids_response:
        logger.error(
            "The ids provided for this delivery did not match our records, "
            f"see: {invalid_delivery_ids_response.reason}"
        )
        return (
            ResponseDelete.create_from_fatal_error(
                invalid_delivery_ids_response.reason
            ),
            None,
        )

    s3_client = get_s3_ingestion_client(pushing_entity_id)

    manifest = _create_and_upload_manifest(
        s3_client,
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=[create_delete_operation(files)],
    )
    return ResponseDelete.create(delivery_id=manifest.manifest_id), manifest


def create_delete_operation(files: list[str]) -> Operation:
    # add validation here if needed
    return Operation(
        operation="delete",
        files=[
            ManifestFile(file_path=Path(file_), file_size=None, checksum=None)
            for file_ in files
        ],
    )


def delivery(
    operations: list[OperationNames],
    operations_sources: list[list[str]],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    max_concurrent_uploads: int = 10,
) -> tuple[ResponseDelivery, Manifest | None]:

    invalid_delivery_ids_response = validate_delivery_ids(
        pushing_entity_id, product_id, dataset_id
    )
    if invalid_delivery_ids_response:
        logger.error(
            "The ids provided for this delivery did not match our records, "
            f"see: {invalid_delivery_ids_response.reason}"
        )
        return (
            ResponseDelivery.create_from_fatal_error(
                invalid_delivery_ids_response.reason
            ),
            None,
        )

    manifest_id = create_manifest_id(product_id)
    all_operations: list[Operation] = []
    validation_results: list[UploadValidationResult | None] = []
    s3_client = get_s3_ingestion_client(pushing_entity_id)
    for operation, sources in zip(operations, operations_sources):
        if operation == "delete":
            all_operations.append(create_delete_operation(sources))
            validation_results.append(None)
        elif operation == "upload":
            operation, validation_result = create_upload_operation(
                [Path(file_) for file_ in sources]
            )
            all_operations.append(operation)
            validation_results.append(validation_result)
    validation_errors = [
        validation_result.files_invalid
        for validation_result in validation_results
        if validation_result and validation_result.files_invalid
    ]
    if validation_errors:
        # TODO: this needs to be consistent accross the toolbox.
        # For now, any validation error will cancel the delivery.
        logger.error(
            f"Some files failed validation: {validation_errors}. Delivery cancelled. No manifest will be created."
        )
        return (
            ResponseDelivery.create_from_fatal_error(
                fatal_error=f"Some files failed validation: {validation_errors}. Delivery cancelled. No manifest will be created."
            ),
            None,
        )
    all_responses: list[ResponseUpload | ResponseDelete] = []
    for operation, validation_result in zip(all_operations, validation_results):
        if operation.operation == "upload":
            put_files_result = _put_files_to_ingestion_system(
                s3_client,
                manifest_id=manifest_id,
                product_id=product_id,
                dataset_id=dataset_id,
                operation=operation,
                max_concurrent_uploads=max_concurrent_uploads,
            )
            _update_operation_with_put_results(operation, put_files_result)
            all_responses.append(
                ResponseUpload.create(
                    delivery_id=manifest_id,
                    result_validation=validation_result,  # type: ignore
                    result_upload=put_files_result,
                )
            )
        elif operation.operation == "delete":
            all_responses.append(ResponseDelete.create(delivery_id=manifest_id))

    manifest = _create_and_upload_manifest(
        s3_client,
        pushing_entity_id,
        product_id,
        dataset_id,
        all_operations,
        manifest_id,
    )
    return (
        ResponseDelivery.create(
            delivery_id=manifest_id, operations_responses=all_responses
        ),
        manifest,
    )


def create_upload_operation(
    files: list[Path],
) -> tuple[Operation, UploadValidationResult]:
    validation_result = upload_files_validation(files)
    return (
        Operation(
            operation="upload",
            files=[
                ManifestFile(
                    file_path=file_,
                    file_size=os.path.getsize(file_) // (1024 * 1024),
                    checksum=None,  # ETag will be filled in after upload
                )
                for file_ in validation_result.files_valid
            ],
        ),
        validation_result,
    )


def _create_and_upload_manifest(
    s3_client: S3Client,
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    operations: list[Operation],
    manifest_id: str | None = None,
) -> Manifest:
    if not manifest_id:
        manifest_id = create_manifest_id(product_id)
    manifest = create_manifest(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=operations,
        manifest_id=manifest_id,
    )
    manifest_bucket_path = get_manifest_destination_key(manifest.manifest_id)
    logger.debug(f"Uploading delivery document to {manifest_bucket_path}")
    s3_client.upload_fileobj(
        key=manifest_bucket_path, file=manifest.model_dump_json().encode()
    )
    return manifest


def _put_files_to_ingestion_system(
    s3_client: S3Client,
    manifest_id: str,
    product_id: str,
    dataset_id: str,
    operation: Operation,
    max_concurrent_uploads: int,
) -> PutFilesResult:

    s3_keys_local_file_mapping = get_upload_bucket_keys_from_local_files(
        [file_.file_path for file_ in operation.files],
        manifest_id,
        product_id,
        dataset_id,
    )
    upload_multiple_files_result = s3_client.upload_multiple_files(
        s3_keys_local_file_mapping,
        max_concurrent_uploads,
    )
    return upload_multiple_files_result


def _update_operation_with_put_results(
    operation: Operation, put_files_result: PutFilesResult
) -> None:
    """
    TODO: add the possibility for users to abort the delivery if there are any errors. For now, we just log them and continue.

    Might be the default one.
    """
    successful_files_dict = {
        file_.local_path: file_ for file_ in put_files_result.successful_files
    }
    errored_files_dict = {file_.path: file_ for file_ in put_files_result.errored_files}
    index_files_to_remove = []
    for i, manifest_file in enumerate(operation.files):
        if manifest_file.file_path in successful_files_dict:
            manifest_file.checksum = successful_files_dict[
                manifest_file.file_path
            ].e_tag
        elif manifest_file.file_path in errored_files_dict:
            logger.error(
                f"File {manifest_file.file_path} failed to upload: {errored_files_dict[manifest_file.file_path].reason}"
            )
            index_files_to_remove.append(i)
    for index in reversed(index_files_to_remove):
        del operation.files[index]
