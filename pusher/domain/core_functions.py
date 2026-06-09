from datetime import date
from pathlib import Path

from pusher.config.logger import logger
from pusher.config.settings import NEW_DATA_BUCKET_PATH, NEW_MANIFESTS_PREFIX, Settings
from pusher.domain.manifests_helper import create_manifest, create_manifest_id
from pusher.domain.models import ResponseUpload, S3File
from pusher.services.ingestion_bucket_service import IngestionBucketService


def get_bucket_keys_from_local_files(
    today: date,
    list_of_files: list[str],
    bucket_name: str,
    manifest_id: str,
    product_id: str,
    dataset_id: str,
) -> dict[Path, str]:
    return {
        Path(file_path): NEW_DATA_BUCKET_PATH.format(
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
    return NEW_MANIFESTS_PREFIX.format(
        YYYY=today.year,
        MM=f"{today.month:02}",
        DD=f"{today.day:02}",
        manifest_id=manifest_id,
    )


def upload(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    files: list[str],
    ingestion_bucket_service: IngestionBucketService,
    settings: Settings,
) -> ResponseUpload:
    """Try and upload all files given.
    Keep track of errors.
    Create Manifest with successful ones.
    Use ETag as checksum."""

    manifest_id = create_manifest_id(product_id)
    today = date.today()
    bucket_keys_by_local_file_path_mapping = get_bucket_keys_from_local_files(
        today,
        files,
        ingestion_bucket_service.bucket_name,
        manifest_id,
        product_id,
        dataset_id,
    )

    upload_multiple_files_result = ingestion_bucket_service.put_multiple_files(
        bucket_keys_by_local_file_path_mapping,
        settings,
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
            error="No successful uploads - manifest was not created.",
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
    ingestion_bucket_service.put_manifest(manifest.model_dump(), manifest_bucket_path)

    return ResponseUpload(
        files=upload_multiple_files_result.success,
        files_errored=[file.local_path for file in upload_multiple_files_result.error],
        manifest=manifest,
    )
