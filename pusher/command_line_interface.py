import sys

import click

from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.models import ResponseUpload
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
@click.option(
    "--max-concurrent-uploads",
    type=int,
    default=10,
    show_default=True,
)
def upload(
    source: list[str],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    max_concurrent_uploads: int = 10,
) -> None:
    """Upload SOURCE to the given dataset."""
    if not source:
        logger.error("No files added to upload.")
        click.echo(
            ResponseUpload(error="No files added to upload.").model_dump_json(
                indent=2,
                exclude_none=True,
                exclude_unset=True,
                exclude_defaults=True,
            )
        )
        sys.exit(1)

    response = _upload(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=source,
        max_concurrent_uploads=max_concurrent_uploads,
    )
    click.echo(
        response.model_dump_json(
            indent=2,
            exclude_none=True,
            exclude_unset=True,
            exclude_defaults=True,
        )
    )


if __name__ == "__main__":
    cli()
