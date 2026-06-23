from pusher.core_functions.core_functions import delete as _delete
from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.models import ResponseDelete, ResponseUpload


def upload(
    sources: list[str],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
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
    sources: list[str], pushing_entity_id: str, dataset_id: str, product_id: str
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
