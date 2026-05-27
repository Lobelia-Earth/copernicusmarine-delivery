"""Click-based command line interface for the pusher package."""

from pathlib import Path

import click

from pusher.core_functions import upload as _upload


@click.group()
def cli() -> None:
    """Pusher command line interface."""


@cli.command()
@click.argument(
    "source",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
)
@click.option(
    "--destination",
    "-d",
    required=True,
    help="Destination identifier to upload to.",
)
def upload(source: Path, destination: str) -> None:
    """Upload SOURCE to the given destination."""
    _upload(source=source, destination=destination)


if __name__ == "__main__":
    cli()
