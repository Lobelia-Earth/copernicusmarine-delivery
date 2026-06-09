import sys

import click
import pydantic_core

from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.models import ResponseUpload
from pusher.core_functions.settings import Settings
from pusher.logger import logger


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
    if not source:
        logger.warning(
            ResponseUpload(error="No files added to upload.").model_dump_json(
                indent=2,
                exclude_none=True,
                exclude_unset=True,
            )
        )
        sys.exit(1)
    try:
        # Both pyright and ty complain about not having the mandatory attributes
        # which are set by environment.
        settings = Settings()  # type: ignore
    except pydantic_core.ValidationError as e:
        logger.error(f"Some variables might be missing from the environment, see:\n{e}")
        sys.exit(1)

    response = _upload(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=source,
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
