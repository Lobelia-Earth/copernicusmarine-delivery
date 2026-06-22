import json
from datetime import date
from pathlib import Path

from cloudpathlib import S3Path

from pusher.core_functions import environment_variables
from pusher.core_functions.delivery_validator import validate_upload_file_requirements
from pusher.core_functions.manifests_helper import create_manifest, create_manifest_id
from pusher.core_functions.models import ResponseUpload, S3File
from pusher.logger import logger
from pusher.s3_client import S3Client


def get_upload_bucket_keys_from_local_files(
    today: date,
    list_of_files: list[Path | S3Path],
    bucket_name: str,
    manifest_id: str,
    product_id: str,
    dataset_id: str,
) -> dict[Path, str]:
    return {
        Path(file_path): environment_variables.NEW_DATA_BUCKET_PATH.format(
            manifest_id=manifest_id,
            product_id=product_id,
            dataset_id=dataset_id,
            file_name=file_path.name,
        )
        for file_path in list_of_files
    }

def get_delete_s3_files_from_local_files(
    list_of_files: list[Path | S3Path],
    product_id: str,
    dataset_id: str
) -> list[S3File]:
    return [
        S3File()
        for file in list_of_files
    ]


def get_manifest_destination_key(today: date, manifest_id: str) -> str:
    return environment_variables.NEW_MANIFESTS_PREFIX.format(manifest_id=manifest_id)


def upload(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
    max_concurrent_uploads: int,
) -> ResponseUpload:
    """
    1. Quick-valdiate all files, keep track of invalid files. If no valid files, return early.
    2. Try and upload all files given. Keep track of errored files. If no successful uploads, return early.
    3. Create Manifest with successful ones (in the future there might be a flag to abort if errors). Use ETag as checksum."""

    logger.info(
        f"Creating release for:\n\tPU: {pushing_entity_id}\n\tProduct ID: {product_id}\n\tDataset ID: {dataset_id}"
        f"\n\tFiles: {[Path(file).name for file in files]}"
    )

    response = ResponseUpload()

    logger.info("Validating files provided before relase")

    validate_result = validate_upload_file_requirements([Path(file) for file in files])

    if validate_result.files_invalid:
        logger.warning("Some files did not pass the validation")
        for invalid_file in validate_result.files_invalid:
            logger.error(f"Invalid file! {invalid_file}")
        response.files_invalid = validate_result.files_invalid
    if not validate_result.files_valid:
        no_valid_files_fatal_error_response = (
            "No file passed the validation. No manifest will be created."
        )
        logger.error(no_valid_files_fatal_error_response)
        response.fatal_error = no_valid_files_fatal_error_response
        return response

    s3_client = S3Client(
        pushing_entity_id=pushing_entity_id,
        access_key_id=environment_variables.OPDV_ACCESS_KEY_ID,
        secret_access_key=environment_variables.OPDV_SECRET_ACCESS_KEY,
        endpoint_url=environment_variables.INGESTION_BUCKETS_ENDPOINT,
        environment=environment_variables.ENVIRONMENT,
    )
    manifest_id = create_manifest_id(product_id)
    today = date.today()
    bucket_keys_by_local_file_path_mapping = get_upload_bucket_keys_from_local_files(
        today,
        validate_result.files_valid,
        s3_client.bucket_name,
        manifest_id,
        product_id,
        dataset_id,
    )
    upload_multiple_files_result = s3_client.upload_multiple_files(
        bucket_keys_by_local_file_path_mapping,
        max_concurrent_uploads,
    )

    if upload_multiple_files_result.errored_files:
        for errored_file in upload_multiple_files_result.errored_files:
            logger.error(f"Error uploading: {errored_file}")
            response.files_failed.append(errored_file)
        if upload_multiple_files_result.successful_files:
            logger.warning(
                f"Manifest will include only {len(upload_multiple_files_result.successful_files)} successful upload(s)"
            )

    if not upload_multiple_files_result.successful_files:
        no_valid_files_fatal_error_response = (
            "No successful uploads - no data were sent."
        )
        logger.error(no_valid_files_fatal_error_response)
        response.fatal_error = no_valid_files_fatal_error_response
        return response

    manifest = create_manifest(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operation_files_mapping={
            "upload": [
                S3File(
                    local_path=file.local_path,
                    s3_path=file.s3_path,
                    e_tag=file.e_tag,
                )
                for file in upload_multiple_files_result.successful_files
            ]
        },
    )

    manifest_bucket_path = get_manifest_destination_key(today, manifest.manifest_id)

    # What if uploading the manifest fails :0! this is the worst of the worst case scenarios!
    logger.debug(f"Uploading manifest to {manifest_bucket_path}")
    upload_file_obj_result = s3_client.upload_fileobj(
        key=manifest_bucket_path, file=json.dumps(manifest.model_dump()).encode()
    )
    response.manifest = manifest
    response.transaction_id = manifest.manifest_id
    response.files_uploaded = [
        file.local_path.name for file in upload_multiple_files_result.successful_files
    ]
    return response



def delete(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
    max_concurrent_deletes: int,
) -> ResponseUpload:
    """
    1. Create manifest with deletes. Push manifest. Deletes are in the main S3, toolbox has no direct access. Toolbox can't delete directly.
    """
    logger.info(
        f"Creating release for:\n\tPU: {pushing_entity_id}\n\tProduct ID: {product_id}\n\tDataset ID: {dataset_id}"
        f"\n\tFiles: {[Path(file).name for file in files]}"
    )

    response = ResponseUpload()

    logger.info("Validating files provided before relase")

    s3_client = S3Client(
        pushing_entity_id=pushing_entity_id,
        access_key_id=environment_variables.OPDV_ACCESS_KEY_ID,
        secret_access_key=environment_variables.OPDV_SECRET_ACCESS_KEY,
        endpoint_url=environment_variables.INGESTION_BUCKETS_ENDPOINT,
        environment=environment_variables.ENVIRONMENT,
    )
    manifest_id = create_manifest_id(product_id)
    today = date.today()

    # helper method to convert from CLI arguments to delete pseudopath.
    # it won't be full path as this bit should not know which bucket it goes.
    # 

    manifest = create_manifest(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operation_files_mapping={
            "delete": [
                S3File(
                    local_path=file.local_path,
                    s3_path=file.s3_path,
                    e_tag=file.e_tag,
                )
                for file in upload_multiple_files_result.successful_files
            ]
        },
    )

    manifest_bucket_path = get_manifest_destination_key(today, manifest.manifest_id)

    # What if uploading the manifest fails :0! this is the worst of the worst case scenarios!
    logger.debug(f"Uploading manifest to {manifest_bucket_path}")
    upload_file_obj_result = s3_client.upload_fileobj(
        key=manifest_bucket_path, file=json.dumps(manifest.model_dump()).encode()
    )
    response.manifest = manifest
    response.transaction_id = manifest.manifest_id
    response.files_uploaded = [
        file.local_path.name for file in upload_multiple_files_result.successful_files
    ]
    return response
