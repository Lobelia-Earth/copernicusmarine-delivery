import json
import logging
import re

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


from pusher.config.settings import Settings
from pusher.domain.models import ErrorPutFile, PutFilesResult, S3File
from pusher.infrastructure.obstore_s3_client import (
    CHUNK_SIZE,
    ObstoreS3Client,
    ObstoreS3ClientConnection,
)

logger = logging.getLogger(__name__)


def _extract_error_message(e: Exception) -> str:
    match = re.search(r'message: "([^"]+)"', str(e))
    return match.group(1) if match else str(e).splitlines()[0]


class IngestionBucketService:
    def __init__(self, client: ObstoreS3Client) -> None:
        self._client = client

    @property
    def bucket_name(self) -> str:
        return self._client._connection._bucket_name

    @classmethod
    def from_s3_credentials(
        cls,
        pushing_entity_id: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint_url: str,
    ) -> "IngestionBucketService":
        connection = ObstoreS3ClientConnection(
            pushing_entity_id=pushing_entity_id,
            access_key_id=access_key_id,
            secret_access_key=access_key_id,
            endpoint_url=endpoint_url,
        )
        return cls(ObstoreS3Client(connection=connection))

    def put_manifest(self, manifest: dict[str, Any], destination_key: str) -> None:
        self._client.upload_file(
            key=destination_key,
            file=json.dumps(manifest).encode(),
            use_multipart=False,
        )

    def put_file(
        self,
        local_path_to_file: Path,
        destination_key: str,
        position: int = 0,
        chunk_size: int = CHUNK_SIZE,
    ) -> S3File | ErrorPutFile:
        logger.debug(
            f"Starting to put file #{position}: {local_path_to_file} to {destination_key}"
        )
        try:
            result = self._client.upload_file(
                key=destination_key,
                file=local_path_to_file,
                use_multipart=True,
                chunk_size=chunk_size,
            )
        except Exception as e:
            return ErrorPutFile(
                local_path=local_path_to_file.as_posix(),
                error=_extract_error_message(e),
            )
        logger.debug(f"Finished putting file #{position} to {destination_key}")
        return S3File(
            s3_path=destination_key,
            local_path=local_path_to_file.as_posix(),
            e_tag=result["e_tag"].strip('"'),
        )

    def put_multiple_files(
        self,
        bucket_keys_by_local_file_path_mapping: dict[Path, str],
        settings: Settings,
    ) -> PutFilesResult:
        total = len(bucket_keys_by_local_file_path_mapping)
        success_results = []
        error_results = []
        with ThreadPoolExecutor(
            max_workers=settings.max_concurrent_uploads
        ) as executor:
            futures = {
                executor.submit(self.put_file, path, key, position=i): (path, key)
                for i, (path, key) in enumerate(
                    bucket_keys_by_local_file_path_mapping.items()
                )
            }
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                if isinstance(result, S3File):
                    success_results.append(result)
                    logger.info(f"Uploaded file {i + 1}/{total}")
                else:
                    error_results.append(result)
        return PutFilesResult(success=success_results, error=error_results)
