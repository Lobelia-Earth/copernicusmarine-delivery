from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.models import ResponseUpload
from pusher.core_functions.settings import Settings


def upload(
    sources: list[str], pushing_entity_id: str, dataset_id: str, product_id: str
) -> ResponseUpload:
    """Upload ``source`` to the given dataset and product."""
    if not sources:
        return ResponseUpload(error="No files added to upload.")
    settings = Settings()  # type: ignore
    response = _upload(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=sources,
        settings=settings,
    )
    return response
