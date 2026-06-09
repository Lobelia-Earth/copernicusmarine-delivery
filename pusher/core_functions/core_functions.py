from datetime import date
from pathlib import Path

from pusher.core_functions import environment_variables
from pusher.core_functions.manifests_helper import create_manifest, create_manifest_id
from pusher.core_functions.models import ResponseUpload, S3File
from pusher.logger import logger
from pusher.s3_client import S3Client


def get_bucket_keys_from_local_files(
    today: date,
    list_of_files: list[str],
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
            YYYY=today.year,
            MM=f"{today.month:02}",
            file_name=file_path.split("/")[
                -1
            ],  # FIXME this is too naive. We should run some checks on the files before hand.
        )
        for file_path in list_of_files
    }


def get_manifest_destination_key(today: date, manifest_id: str) -> str:
    return environment_variables.NEW_MANIFESTS_PREFIX.format(manifest_id=manifest_id)


def upload(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
    max_concurrent_uploads: int,
) -> ResponseUpload:
    """Try and upload all files given.
    Keep track of errors.
    Create Manifest with successful ones.
    Use ETag as checksum."""

    s3_client = S3Client(
        pushing_entity_id=pushing_entity_id,
        access_key_id=environment_variables.ACCESS_KEY_ID,
        secret_access_key=environment_variables.SECRET_ACCESS_KEY,
        endpoint_url=environment_variables.INGESTION_BUCKETS_ENDPOINT,
        environment=environment_variables.ENVIRONMENT,
    )
    manifest_id = create_manifest_id(product_id)
    today = date.today()
    bucket_keys_by_local_file_path_mapping = get_bucket_keys_from_local_files(
        today,
        files,
        s3_client.bucket_name,
        manifest_id,
        product_id,
        dataset_id,
    )

    upload_multiple_files_result = s3_client.upload_multiple_files(
        bucket_keys_by_local_file_path_mapping,
        max_concurrent_uploads,
    )

    if upload_multiple_files_result.error:
        failed = "\n".join(
            f"  {e.local_path}: {e.error}" for e in upload_multiple_files_result.error
        )
        logger.error(
            f"Failed to upload {len(upload_multiple_files_result.error)} file(s):\n{failed}"
        )
        if upload_multiple_files_result.success:
            logger.warning(
                f"Manifest will include only {len(upload_multiple_files_result.success)} successful upload(s)"
            )

    if not upload_multiple_files_result.success:
        logger.error("Manifest won't be created as there were no successful uploads")
        return ResponseUpload(
            files_errored=[f.local_path for f in upload_multiple_files_result.error],
            error="No successful uploads - no data were sent.",
        )

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
                for file in upload_multiple_files_result.success
            ]
        },
    )

    manifest_bucket_path = get_manifest_destination_key(today, manifest.manifest_id)

    # What if uploading the manifest fails :0! this is the worst of the worst case scenarios!
    s3_client.upload_file_obj(key=manifest_bucket_path, file=manifest.model_dump())

    return ResponseUpload(
        files=upload_multiple_files_result.success,
        files_errored=[file.local_path for file in upload_multiple_files_result.error],
        manifest=manifest,
    )
