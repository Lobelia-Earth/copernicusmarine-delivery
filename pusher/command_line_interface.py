import json
import sys
from functools import wraps
from itertools import chain
from pathlib import Path
from re import finditer
from typing import Any, Callable

import click
import yaml
from pydantic import ValidationError

from delivery_common.domain import Manifest
from pusher.core_functions.constants import (
    CHUNK_CONCURRENCY,
    DEFAULT_CHUNK_SIZE_MB,
    MAX_CONCURRENT_UPLOADS,
)
from pusher.core_functions.core_functions import delete as _delete
from pusher.core_functions.core_functions import delivery as _delivery
from pusher.core_functions.core_functions import get_manifest
from pusher.core_functions.core_functions import upload as _upload
from pusher.core_functions.domain import DeliveryFile, ResponseDelete, ResponseUpload
from pusher.core_functions.utils import megabytes_to_bytes
from pusher.logger import logger


def _exception_to_sentence(exception: Exception) -> str:
    return _camel_case_to_sentence(exception.__class__.__name__)


def _title_case_to_lower_case(identifier: str) -> str:
    return identifier.lower() if identifier.istitle() else identifier


def _camel_case_to_sentence(identifier: str) -> str:
    matches = finditer(
        ".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)", identifier
    )
    capital_words = list(map(lambda match: match.group(0), matches))
    first_word = capital_words[:1]
    other_words = capital_words[1:]
    sentence = chain(first_word, map(_title_case_to_lower_case, other_words))
    return " ".join(sentence)


def _log_exception(log_function: Callable, exception: Exception):
    exception_string = str(exception).strip('"')
    details = f": {exception_string}" if exception_string else ""
    message = _exception_to_sentence(exception) + details
    log_function(message)


def log_exception_and_exit(function: Callable) -> Any:
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as exception:
            try:
                custom_exception_message = exception.__getattribute__(
                    "custom_exception_message"
                )
                logger.error(custom_exception_message)
            except AttributeError:
                _log_exception(logger.error, exception)
            exit(1)

    return wrapper


_shared_options = [
    click.option("--dataset-id", type=str, help="ID of the dataset.", required=True),
    click.option("--product-id", type=str, help="ID of the product.", required=True),
    click.option(
        "--pushing-entity-id", type=str, help="ID of the pushing entity.", required=True
    ),
    click.option(
        "--save-delivery-json",
        is_flag=True,
        help="Output delivery document to a json file named with the deliveryID.",
    ),
]


def shared_options(func):
    """Prepend in reversed order, as click applies from bottom-up"""
    for option in reversed(_shared_options):
        func = option(func)
    return func


class OrderCommands(click.Group):
    def list_commands(self, ctx: click.Context) -> list[str]:
        return list(self.commands)


@click.group(cls=OrderCommands)
def cli(max_content_width=200) -> None:
    """Pusher command line interface."""


@cli.command()
@click.option(
    "--file",
    required=True,
    help="A path to a yaml file that describes the deliver, "
    "containing a set of operations [upload, delete] and their relative files."
    "See the documentation for the format of the delivery file",
)
@shared_options
@click.option(
    "--max-concurrent-uploads",
    type=int,
    default=MAX_CONCURRENT_UPLOADS,
    show_default=True,
    help="The maximum number of parallel threads that will be used to upload files defined in the `sources` attribute. Defaults to 5.",
)
@click.option(
    "--chunk-size-mb",
    type=int,
    default=DEFAULT_CHUNK_SIZE_MB,
    show_default=True,
    help="The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.",
)
@click.option(
    "--chunk-concurrency",
    type=int,
    default=CHUNK_CONCURRENCY,
    show_default=True,
    help="Number of parts uploaded in parallel per file (multipart upload).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate the delivery and print out the expected operations.",
)
@log_exception_and_exit
def delivery(
    file: Path,
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    save_delivery_json: bool = False,
    max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
    chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
    chunk_concurrency: int = CHUNK_CONCURRENCY,
    dry_run: bool = False,
) -> None:
    """Perform a delivery with multiple operations [upload, delete]."""
    with open(file) as f:
        delivery_file = DeliveryFile.model_validate(yaml.safe_load(f))

    response_delivery, manifest = _delivery(
        [
            (operation.operation, operation.files)
            for operation in delivery_file.delivery
        ],
        pushing_entity_id=pushing_entity_id,
        dataset_id=dataset_id,
        product_id=product_id,
        max_concurrent_uploads=max_concurrent_uploads,
        chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
        chunk_concurrency=chunk_concurrency,
        dry_run=dry_run,
    )
    if dry_run and manifest:
        print_dry_run_summary(manifest)
    else:
        click.echo(
            response_delivery.model_dump_json(
                indent=2,
                exclude_none=True,
                exclude_unset=True,
                exclude_defaults=True,
            )
        )
    if save_delivery_json and manifest:
        saving_delivery_file(manifest)


@cli.command()
@click.option(
    "--source",
    type=str,
    multiple=True,
    help="Relative path to the file. `product_id/dataset_id` are prepended to the file.",
)
@shared_options
@click.option(
    "--max-concurrent-uploads",
    type=int,
    default=MAX_CONCURRENT_UPLOADS,
    show_default=True,
    help="The maximum number of parallel threads that will be used to upload files defined in the `sources` attribute. Defaults to 5.",
)
@click.option(
    "--chunk-size-mb",
    type=int,
    default=DEFAULT_CHUNK_SIZE_MB,
    show_default=True,
    help="The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.",
)
@click.option(
    "--chunk-concurrency",
    type=int,
    default=CHUNK_CONCURRENCY,
    show_default=True,
    help="Number of parts uploaded in parallel per file (multipart upload).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate the upload and print out the expected operations.",
)
@log_exception_and_exit
def upload(
    source: list[str],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    save_delivery_json: bool = False,
    max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
    chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
    chunk_concurrency: int = CHUNK_CONCURRENCY,
    dry_run: bool = False,
) -> None:
    """Upload local SOURCE(S) of the given dataset to MDS."""
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
        chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
        chunk_concurrency=chunk_concurrency,
        dry_run=dry_run,
    )
    if dry_run and manifest:
        print_dry_run_summary(manifest)
    else:
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
@click.option(
    "--source",
    type=str,
    multiple=True,
    help="S3 Path to the file. `product_id/dataset_id` are prepended by default.",
)
@shared_options
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate the delivery and print out the expected operations.",
)
@log_exception_and_exit
def delete(
    source: list[str],
    pushing_entity_id: str,
    dataset_id: str,
    product_id: str,
    save_delivery_json: bool = False,
    dry_run: bool = False,
) -> None:
    """Delete remote SOURCE(S) from the given dataset from MDS."""
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
        dry_run=dry_run,
    )
    if dry_run and manifest:
        print_dry_run_summary(manifest)
    else:
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


def saving_delivery_file(manifest: Manifest) -> None:
    manifest_output_file_name = f"{manifest.manifest_id}.json"
    logger.info(f"Writing delivery file to {manifest_output_file_name}")
    with open(manifest_output_file_name, "w") as output_file:
        output_file.write(
            manifest.model_dump_json(
                indent=2,
            )
        )


def print_dry_run_summary(manifest: Manifest) -> None:
    print("\n[DRY RUN] The following operations would be submitted:")
    uploads, deletes = 0, 0
    for operation in manifest.operations:
        if operation.operation == "upload":
            uploads += 1
            print("\n")
            for file in operation.files:
                print(f"\t[UPLOAD] {file.key_suffix} -> {file.key_suffix}")
        elif operation.operation == "delete":
            print("\n")
            deletes += 1
            for file in operation.files:
                print(f"\t[DELETE] {file.key_suffix}")

    print(f"\nTotal: {uploads} uploads, {deletes} deletes.\n")


@cli.command()
@click.option("--delivery-id", help="ID of the delivery to check status for.")
@click.option("--pushing-entity-id", help="ID of the pushing entity.")
@click.option("--product-id", help="ID of the product.")
@click.option("--dataset-id", help="ID of the dataset.")
@click.option(
    "--delivery-json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to an existing delivery json file",
)
@log_exception_and_exit
def status(
    delivery_id: str | None = None,
    pushing_entity_id: str | None = None,
    product_id: str | None = None,
    dataset_id: str | None = None,
    delivery_json: Path | None = None,
) -> None:
    """Get the status of a delivery (upload and/or delete). Specify either ids
    [delivery_id, pushing_entity_id, product_id, dataset_id] or a path to a delivery json file.
    """
    if (
        not all([delivery_id, pushing_entity_id, product_id, dataset_id])
        and not delivery_json
    ):
        raise click.UsageError(
            message=(
                "Specify either the set of ids delivery_id, pushing_entity_id, "
                "product_id, dataset_id] or a path to a delivery json file."
            )
        )

    if delivery_json:
        try:
            with open(delivery_json) as delivery_file:
                manifest = Manifest.model_validate(json.load(delivery_file))
        except (json.JSONDecodeError, ValidationError) as e:
            raise click.UsageError(f"Invalid delivery json: {e}")
        delivery_id = manifest.manifest_id
        pushing_entity_id = manifest.pushing_entity_id
        product_id = manifest.product_id
        dataset_id = manifest.dataset_id
    else:
        delivery_id = delivery_id
        pushing_entity_id = pushing_entity_id
        product_id = product_id
        dataset_id = dataset_id

    manifest = get_manifest(
        delivery_id=delivery_id,  # type: ignore
        pushing_entity_id=pushing_entity_id,  # type: ignore
        product_id=product_id,  # type: ignore
        dataset_id=dataset_id,  # type: ignore
    )
    click.echo(
        manifest.model_dump_json(
            indent=2,
            exclude_none=True,
        )
    )


if __name__ == "__main__":
    cli()
