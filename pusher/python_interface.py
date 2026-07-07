from typing import cast, get_args

from delivery_common.domain import Manifest, OperationNames
from pusher.core_functions.core_functions import delete as _delete
from pusher.core_functions.core_functions import delivery as _delivery
from pusher.core_functions.core_functions import get_manifest
from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.models import (
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
    response, _ = _upload(
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
    max_concurrent_uploads: int = 10,
) -> ResponseDelivery:
    """
    Creates a delivery. A delivery is a set of operations (upload or delete) to be performed on a dataset.

    Each operation will be performed sequentially in the order they are given.
    Each operation can have multiple sources (files) to be processed.

    :param operations: A list of operations to be performed. Each operation is a tuple with the operation name as the first element and a list of sources as the second element. Available operations are 'upload' and 'delete'.
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
