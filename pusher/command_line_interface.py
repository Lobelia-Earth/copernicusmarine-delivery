import click

from pusher.core_functions import upload as _upload


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
def upload(source: list[str], dataset_id: str, product_id: str) -> None:
    """Upload SOURCE to the given dataset."""
    manifest = _upload(product_id=product_id, dataset_id=dataset_id, files=source)
    print(manifest.model_dump_json(indent=2))


if __name__ == "__main__":
    cli()
