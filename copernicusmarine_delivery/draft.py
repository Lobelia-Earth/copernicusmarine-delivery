"""
Build a delivery in steps through a draft: create an empty draft, extend it with operations, publish it.

Nothing is published until :py:func:`publish`. A draft is identified by its delivery ID,
which is all that is needed to extend or publish it.
"""

from copernicusmarine_delivery.core_functions.constants import (
    CHUNK_CONCURRENCY,
    DEFAULT_CHUNK_SIZE_MB,
    MAX_CONCURRENT_UPLOADS,
)
from copernicusmarine_delivery.core_functions.core_functions import (
    create_draft as _create_draft,
)
from copernicusmarine_delivery.core_functions.core_functions import (
    extend_draft as _extend_draft,
)
from copernicusmarine_delivery.core_functions.core_functions import (
    publish_draft as _publish_draft,
)
from copernicusmarine_delivery.core_functions.domain import ResponseDelivery
from copernicusmarine_delivery.core_functions.utils import megabytes_to_bytes
from copernicusmarine_delivery.python_interface import Delete, Upload, _context
from delivery_common.domain import Delivery as DeliveryModel


def create(product_id: str, dataset_id: str, dry_run: bool = False, staging: bool = False, **kwargs) -> str:
    """
    Create an empty draft for the dataset. Nothing is uploaded and nothing is published.

    See :ref:`Create a draft <draft-create>`.

    :param product_id: The ID of the product.
    :param dataset_id: The ID of the dataset.
    :param dry_run: Validate without saving the draft.
    :param staging: Use the staging environment instead of production.

    :return: The delivery ID of the draft. Keep it: it is needed to extend and publish the draft.
    """
    draft = _create_draft(
        product_id=product_id,
        dataset_id=dataset_id,
        dry_run=dry_run,
        ctx=_context(staging, kwargs),
    )
    return draft.delivery_id


def extend(
    delivery_id: str,
    operations: list[Upload | Delete],
    raise_on_upload_error: bool = False,
    max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
    chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
    chunk_concurrency: int = CHUNK_CONCURRENCY,
    dry_run: bool = False,
    disable_progress_bar: bool = False,
    staging: bool = False,
    **kwargs,
) -> ResponseDelivery:
    """
    Upload the operations and append them to the draft ``delivery_id``. Nothing is published.

    Raises if the draft is not found, for example if it is already published, or if there are no operations.
    The product and the dataset are the ones of the draft.

    See :ref:`Extend a draft <draft-extend>`.

    :param delivery_id: The ID of the draft, from :py:func:`create`.
    :param operations: The :class:`~copernicusmarine_delivery.Upload` and :class:`~copernicusmarine_delivery.Delete` operations to append.
    :param raise_on_upload_error: If True, raise an exception and stop if any file fails to upload. By default, the upload will continue and skip any files that fail to upload.
    :param max_concurrent_uploads: The maximum number of parallel threads that will be used to upload files. Defaults to 5.
    :param chunk_size_mb: The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.
    :param chunk_concurrency: The number of chunks per file that will be uploaded in parallel in multipart uploads. Defaults to 6.
    :param dry_run: Validate without performing any actual operation in S3.
    :param staging: Use the staging environment instead of production.

    :return: :py:obj:`~copernicusmarine_delivery.ResponseDelivery` object containing the result of the extension.
    """  # noqa
    if not operations:
        raise ValueError("No operations to add to the draft.")
    response, _ = _extend_draft(
        ctx=_context(staging, kwargs),
        delivery_id=delivery_id,
        operations=operations,
        raise_on_upload_error=raise_on_upload_error,
        max_concurrent_uploads=max_concurrent_uploads,
        chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
        chunk_concurrency=chunk_concurrency,
        dry_run=dry_run,
        disable_progress_bar=disable_progress_bar,
    )
    return response


def publish(delivery_id: str, dry_run: bool = False, staging: bool = False, **kwargs) -> DeliveryModel:
    """
    Publish the draft ``delivery_id`` as it is saved.

    Raises if the draft is not found, for example if it is already published.

    See :ref:`Publish a draft <draft-publish>`.

    :param delivery_id: The ID of the draft, from :py:func:`create`.
    :param dry_run: Validate without publishing.
    :param staging: Use the staging environment instead of production.

    :return: DeliveryModel object of the published delivery.
    """
    return _publish_draft(
        delivery_id=delivery_id,
        dry_run=dry_run,
        ctx=_context(staging, kwargs),
    )
