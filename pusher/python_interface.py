from pusher.core_functions import upload as _upload
from pusher.models import Manifest


def upload(source: list[str], dataset_id: str, product_id: str) -> Manifest:
    """Upload ``source`` to the given dataset and product."""
    manifest = _upload(product_id=product_id, dataset_id=dataset_id, files=source)
    return manifest
