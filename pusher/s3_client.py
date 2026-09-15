import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from obstore import delete, get, put
from obstore import list as list_obstore
from obstore.store import S3Store

from delivery_common.domain import now_in_utc_isoformat
from pusher.auth import login
from pusher.core_functions.domain import (
    ErrorFile,
    GetConfigResponse,
    PutFilesResult,
    S3File,
    S3Path,
)
from pusher.core_functions.exceptions import (
    ConnectionRefusedException,
    NoSuchBucketException,
)
from pusher.environment_variables import (
    ALLOW_HTTP,
    INGESTION_SERVICE_URL,
)
from pusher.http_client import http_client
from pusher.logger import logger

if TYPE_CHECKING:
    from obstore.store import S3Credential, S3CredentialProvider

_RETRY_CONFIG: Any = {
    "max_retries": 5,
    "retry_timeout": timedelta(minutes=10),
    "backoff": {
        "base": 2,
        "init_backoff": timedelta(seconds=1),
        "max_backoff": timedelta(seconds=30),
    },
}

_CLIENT_CONFIG: Any = {
    "allow_http": ALLOW_HTTP,
    "timeout": "300s",
}

_OS_ERROR_RETRIES = 3
_OS_ERROR_BACKOFF_SECONDS = 5


def _extract_error_message(e: Exception) -> str:
    match = re.search(r'message: "([^"]+)"', str(e))
    return match.group(1) if match else str(e).splitlines()[0]


def _fetch_s3_credentials(
    pushing_entity_id: str, config: GetConfigResponse
) -> S3Credential:
    token = login(config)
    resp = http_client.get(
        f"{INGESTION_SERVICE_URL}/credentials/{pushing_entity_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    creds = resp.json()
    return {
        "access_key_id": creds["access_key_id"],
        "secret_access_key": creds["secret_access_key"],
        "token": creds["session_token"],
        "expires_at": datetime.fromisoformat(creds["expiration"]),
    }


def _get_s3_store(
    endpoint_url: str,
    bucket_name: str,
    pushing_entity_id: str,
    config: GetConfigResponse,
) -> S3Store:
    credential_provider: S3CredentialProvider = partial(
        _fetch_s3_credentials, pushing_entity_id, config
    )
    s3_config = {"endpoint": endpoint_url}
    return S3Store.from_url(
        url=f"s3://{bucket_name}",
        config=s3_config,
        credential_provider=credential_provider,
        retry_config=_RETRY_CONFIG,
        client_options=_CLIENT_CONFIG,
    )


def _make_client(
    bucket_name: str,
    store: S3Store,
    assert_bucket_exists: bool = True,
    chunk_concurrency: int = 6,
) -> "S3Client":
    return S3Client(
        store=store,
        bucket_name=bucket_name,
        assert_bucket_exists=assert_bucket_exists,
        max_concurrency=chunk_concurrency,
    )


def get_s3_ingestion_client(
    pushing_entity_id: str,
    bucket_name: str,
    config: GetConfigResponse,
    endpoint_url: str,
    chunk_concurrency: int = 6,
) -> "S3Client":
    # TODO: add a refresh in the credentials
    # TODO: The bucket name should be returned by the OPDV as part of the pushing_entities file
    # TODO: The endpoint URL should be returned by the OPDV
    return _make_client(
        bucket_name=bucket_name,
        store=_get_s3_store(
            bucket_name=bucket_name,
            endpoint_url=endpoint_url,
            pushing_entity_id=pushing_entity_id,
            config=config,
        ),
        chunk_concurrency=chunk_concurrency,
    )


class S3Client:
    def __init__(
        self,
        store: S3Store,
        bucket_name: str,
        assert_bucket_exists: bool,
        max_concurrency: int = 6,
    ) -> None:
        self._store = store
        self._bucket_name = bucket_name
        self.max_concurrency = max_concurrency
        if assert_bucket_exists:
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
        chunk_size: int,
        use_multipart: bool = True,
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

    def _put_with_os_error_retry(
        self, key: str, file: Path, use_multipart: bool, chunk_size: int
    ) -> Any:
        for attempt in range(1, _OS_ERROR_RETRIES + 1):
            try:
                return put(
                    store=self._store,
                    path=key,
                    file=file,
                    use_multipart=use_multipart,
                    chunk_size=chunk_size,
                    max_concurrency=self.max_concurrency,
                )
            except OSError as e:
                if attempt == _OS_ERROR_RETRIES:
                    raise
                logger.warning(
                    f"Socket error uploading {file.name} "
                    f"(attempt {attempt}/{_OS_ERROR_RETRIES}): {e}. Retrying."
                )
                time.sleep(_OS_ERROR_BACKOFF_SECONDS * attempt)

    def upload_file(
        self,
        key: str,
        file: Path,
        chunk_size: int,
        dry_run: bool,
        raise_on_error: bool,
        use_multipart: bool,
    ) -> S3File | ErrorFile:
        """Upload a local file (by Path) to S3."""
        try:
            if dry_run:
                e_tag = "dry-run"
                upload_start_time = now_in_utc_isoformat()
                upload_end_time = now_in_utc_isoformat()
            else:
                logger.debug(f"Starting upload for {file.name}")
                upload_start_time = now_in_utc_isoformat()
                put_result = self._put_with_os_error_retry(
                    key, file, use_multipart, chunk_size
                )
                upload_end_time = now_in_utc_isoformat()
                logger.debug(
                    f"Successfully uploaded file {file.name} from {upload_start_time} to {upload_end_time}"
                )
                e_tag = put_result["e_tag"].strip('"')
            return S3File(
                local_path=file,
                ingestion_system_s3_path=S3Path(key),
                e_tag=e_tag,
                upload_start_time=upload_start_time,
                upload_end_time=upload_end_time,
            )

        except Exception as e:
            if raise_on_error:
                logger.error(
                    f"Something went wrong uploading: {file.name}. "
                    f"There won't be any delivery."
                )
                raise e
            logger.error(
                f"Something went wrong uploading: {file.name}. "
                f"Skipping this file. Error: {_extract_error_message(e)}"
            )
            return ErrorFile(
                local_path=file,
                reason=_extract_error_message(e),
            )

    def upload_multiple_files(
        self,
        s3_key_local_file_mapping: dict[Path, str],
        raise_on_error: bool,
        chunk_size: int,
        max_concurrent_uploads: int,
        dry_run: bool,
    ) -> PutFilesResult:
        total = len(s3_key_local_file_mapping)
        success_results = []
        error_results = []

        logger.info(
            f"{'[DRY RUN]: ' if dry_run else ''}Starting to upload {len(s3_key_local_file_mapping)} files ..."
        )
        with ThreadPoolExecutor(max_workers=max_concurrent_uploads) as executor:
            futures = {
                executor.submit(
                    self.upload_file,
                    key=key,
                    file=path,
                    use_multipart=True,
                    raise_on_error=raise_on_error,
                    chunk_size=chunk_size,
                    dry_run=dry_run,
                ): (path, key)
                for _, (path, key) in enumerate(s3_key_local_file_mapping.items())
            }
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                if isinstance(result, S3File):
                    success_results.append(result)
                    if not dry_run:
                        logger.info(
                            f"{'[DRY RUN]: ' if dry_run else ''}Uploaded [{i + 1}/{total}] file {result.local_path.name}"
                        )
                else:
                    error_results.append(result)

        return PutFilesResult(
            successful_files=success_results, errored_files=error_results
        )

    def get_file_stream(self, path_to_file: str) -> bytes:
        response = get(
            self._store,
            path=path_to_file,
        )
        return b"".join(response.stream(min_chunk_size=20 * 1024 * 1024))

    def delete_keys(self, keys: list[str]) -> None:
        delete(self._store, paths=keys)
