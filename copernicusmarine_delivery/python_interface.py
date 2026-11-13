from pydantic import BaseModel, Field

from copernicusmarine_delivery.auth import get_config
from copernicusmarine_delivery.core_functions.constants import (
    CHUNK_CONCURRENCY,
    DEFAULT_CHUNK_SIZE_MB,
    MAX_CONCURRENT_UPLOADS,
)
from copernicusmarine_delivery.core_functions.core_functions import (
    delete as _delete,
)
from copernicusmarine_delivery.core_functions.core_functions import (
    delivery as _delivery,
)
from copernicusmarine_delivery.core_functions.core_functions import (
    publish_draft as _publish_draft,
)
from copernicusmarine_delivery.core_functions.core_functions import (
    upload as _upload,
)
from copernicusmarine_delivery.core_functions.delivery import (
    TimeframeLiteral,
    get_deliveries,
    load_draft,
)
from copernicusmarine_delivery.core_functions.domain import Delete as _Delete
from copernicusmarine_delivery.core_functions.domain import (
    ResponseDelete,
    ResponseDelivery,
    ResponseUpload,
)
from copernicusmarine_delivery.core_functions.domain import Upload as _Upload
from copernicusmarine_delivery.core_functions.utils import megabytes_to_bytes
from copernicusmarine_delivery.environment_variables import (
    COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID,
)
from delivery_common.domain import Delivery as DeliveryModel


class Upload(_Upload):
    """
    Upload ``files`` to the given dataset and product.

    :param files: Relative or absolute path to local files. See `Files paths and anchors` in the documentation.
    :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files defined in the `files` attribute. Defaults to 5.
    :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
    :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.
    :param dry_run: Validate the upload without performing any actual operation in S3.
    """

    def submit(
        self,
        product_id: str,
        dataset_id: str,
        anchor: str | None = None,
        raise_on_upload_error: bool = False,
        max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
        chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
        chunk_concurrency: int = CHUNK_CONCURRENCY,
        dry_run: bool = False,
        **kwargs,
    ) -> ResponseUpload:
        """
        Perform the upload.

        :param product_id: The ID of the product.
        :param dataset_id: The ID of the dataset.
        :param anchor: Optional anchor to convert the local file path to an S3 suffix. See `File paths and anchors` in the documentation.
        :param raise_on_upload_error: If True, raise an exception and stop the upload if any file fails to upload. By default, the upload will continue and skip any files that fail to upload.
        :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files defined in the `operations` attribute. Defaults to 5.
        :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
        :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.
        :param publish: Save the delivery as a draft instead of publishing it. Publish later with :py:func:`~copernicusmarine_delivery.publish_draft`.
        :param delivery_id: ID of an existing draft delivery. The operations are appended to it.

        :return: :py:obj:`~copernicusmarine_delivery.ResponseUpload` object containing the result of the upload.
        """

        if not self.files:
            return ResponseUpload(fatal_error="No files added to upload.")
        response, _ = _upload(
            product_id=product_id,
            dataset_id=dataset_id,
            files=self.files,
            anchor=anchor,
            raise_on_upload_error=raise_on_upload_error,
            max_concurrent_uploads=max_concurrent_uploads,
            chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
            chunk_concurrency=chunk_concurrency,
            dry_run=dry_run,
            on_behalf_of=kwargs.get("pushing_entity_id") or COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID,
        )
        return response


class Delete(_Delete):
    """
    Delete ``files`` from the given dataset and product.

    :param files: Files' Key suffix in S3 without `product_id/dataset_id` in the folder structure. See `File paths and anchors` in the documentation for more details.
    :param dry_run: Validate the delete without performing any actual operation in S3.
    """

    def submit(
        self,
        product_id: str,
        dataset_id: str,
        dry_run: bool = False,
        **kwargs,
    ) -> ResponseDelete:
        """
        Perform the delete.

        :param product_id: The ID of the product.
        :param dataset_id: The ID of the dataset.
        :param publish: Save the delivery as a draft instead of publishing it. Publish later with :py:func:`~copernicusmarine_delivery.publish_draft`.
        :param delivery_id: ID of an existing draft delivery. The operations are appended to it.

        :return: :py:obj:`~copernicusmarine_delivery.ResponseDelete` object containing the result of the delete.

        """  # noqa
        if not self.files:
            return ResponseDelete(fatal_error="No files added to delete.")
        response, _ = _delete(
            product_id=product_id,
            dataset_id=dataset_id,
            files=self.files,
            dry_run=dry_run,
            on_behalf_of=kwargs.get("pushing_entity_id") or COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID,
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
        """Add an operation to the delivery. Operations are performed in the order they are added.

        :param operation: An :class:`Upload` or :class:`Delete` operation.
        """
        self.operations.append(operation)

    def submit(
        self,
        product_id: str,
        dataset_id: str,
        raise_on_upload_error: bool = False,
        max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
        chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
        chunk_concurrency: int = CHUNK_CONCURRENCY,
        dry_run: bool = False,
        publish: bool = True,
        draft_delivery: DeliveryModel | None = None,
        **kwargs,
    ) -> ResponseDelivery:
        """
        Perform the delivery by executing all added operations sequentially.

        :param product_id: The ID of the product.
        :param dataset_id: The ID of the dataset.
        :param anchor: Optional anchor to convert the local file path to an S3 suffix. See `File paths and anchors` in the documentation for more details.
        :param raise_on_upload_error: If True, raise an exception and stop the delivery if any file fails to upload. By default, the delivery will continue and skip any files that fail to upload.
        :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files defined in the `operations` attribute. Defaults to 5.
        :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
        :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.
        :param publish: Save the delivery as a draft instead of publishing it. Publish later with :py:func:`~copernicusmarine_delivery.publish_draft`.
        :param delivery_id: ID of an existing draft delivery. The operations are appended to it.

        :return: :py:obj:`~copernicusmarine_delivery.ResponseDelivery` object containing the result of the delivery.
        """  # noqa

        if not self.operations:
            return ResponseDelivery(fatal_error="No operations added to delivery.")
        response, _ = _delivery(
            product_id=product_id,
            dataset_id=dataset_id,
            operations=self.operations,
            raise_on_upload_error=raise_on_upload_error,
            max_concurrent_uploads=max_concurrent_uploads,
            chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
            chunk_concurrency=chunk_concurrency,
            dry_run=dry_run,
            on_behalf_of=kwargs.get("pushing_entity_id") or COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID,
            publish=publish,
            draft_delivery=draft_delivery,
        )
        return response


class DraftDelivery(BaseModel):
    """
    A delivery built in steps. It is saved as a draft and only published when explicitly done with `publish`.

    ``create`` and ``extend`` upload the added operations and save them in the draft.
    ``publish`` publishes the draft as it is saved.
    To continue a draft in another session, pass its ``delivery_id``.
    The draft is then fetched when the object is created, so it raises if it is not found.
    ``product_id`` and ``dataset_id`` are taken from the draft if not given.

    :param product_id: The ID of the product. Required if there is no ``delivery_id``.
    :param dataset_id: The ID of the dataset. Required if there is no ``delivery_id``.
    :param delivery_id: The ID of an existing draft. Set by :py:meth:`DraftDelivery.create`.
    """

    product_id: str
    dataset_id: str
    delivery_id: str | None = None
    draft_delivery: DeliveryModel | None = None
    operations: list[Upload | Delete] = Field(default_factory=list)

    def __init__(
        self,
        product_id: str | None = None,
        dataset_id: str | None = None,
        delivery_id: str | None = None,
        **kwargs,
    ) -> None:
        draft = None
        if delivery_id is not None:
            draft = load_draft(
                config=get_config(),
                on_behalf_of=kwargs.get("pushing_entity_id") or COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID,
                delivery_id=delivery_id,
            )
            product_id = product_id or draft.product_id
            dataset_id = dataset_id or draft.dataset_id
        elif product_id is None or dataset_id is None:
            raise ValueError("product_id and dataset_id are required when there is no delivery_id to get them from.")
        super().__init__(product_id=product_id, dataset_id=dataset_id, delivery_id=delivery_id, draft_delivery=draft)

    def add(self, operation: Upload | Delete) -> None:
        """Add an operation. It is only saved in the draft by :py:meth:`create` or :py:meth:`extend`.

        :param operation: An :class:`Upload` or :class:`Delete` operation.
        """
        self.operations.append(operation)

    def create(
        self,
        raise_on_upload_error: bool = False,
        max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
        chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
        chunk_concurrency: int = CHUNK_CONCURRENCY,
        dry_run: bool = False,
        **kwargs,
    ) -> ResponseDelivery:
        """
        Upload the added operations and save them in a new draft. Its ``delivery_id`` is set on this object.
        Calling it again creates another new draft and replaces the ``delivery_id``.

        :param raise_on_upload_error: If True, raise an exception and stop if any file fails to upload. By default, the delivery will continue and skip any files that fail to upload.
        :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files. Defaults to 5.
        :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
        :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.
        :param dry_run: Validate without performing any actual operation in S3.

        :return: :py:obj:`~copernicusmarine_delivery.ResponseDelivery` object containing the result of the delivery.
        """
        if not self.operations:
            return ResponseDelivery(fatal_error="No operations added to delivery.")
        on_behalf_of = kwargs.get("pushing_entity_id") or COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID
        response, delivery = _delivery(
            product_id=self.product_id,
            dataset_id=self.dataset_id,
            operations=self.operations,
            raise_on_upload_error=raise_on_upload_error,
            max_concurrent_uploads=max_concurrent_uploads,
            chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
            chunk_concurrency=chunk_concurrency,
            dry_run=dry_run,
            on_behalf_of=on_behalf_of,
            publish=False,
            draft_delivery=None,
        )
        if not dry_run:
            self.delivery_id = response.delivery_id
            self.draft_delivery = delivery
            self.operations = []
        return response

    def extend(
        self,
        raise_on_upload_error: bool = False,
        max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
        chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
        chunk_concurrency: int = CHUNK_CONCURRENCY,
        dry_run: bool = False,
        **kwargs,
    ) -> ResponseDelivery:
        """
        Upload the added operations and append them to the draft ``delivery_id``.

        Same parameters as :py:meth:`DraftDelivery.create`.

        :return: :py:obj:`~copernicusmarine_delivery.ResponseDelivery` object containing the result of the delivery.
        """
        if self.draft_delivery is None:
            raise ValueError("No draft to extend. Call create() first or give a delivery_id.")
        if not self.operations:
            return ResponseDelivery(fatal_error="No operations added to delivery.")
        on_behalf_of = kwargs.get("pushing_entity_id") or COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID
        response, delivery = _delivery(
            product_id=self.product_id,
            dataset_id=self.dataset_id,
            operations=self.operations,
            raise_on_upload_error=raise_on_upload_error,
            max_concurrent_uploads=max_concurrent_uploads,
            chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
            chunk_concurrency=chunk_concurrency,
            dry_run=dry_run,
            on_behalf_of=on_behalf_of,
            publish=False,
            draft_delivery=self.draft_delivery,
        )
        if not dry_run:
            self.draft_delivery = delivery
            self.operations = []
        return response

    def publish(self, dry_run: bool = False, **kwargs) -> DeliveryModel:
        """
        Publish the draft as it is saved. Raises if there are added operations not yet saved with :py:meth:`extend`.

        :param dry_run: Validate without publishing.

        :return: DeliveryModel object of the published delivery.
        """
        if self.delivery_id is None:
            raise ValueError("No draft to publish. Call create() first or give a delivery_id.")
        if self.operations:
            raise ValueError("There are operations not saved in the draft. Call extend() first.")
        on_behalf_of = kwargs.get("pushing_entity_id") or COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID
        return _publish_draft(
            product_id=self.product_id,
            dataset_id=self.dataset_id,
            delivery_id=self.delivery_id,
            dry_run=dry_run,
            on_behalf_of=on_behalf_of,
        )


def delivery_status(delivery_id: str, on_behalf_of: str | None = None) -> DeliveryModel:
    """
    Get the status of a delivery.

    :param delivery_id: The ID of the delivery to check.
    :param on_behalf_of: For internal usage only.

    :return: DeliveryModel object representing the status of the delivery.
    """
    config = get_config()
    delivery = get_deliveries(
        delivery_id=delivery_id,
        config=config,
        on_behalf_of=on_behalf_of,
    )
    if not delivery:
        raise ValueError(f"Delivery with id {delivery_id} not found.")

    return delivery[0]


def list_deliveries(timeframe: TimeframeLiteral = "mo", on_behalf_of: str | None = None) -> list[DeliveryModel]:
    """
    List all deliveries for a given pushing entity.

    :param timeframe: The timeframe to filter deliveries by. Defaults to "mo" (last month).

    :return: A list of DeliveryModel objects sorted by delivery_id in descending order (most recent first).
    """
    config = get_config()
    deliveries = get_deliveries(config=config, timeframe=timeframe, on_behalf_of=on_behalf_of)
    return deliveries
