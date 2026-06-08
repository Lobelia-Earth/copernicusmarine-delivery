from pusher.config.logger import logger
from pusher.config.settings import Settings
from pusher.domain.core_functions import upload as _upload
from pusher.domain.models import ResponseUpload
from pusher.services.ingestion_bucket_service import IngestionBucketService


def upload(
    source: list[str], pushing_entity_id: str, dataset_id: str, product_id: str
) -> ResponseUpload:
    """Upload ``source`` to the given dataset and product."""
    settings = Settings()  # type: ignore
    try:
        ingestion_bucket_service = IngestionBucketService.from_s3_credentials(
            pushing_entity_id=pushing_entity_id,
            access_key_id=settings.access_key_id,
            secret_access_key=settings.secret_access_key,
            endpoint_url=settings.ingestion_buckets_endpoint,
        )
    except Exception:
        logger.error(
            f"Something went wrong while trying to connecto to S3 for pushing entity: {pushing_entity_id}. Check for typos or contact MDS Service Desk"
        )
        raise

    response = _upload(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=source,
        ingestion_bucket_service=ingestion_bucket_service,
        settings=settings,
    )
    return response
