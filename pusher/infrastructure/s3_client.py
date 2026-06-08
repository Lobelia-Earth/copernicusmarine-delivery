from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any, Optional


class S3ClientConnection(ABC):
    @abstractmethod
    def get_store(self) -> Any: ...


class S3Client(ABC):
    connection: S3ClientConnection
    bucket_does_not_exist_exception: Exception

    @abstractmethod
    def upload_file(
        self, key: str, file: bytes | Path, use_multipart: bool, chunk_size: int
    ) -> dict[str, Any]: ...

    @abstractmethod
    def get_file_metadata(self, key: str) -> Optional[dict]: ...
