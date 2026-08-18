from pydantic import BaseModel, Field

from delivery_common.domain import Delivery as DeliveryModel
from delivery_common.domain import OperationNames
from pusher.core_functions.constants import (
    CHUNK_CONCURRENCY,
    DEFAULT_CHUNK_SIZE_MB,
    MAX_CONCURRENT_UPLOADS,
)
from pusher.core_functions.core_functions import delete as _delete
from pusher.core_functions.core_functions import delivery as _delivery
from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.delivery import get_deliveries
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
    :param files: Relative or absolute path to the file. `dataset_id` will be used as an anchor (anything before it removed) and `product_id/` prepended before upload.
    :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files defined in the `files` attribute. Defaults to 5.
    :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
    :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.
    :param dry_run: Validate the upload without performing any actual operation in S3.
    """

    def __init__(self, files: list[str]):
        super().__init__(operation=OperationNames.upload, files=files)

    def submit(
        self,
        pushing_entity_id: str,
        product_id: str,
        dataset_id: str,
        anchor: str | None = None,
        raise_on_upload_error: bool = False,
        max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
        chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
        chunk_concurrency: int = CHUNK_CONCURRENCY,
        dry_run: bool = False,
    ) -> ResponseUpload:
        """
        Perform the upload.

        :param pushing_entity_id: The ID of the pushing entity.
        :param product_id: The ID of the product.
        :param dataset_id: The ID of the dataset.
        :param anchor: Specify a different anchor from the default 'dataset_id'.
        :param raise_on_upload_error: If True, raise an exception and stop the upload if any file fails to upload. By default, the upload will continue and skip any files that fail to upload.
        :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files defined in the `operations` attribute. Defaults to 5.
        :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
        :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.

        :return: ResponseUpload object containing the result of the upload.
        """

        if not self.files:
            return ResponseUpload(fatal_error="No files added to upload.")
        response, _ = _upload(
            pushing_entity_id=pushing_entity_id,
            product_id=product_id,
            dataset_id=dataset_id,
            files=self.files,
            anchor=anchor or dataset_id,
            raise_on_upload_error=raise_on_upload_error,
            max_concurrent_uploads=max_concurrent_uploads,
            chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
            chunk_concurrency=chunk_concurrency,
            dry_run=dry_run,
        )
        return response


class Delete(BaseOperation):
    """
    Delete ``files`` from the given dataset and product.
    :param files: S3 Path to the file. `product_id/dataset_id` are prepended by default.
    :param dry_run: Validate the delete without performing any actual operation in S3.
    """

    def __init__(self, files: list[str]):
        super().__init__(operation=OperationNames.delete, files=files)

    def submit(
        self,
        pushing_entity_id: str,
        product_id: str,
        dataset_id: str,
        dry_run: bool = False,
    ) -> ResponseDelete:
        """
        Perform the delete.

        :param pushing_entity_id: The ID of the pushing entity.
        :param product_id: The ID of the product.
        :param dataset_id: The ID of the dataset.

        :return: ResponseDelete object containing the result of the delete.

        """  # noqa
        if not self.files:
            return ResponseDelete(fatal_error="No files added to delete.")
        response, _ = _delete(
            pushing_entity_id=pushing_entity_id,
            product_id=product_id,
            dataset_id=dataset_id,
            files=self.files,
            dry_run=dry_run,
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
    :param dry_run: Validate the delivery without performing any actual operation in S3.
    """  # noqa

    operations: list[Upload | Delete] = Field(default_factory=list)

    def add(self, operation: Upload | Delete) -> None:
        self.operations.append(operation)

    def submit(
        self,
        pushing_entity_id: str,
        product_id: str,
        dataset_id: str,
        anchor: str | None = None,
        raise_on_upload_error: bool = False,
        max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
        chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
        chunk_concurrency: int = CHUNK_CONCURRENCY,
        dry_run: bool = False,
    ) -> ResponseDelivery:
        """
        Perform the delivery by executing all added operations sequentially.

        :param pushing_entity_id: The ID of the pushing entity.
        :param product_id: The ID of the product.
        :param dataset_id: The ID of the dataset.
        :param anchor: Specify a different anchor from the default 'dataset_id'.
        :param raise_on_upload_error: If True, raise an exception and stop the delivery if any file fails to upload. By default, the delivery will continue and skip any files that fail to upload.
        :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files defined in the `operations` attribute. Defaults to 5.
        :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
        :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.

        :return: ResponseDelivery object containing the result of the delivery.
        """  # noqa

        if not self.operations:
            return ResponseDelivery(fatal_error="No operations added to delivery.")
        response, _ = _delivery(
            pushing_entity_id=pushing_entity_id,
            product_id=product_id,
            dataset_id=dataset_id,
            anchor=anchor or dataset_id,
            operations=[(op.operation, op.files) for op in self.operations],
            raise_on_upload_error=raise_on_upload_error,
            max_concurrent_uploads=max_concurrent_uploads,
            chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
            chunk_concurrency=chunk_concurrency,
            dry_run=dry_run,
        )
        return response


def delivery_status(delivery_id: str, pushing_entity_id: str) -> DeliveryModel:
    """
    Get the status of a delivery.

    Right now, returns the delivery.
    """
    delivery = get_deliveries(
        delivery_id=delivery_id,
        pushing_entity_id=pushing_entity_id,
    )
    if not delivery:
        raise ValueError(
            f"Delivery with id {delivery_id} not found for pushing entity {pushing_entity_id}."
        )

    return delivery[0]


def list_deliveries(pushing_entity_id: str) -> list[DeliveryModel]:
    """
    List all deliveries for a given pushing entity.

    :param pushing_entity_id: The ID of the pushing entity.
    :return: A list of DeliveryModel objects sorted by delivery_id in descending order (most recent first).
    """
    deliveries = get_deliveries(pushing_entity_id=pushing_entity_id)
    return deliveries
