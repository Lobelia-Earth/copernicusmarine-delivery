import sys

import click

from pusher.core_functions.core_functions import delete as _delete
from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.models import ResponseDelete, ResponseUpload
from pusher.logger import logger

_shared_options = [
    click.option("--source", type=str, multiple=True),
    click.option("--dataset-id", type=str),
    click.option("--product-id", type=str),
    click.option("--pushing-entity-id", type=str),
    click.option(
        "--save-delivery-json",
        is_flag=True,
        help="Output delivery document to a json file.",
    ),
]


def shared_options(func):
    """Prepend in reversed order, as click applies from bottom-up"""
    for option in reversed(_shared_options):
        func = option(func)
    return func


@click.group()
def cli() -> None:
    """Pusher command line interface."""


@cli.command()
@shared_options
@click.option("--max-concurrent-uploads", type=int, default=10, show_default=True)
def upload(
    source: list[str],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    save_delivery_json: bool = False,
    max_concurrent_uploads: int = 10,
) -> None:
    """Upload SOURCE to the given dataset."""
    if not source:
        logger.error("No files added to upload.")
        click.echo(
            ResponseUpload(fatal_error="No files added to upload.").model_dump_json(
                indent=2,
                exclude_none=True,
                exclude_unset=True,
                exclude_defaults=True,
            )
        )
        sys.exit(1)

    response, manifest = _upload(
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
    if save_delivery_json and manifest:
        saving_delivery_file(manifest)


@cli.command()
@shared_options
def delete(
    source: list[str],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    save_delivery_json: bool = False,
) -> None:
    """Delete SOURCE from the given dataset."""
    if not source:
        logger.error("No files added to delete.")
        click.echo(
            ResponseDelete(fatal_error="No files added to delete.").model_dump_json(
                indent=2,
                exclude_none=True,
                exclude_unset=True,
                exclude_defaults=True,
            )
        )
        sys.exit(1)

    response, manifest = _delete(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=source,
    )
    click.echo(
        response.model_dump_json(
            indent=2,
            exclude_none=True,
            exclude_unset=True,
            exclude_defaults=True,
        )
    )
    if save_delivery_json and manifest:
        saving_delivery_file(manifest)


def saving_delivery_file(manifest):
    manifest_output_file_name = f"{manifest.manifest_id}.json"
    logger.info(f"Writing delivery file to {manifest_output_file_name}")
    with open(manifest_output_file_name, "w") as output_file:
        output_file.write(
            manifest.model_dump_json(
                indent=2,
                exclude_none=True,
                exclude_unset=True,
                exclude_defaults=True,
            )
        )


if __name__ == "__main__":
    cli()
