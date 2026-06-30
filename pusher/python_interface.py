from pusher.core_functions.core_functions import delete as _delete
from pusher.core_functions.core_functions import delivery as _delivery
from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.models import (
    OperationNames,
    ResponseDelete,
    ResponseDelivery,
    ResponseUpload,
)


def upload(
    sources: list[str],
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    max_concurrent_uploads: int = 10,
) -> ResponseUpload:
    """Upload ``sources`` to the given dataset and product."""
    if not sources:
        return ResponseUpload(fatal_error="No files added to upload.")
    response = _upload(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=sources,
        max_concurrent_uploads=max_concurrent_uploads,
    )
    return response


def delete(
    sources: list[str],
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
) -> ResponseDelete:
    """Delete ``sources`` from the given dataset and product."""
    if not sources:
        return ResponseDelete(fatal_error="No files given to delete.")
    response = _delete(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=sources,
    )
    return response


def delivery(
    operations: list[OperationNames],
    operations_sources: list[list[str]],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    max_concurrent_uploads: int = 10,
) -> ResponseDelivery:
    """
    Creates a delivery. A delivery is a set of operations (upload or delete) to be performed on a dataset.

    Each operation will be performed sequentially in the order they are given.
    Each operation can have multiple sources (files) to be processed.

    It is important to sort the operations and their sources in the same order, so that the first operation corresponds to the first list of sources, the second operation to the second list of sources, and so on.
    """  # noqa

    if not operations:
        return ResponseDelivery(fatal_error="No operations given for delivery.")
    if not len(operations) == len(operations_sources):
        # TODO: should we raise here?
        return ResponseDelivery(
            fatal_error="The number of operations and the number of sources lists must be the same."
        )
    return _delivery(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        operations=operations,
        operations_sources=operations_sources,
        max_concurrent_uploads=max_concurrent_uploads,
    )
