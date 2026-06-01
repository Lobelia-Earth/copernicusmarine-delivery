from typing import Literal

from pydantic import BaseModel


class ManifestFile(BaseModel):
    #: Path to the file in the destination storage (e.g., S3 path).
    s3_path: str
    #: Estimation of the size of the file in MB.
    file_size: int | None
    #: checksum of the file to be uploaded.
    checksum: str


class Operation(BaseModel):
    operation: Literal["upload", "delete"]
    files: list[ManifestFile]


class Manifest(BaseModel):
    #: Unique identifier for the manifest. Contains a date that is not in UTC.
    manifest_id: str
    producer_id: str
    product_id: str
    dataset_id: str
    operations: list[Operation]

    #: ISO 8601 formatted timestamp in UTC
    creation_time: str
