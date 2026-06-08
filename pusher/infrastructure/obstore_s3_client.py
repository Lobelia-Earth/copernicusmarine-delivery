import os

from datetime import timedelta
from pathlib import Path
from typing import Any, TYPE_CHECKING, cast

from obstore.store import S3Store

from .s3_client import S3Client, S3ClientConnection


if TYPE_CHECKING:
    pass

CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB

ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

_RETRY_CONFIG = {
    "max_retries": 5,
    "retry_timeout": timedelta(minutes=10),
    "backoff": {
        "base": 2,
        "init_backoff": timedelta(seconds=1),
        "max_backoff": timedelta(seconds=30),
    },
}

_CLIENT_OPTIONS = {"allow_http": True} if ENVIRONMENT == "dev" else {}


class NoSuchBucketException(Exception): ...


class ConnectionRefusedException(Exception): ...


class ObstoreS3ClientConnection(S3ClientConnection):
    def __init__(
        self,
        pushing_entity_id: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint_url: str,
    ) -> None:
        self._bucket_name = f"mdl-ing-{pushing_entity_id.lower()}"
        self._store: S3Store = S3Store.from_url(
            url=f"s3://{self._bucket_name}",
            config={
                "endpoint": endpoint_url,
                "access_key_id": access_key_id,
                "secret_access_key": secret_access_key,
            },
            retry_config=_RETRY_CONFIG,
            client_options=_CLIENT_OPTIONS,
        )
        self._assert_bucket_exists()

    def _assert_bucket_exists(self) -> None:
        try:
            next(iter(self._store.list(chunk_size=1)), None)
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

    def get_store(self) -> S3Store:
        return self._store


class ObstoreS3Client(S3Client):
    def __init__(
        self, connection: ObstoreS3ClientConnection, max_concurrency: int = 12
    ) -> None:
        self.max_concurrency = max_concurrency
        self._connection = connection
        self._store = self._connection.get_store()

    def upload_file(
        self,
        key: str,
        file: bytes | Path,
        use_multipart: bool = True,
        chunk_size: int = CHUNK_SIZE,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._store.put(
                path=key,
                file=file,
                use_multipart=use_multipart,
                chunk_size=chunk_size,
                max_concurrency=self.max_concurrency,
            ),
        )

    def get_file_metadata(self, key: str) -> Any:
        return self._store.head(path=key)
