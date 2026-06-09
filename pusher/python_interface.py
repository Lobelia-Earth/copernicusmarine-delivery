from pusher.config.logger import logger
from pusher.config.settings import Settings
from pusher.domain.core_functions import upload as _upload
from pusher.domain.exceptions import ConnectionRefusedException, NoSuchBucketException
from pusher.domain.models import ResponseUpload
from pusher.services.ingestion_bucket_service import IngestionBucketService


def upload(
    source: list[str], pushing_entity_id: str, dataset_id: str, product_id: str
) -> ResponseUpload:
    """Upload ``source`` to the given dataset and product."""
    if not source:
        return ResponseUpload(error="No files added to upload.")
    settings = Settings()  # type: ignore
    try:
        ingestion_bucket_service = IngestionBucketService.from_s3_credentials(
            pushing_entity_id=pushing_entity_id,
            access_key_id=settings.access_key_id,
            secret_access_key=settings.secret_access_key,
            endpoint_url=settings.ingestion_buckets_endpoint,
        )
    except (ConnectionRefusedException, NoSuchBucketException) as e:
        logger.error(str(e))
        return ResponseUpload(error=str(e))

    response = _upload(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=source,
        ingestion_bucket_service=ingestion_bucket_service,
        settings=settings,
    )
    return response
