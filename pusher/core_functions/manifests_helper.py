import os
from datetime import datetime, timezone
from pathlib import Path
from random import randint

from pusher.core_functions.models import (
    Manifest,
    ManifestFile,
    Operation,
    S3File,
)


def create_manifest(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    operations: list[Operation],
    manifest_id: str,
) -> Manifest:
    return Manifest(
        manifest_id=manifest_id,
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=operations,
        creation_time=datetime.now(timezone.utc).isoformat(),
    )


def create_manifest_id(product_id: str) -> str:
    timestamp_format = "%Y%m%dT%H%M%S"
    iso_timestamp_with_seconds = datetime.now().strftime(timestamp_format)
    random_number = randint(1000, 9999)
    return f"{iso_timestamp_with_seconds}-{product_id}-{random_number}"


def create_upload_manifest_files(files: list[S3File]) -> list[ManifestFile]:
    manifest_files = []
    for file_ in files:
        assert os.path.exists(file_.local_path), (
            f"File {file_} does not exist for upload operation"
        )
        assert os.path.getsize(file_.local_path) > 0, f"File {file_} seems empty"
        file_size = os.path.getsize(file_.local_path) // (1024 * 1024)
        manifest_file = ManifestFile(
            file_path=Path(file_.s3_path),
            file_size=file_size,
            checksum=file_.e_tag,
        )
        manifest_files.append(manifest_file)
    return manifest_files
