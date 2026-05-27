import os
from datetime import datetime, timezone
from random import randint
from typing import Literal

from pusher.models import Manifest, ManifestFile


def create_manifest(
    producer_id: str,
    product_id: str,
    dataset_id: str,
    operation: Literal["upload", "delete"],
    files: list[str],
) -> Manifest:
    manifest_files = create_manifest_files(files, operation)
    return Manifest(
        manifest_id=create_manifest_id(dataset_id),
        producer_id=producer_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operation=operation,
        files=manifest_files,
        creation_time=datetime.now(timezone.utc).isoformat(),
    )


def create_manifest_id(dataset_id: str) -> str:
    timestamp_format = "%Y%m%dT%H%M%S"
    iso_timestamp_with_seconds = datetime.now().strftime(timestamp_format)
    random_number = randint(1000, 9999)
    return f"{iso_timestamp_with_seconds}-{dataset_id}-{random_number}"


def create_manifest_files(
    files: list[str], operation: Literal["upload", "delete"]
) -> list[ManifestFile]:
    manifest_files = []
    for file_ in files:
        if operation == "delete":
            file_size = None
        else:
            # TODO: add documented validation here with proper error handling
            assert os.path.exists(
                file_
            ), f"File {file_} does not exist for upload operation"
            assert os.path.getsize(file_) > 0, f"File {file_} seems empty"
            file_size = os.path.getsize(file_) // (1024 * 1024)  # Size in MB

        manifest_file = ManifestFile(
            s3_path=file_,
            file_size=file_size,
            local_file_path=file_ if operation == "upload" else None,
            checksum="TODO",
        )
        manifest_files.append(manifest_file)
    return manifest_files
