import sys

import click

from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.models import ResponseUpload
from pusher.logger import logger

_shared_options = [
    click.option(
        "--source",
        type=str,
        multiple=True,
    ),
    click.option(
        "--dataset-id",
        type=str,
    ),
    click.option(
        "--product-id",
        type=str,
    ),
    click.option(
        "--pushing-entity-id",
        type=str,
    ),
    click.option("--save-delivery-json", is_flag=True)
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
@click.option(
    "--max-concurrent-uploads",
    type=int,
    default=10,
    show_default=True,
),
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
            exclude={"manifest"},
            exclude_none=True,
            exclude_unset=True,
            exclude_defaults=True,
        )
    )
    if save_delivery_json:
        assert response.manifest
        manifest_output_file_name = f"{response.manifest.manifest_id}.json"
        logger.info(f"Writing delivery result to {manifest_output_file_name}")
        with open(manifest_output_file_name, "w") as output_file:
            output_file.write(response.manifest.model_dump_json(indent=2))

@cli.command()
@shared_options
@click.option(
    "--max-concurrent-deletes",
    type=int,
    default=10,
    show_default=True,
),
def delete(
    source: list[str],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    save_delivery_json: bool = False,
    max_concurrent_deletes: int = 10,
) -> None: 
    """Delete SOURCE from the given dataset."""
    if not source:
        logger.error("No files added to delete.")
        click.echo(
            ResponseUpload(fatal_error="No files added to delete.").model_dump_json(
                indent=2,
                exclude_none=True,
                exclude_unset=True,
                exclude_defaults=True,
            )
        )
        sys.exit(1)
    response = _delete(
        pushing_entity_id=pushing_entity_id,
        product_id=product_id,
        dataset_id=dataset_id,
        files=source,
        max_concurrent_deletes=max_concurrent_deletes,
    )
    click.echo(
        response.model_dump_json(
            indent=2,
            exclude={"manifest"},
            exclude_none=True,
            exclude_unset=True,
            exclude_defaults=True,
        )
    )
    if save_delivery_json:
        assert response.manifest
        manifest_output_file_name = f"{response.manifest.manifest_id}.json"
        logger.info(f"Writing delivery result to {manifest_output_file_name}")
        with open(manifest_output_file_name, "w") as output_file:
            output_file.write(response.manifest.model_dump_json(indent=2))

if __name__ == "__main__":
    cli()
