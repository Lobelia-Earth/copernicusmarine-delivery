import pydantic_core
import click
import sys

from pusher.config.logger import logger
from pusher.config.settings import Settings
from pusher.domain.core_functions import upload as _upload
from pusher.services.ingestion_bucket_service import IngestionBucketService


@click.group()
def cli() -> None:
    """Pusher command line interface."""


@cli.command()
@click.option(
    "--source",
    type=str,
    multiple=True,
)
@click.option(
    "--dataset-id",
    type=str,
)
@click.option(
    "--product-id",
    type=str,
)
@click.option(
    "--pushing-entity-id",
    type=str,
)
def upload(
    source: list[str], pushing_entity_id: str, dataset_id: str, product_id: str
) -> None:
    """Upload SOURCE to the given dataset."""
    try:
        settings = Settings()  # type: ignore
    except pydantic_core.ValidationError as e:
        logger.error(f"Some variables might be missing from the environment, see:\n{e}")
        sys.exit(1)
    try:
        bucket_repository = IngestionBucketService.from_s3_credentials(
            pushing_entity_id=pushing_entity_id,
            access_key_id=settings.access_key_id,
            secret_access_key=settings.secret_access_key,
            endpoint_url=settings.ingestion_buckets_endpoint,
        )
    except Exception:
        logger.error(
            f"Something went wrong while trying to connecto to S3 for pushing entity: {pushing_entity_id}. Check for typos or contact MDS Service Desk"
        )
        sys.exit(1)

    response = _upload(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=source,
        ingestion_bucket_service=bucket_repository,
        settings=settings,
    )
    logger.info(
        response.model_dump_json(
            indent=2,
            exclude_none=True,
            exclude_unset=True,
        )
    )


if __name__ == "__main__":
    cli()
