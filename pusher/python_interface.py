from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.models import ResponseUpload


def upload(
    sources: list[str],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    max_concurrent_uploads: int = 10,
) -> ResponseUpload:
    """Upload ``source`` to the given dataset and product."""
    if not sources:
        return ResponseUpload(error="No files added to upload.")
    response = _upload(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=sources,
        max_concurrent_uploads=max_concurrent_uploads,
    )
    return response
