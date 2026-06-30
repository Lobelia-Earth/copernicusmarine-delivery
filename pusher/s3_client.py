import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path

from environment_variables import (
    ENVIRONMENT,
    INGESTION_BUCKETS_ENDPOINT,
    OPDV_ACCESS_KEY_ID,
    OPDV_SECRET_ACCESS_KEY,
)
from obstore import list as list_obstore
from obstore import put
from obstore.store import ClientConfig, RetryConfig, S3Store

from pusher.core_functions.exceptions import (
    ConnectionRefusedException,
    NoSuchBucketException,
)
from pusher.core_functions.models import ErrorFile, PutFilesResult, S3File, S3Path
from pusher.logger import logger

CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB

_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    retry_timeout=timedelta(minutes=10),
    backoff={
        "base": 2,
        "init_backoff": timedelta(seconds=1),
        "max_backoff": timedelta(seconds=30),
    },
)

_CLIENT_OPTIONS: ClientConfig = ClientConfig(allow_http=True)


def _extract_error_message(e: Exception) -> str:
    match = re.search(r'message: "([^"]+)"', str(e))
    return match.group(1) if match else str(e).splitlines()[0]


class S3Client:
    def __init__(
        self,
        pushing_entity_id: str,
        max_concurrency: int = 12,
    ) -> None:
        self.max_concurrency = max_concurrency
        self._endpoint_url = INGESTION_BUCKETS_ENDPOINT
        self._access_key_id = OPDV_ACCESS_KEY_ID
        self._secret_access_key = OPDV_SECRET_ACCESS_KEY
        self._bucket_name = f"mdl-ing-{pushing_entity_id.lower()}"
        self._store: S3Store = S3Store.from_url(
            url=f"s3://{self._bucket_name}",
            config={
                "endpoint": self._endpoint_url,
                "access_key_id": self._access_key_id,
                "secret_access_key": self._secret_access_key,
            },
            retry_config=_RETRY_CONFIG,
            client_options={} if ENVIRONMENT != "local" else _CLIENT_OPTIONS,
        )

        self._assert_bucket_exists()

    def _assert_bucket_exists(self) -> None:
        try:
            next(iter(list_obstore(store=self._store, chunk_size=1)), None)
        except Exception as e:
            if "NoSuchBucket" in str(e):
                raise NoSuchBucketException(
                    f"Bucket does not exist: {self._bucket_name}"
                )
            elif "ConnectionRefused" in str(e):
                raise ConnectionRefusedException(
                    f"Can't connect to bucket: {self._bucket_name}"
                )
            raise e

    @property
    def bucket_name(self) -> str:
        return self._bucket_name

    def upload_fileobj(
        self,
        key: str,
        file: bytes,
        use_multipart: bool = True,
        chunk_size: int = CHUNK_SIZE,
    ):
        """Upload a file object (bytes) to S3."""
        try:
            logger.debug(f"Starting file_obj upload to {key}")
            put_result = put(
                store=self._store,
                path=key,
                file=file,
                use_multipart=use_multipart,
                chunk_size=chunk_size,
                max_concurrency=self.max_concurrency,
            )
            logger.debug(f"Uploaded file obj PutResult: {put_result}")
        except Exception as e:
            raise

    def upload_file(
        self,
        key: str,
        file: Path,
        use_multipart: bool = True,
        chunk_size: int = CHUNK_SIZE,
    ) -> S3File | ErrorFile:
        """Upload a local file (by Path) to S3."""
        logger.debug(f"Starting upload for {file.name}")
        try:
            put_result = put(
                store=self._store,
                path=key,
                file=file,
                use_multipart=use_multipart,
                chunk_size=chunk_size,
                max_concurrency=self.max_concurrency,
            )
            logger.debug(f"Successfully uploaded file {file.name}")
            return S3File(
                local_path=file,
                s3_path=S3Path(key),
                e_tag=put_result["e_tag"].strip('"'),  # type: ignore
            )

        except Exception as e:
            logger.error(f"Something went wrong uploading: {file.name}")
            return ErrorFile(
                path=file,
                reason=_extract_error_message(e),
            )

    def upload_multiple_files(
        self,
        s3_key_local_file_mapping: dict[Path, str],
        max_concurrent_uploads: int,
    ) -> PutFilesResult:
        total = len(s3_key_local_file_mapping)
        success_results = []
        error_results = []
        with ThreadPoolExecutor(max_workers=max_concurrent_uploads) as executor:
            futures = {
                executor.submit(
                    self.upload_file,
                    key=key,
                    file=path,
                    use_multipart=True,
                    chunk_size=CHUNK_SIZE,
                ): (path, key)
                for _, (path, key) in enumerate(s3_key_local_file_mapping.items())
            }
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                if isinstance(result, S3File):
                    success_results.append(result)
                    logger.info(f"Uploaded file {i + 1}/{total}")
                else:
                    error_results.append(result)
        return PutFilesResult(
            successful_files=success_results, errored_files=error_results
        )
