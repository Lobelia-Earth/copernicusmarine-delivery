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
@click.option(
    "--save-delivery-json",
    is_flag=True,
    help="Output delivery document to a json file.",
)
def upload(
    source: list[str],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    max_concurrent_uploads: int = 10,
    save_delivery_json: bool = False,
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
            exclude={"delivery"},
            exclude_none=True,
            exclude_unset=True,
            exclude_defaults=True,
        )
    )
    if save_delivery_json and response.delivery:
        manifest_output_file_name = f"{response.delivery.manifest_id}.json"
        logger.info(f"Writing delivery result to {manifest_output_file_name}")
        with open(manifest_output_file_name, "w") as output_file:
            output_file.write(
                response.delivery.model_dump_json(
                    indent=2,
                    exclude_none=True,
                    exclude_unset=True,
                    exclude_defaults=True,
                )
            )


if __name__ == "__main__":
    cli()
