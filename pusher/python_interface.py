from typing import cast, get_args

from pydantic import BaseModel, Field

from delivery_common.domain import Manifest, OperationNames
from pusher.core_functions.constants import (
    CHUNK_CONCURRENCY,
    DEFAULT_CHUNK_SIZE_MB,
    MAX_CONCURRENT_UPLOADS,
)
from pusher.core_functions.core_functions import delete as _delete
from pusher.core_functions.core_functions import delivery as _delivery
from pusher.core_functions.core_functions import get_manifest
from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.domain import (
    BaseOperation,
    ResponseDelete,
    ResponseDelivery,
    ResponseUpload,
)
from pusher.core_functions.utils import megabytes_to_bytes


class Upload(BaseOperation):
    """
    Upload ``files`` to the given dataset and product.
    :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files defined in the `files` attribute. Defaults to 5.
    :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
    :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.
    """

    def __init__(self, files: list[str]):
        super().__init__(operation="upload", files=files)

    def submit(
        self,
        pushing_entity_id: str,
        dataset_id: str,
        product_id: str,
        max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
        chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
        chunk_concurrency: int = CHUNK_CONCURRENCY,
    ) -> ResponseUpload:

        if not self.files:
            return ResponseUpload(fatal_error="No files added to upload.")
        response, _ = _upload(
            pushing_entity_id=pushing_entity_id,
            product_id=product_id,
            dataset_id=dataset_id,
            files=self.files,
            max_concurrent_uploads=max_concurrent_uploads,
            chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
            chunk_concurrency=chunk_concurrency,
        )
        return response


class Delete(BaseOperation):
    def __init__(self, files: list[str]):
        super().__init__(operation="delete", files=files)

    def submit(
        self,
        pushing_entity_id: str,
        dataset_id: str,
        product_id: str,
    ) -> ResponseDelete:

        if not self.files:
            return ResponseDelete(fatal_error="No files added to delete.")
        response, _ = _delete(
            pushing_entity_id=pushing_entity_id,
            product_id=product_id,
            dataset_id=dataset_id,
            files=self.files,
        )
        return response


class Delivery(BaseModel):
    """
    Creates a delivery. A delivery is a set of operations (upload or delete) to be performed on a dataset.

    Each operation will be performed sequentially in the order they are given.
    Each operation can have multiple sources (files) to be processed.

    :param operations: A list of operations to be performed. Each operation is a tuple with the operation name as the first element and a list of sources as the second element. Available operations are 'upload' and 'delete'.
    :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files defined in the `operations` attribute. Defaults to 5.
    :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
    :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.
    """  # noqa

    operations: list[Upload | Delete] = Field(default_factory=list)

    def add(self, operation: Upload | Delete) -> None:
        self.operations.append(operation)

    def submit(
        self,
        pushing_entity_id: str,
        dataset_id: str,
        product_id: str,
        max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
        chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
        chunk_concurrency: int = CHUNK_CONCURRENCY,
    ) -> ResponseDelivery:

        if not self.operations:
            return ResponseDelivery(fatal_error="No operations added to delivery.")
        response, _ = _delivery(
            pushing_entity_id=pushing_entity_id,
            product_id=product_id,
            dataset_id=dataset_id,
            operations=[(op.operation, op.files) for op in self.operations],
            max_concurrent_uploads=max_concurrent_uploads,
            chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
            chunk_concurrency=chunk_concurrency,
        )
        return response


def delivery_status(
    delivery_id: str, pushing_entity_id: str, product_id: str, dataset_id: str
) -> Manifest:
    """
    Get the status of a delivery.

    Right now, returns the manifest.
    """
    manifest = get_manifest(
        delivery_id=delivery_id,
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
    )
    return manifest


###
# LEGACY: keeping until the result of the internal testing.
###
def upload(
    sources: list[str],
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
    chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
    chunk_concurrency: int = CHUNK_CONCURRENCY,
) -> ResponseUpload:
    """
    LEGACY: keeping until the result of the internal testing.

    Upload ``sources`` to the given dataset and product.
    :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files defined in the `sources` attribute. Defaults to 5.
    :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
    :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.
    """
    if not sources:
        return ResponseUpload(fatal_error="No files added to upload.")
    response, _ = _upload(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=sources,
        max_concurrent_uploads=max_concurrent_uploads,
        chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
        chunk_concurrency=chunk_concurrency,
    )
    return response


def delete(
    sources: list[str],
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
) -> ResponseDelete:
    """
    LEGACY: keeping until the result of the internal testing.

    Delete ``sources`` from the given dataset and product.
    """
    if not sources:
        return ResponseDelete(fatal_error="No files given to delete.")
    response, _ = _delete(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=sources,
    )
    return response


def delivery(
    operations: list[tuple[str, list[str]]],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
    chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
    chunk_concurrency: int = CHUNK_CONCURRENCY,
) -> ResponseDelivery:
    """
    LEGACY: keeping until the result of the internal testing.

    Creates a delivery. A delivery is a set of operations (upload or delete) to be performed on a dataset.

    Each operation will be performed sequentially in the order they are given.
    Each operation can have multiple sources (files) to be processed.

    :param operations: A list of operations to be performed. Each operation is a tuple with the operation name as the first element and a list of sources as the second element. Available operations are 'upload' and 'delete'.
    :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files defined in the `operations` attribute. Defaults to 5.
    :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
    :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.
    """  # noqa

    if not operations:
        return ResponseDelivery(fatal_error="No operations given for delivery.")
    if not isinstance(operations, list):
        return ResponseDelivery(
            fatal_error="Operations must be a list because order matters."
        )
    for operation_name in [operation[0] for operation in operations]:
        authorised_operations = get_args(OperationNames)
        if operation_name not in authorised_operations:
            return ResponseDelivery(
                fatal_error=f"Operation '{operation_name}' is not supported. Supported operations are: {authorised_operations}."
            )

    response, _ = _delivery(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=cast(list[tuple[OperationNames, list[str]]], operations),
        max_concurrent_uploads=max_concurrent_uploads,
        chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
        chunk_concurrency=chunk_concurrency,
    )
    return response
