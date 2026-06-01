from pusher.manifests_helper import create_manifest
from pusher.models import Manifest


def upload(product_id: str, dataset_id: str, files: list[str]) -> Manifest:
    manifest = create_manifest(
        producer_id="TODO",
        product_id=product_id,
        dataset_id=dataset_id,
        operation_files_mapping={"upload": files},
    )
    # TODO: Implement the actual upload logic here.
    # TODO: upload manifest to S3
    return manifest
