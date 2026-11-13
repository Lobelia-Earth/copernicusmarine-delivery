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

from copernicusmarine_delivery.auth import get_config
from copernicusmarine_delivery.core_functions.constants import (
    CHUNK_CONCURRENCY,
    DEFAULT_CHUNK_SIZE_MB,
    MAX_CONCURRENT_UPLOADS,
)
from copernicusmarine_delivery.core_functions.core_functions import delete as _delete
from copernicusmarine_delivery.core_functions.core_functions import (
    delivery as _delivery,
)
from copernicusmarine_delivery.core_functions.core_functions import (
    publish_draft as _publish_draft,
)
from copernicusmarine_delivery.core_functions.core_functions import (
    upload as _upload,
)
from copernicusmarine_delivery.core_functions.delivery import TimeframeLiteral, get_deliveries, load_draft
from copernicusmarine_delivery.core_functions.domain import (
    BaseResponse,
    DeliveryFile,
    ResponseDelete,
    ResponseUpload,
)
from copernicusmarine_delivery.core_functions.utils import megabytes_to_bytes
from copernicusmarine_delivery.logger import LOG_LEVELS, logger
from delivery_common.domain import Delivery


def _exception_to_sentence(exception: Exception) -> str:
    return _camel_case_to_sentence(exception.__class__.__name__)


def _title_case_to_lower_case(identifier: str) -> str:
    return identifier.lower() if identifier.istitle() else identifier


def _camel_case_to_sentence(identifier: str) -> str:
    matches = finditer(".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)", identifier)
    capital_words = list(map(lambda match: match.group(0), matches))
    first_word = capital_words[:1]
    other_words = capital_words[1:]
    sentence = chain(first_word, map(_title_case_to_lower_case, other_words))
    return " ".join(sentence)


def _api_error_detail(exception: Exception) -> str | None:
    """API `detail` from an HTTPError response, else None."""
    response = getattr(exception, "response", None)
    if response is None:
        return None
    try:
        detail = response.json()["detail"]
    except (ValueError, KeyError, TypeError):  # body not JSON / no `detail`
        return None
    return detail if isinstance(detail, str) else json.dumps(detail)


def _exception_message(exception: Exception) -> str:
    custom_exception_message = getattr(exception, "custom_exception_message", None)
    if custom_exception_message:
        return custom_exception_message
    exception_string = _api_error_detail(exception) or str(exception).strip('"')
    details = f": {exception_string}" if exception_string else ""
    return _exception_to_sentence(exception) + details


def log_exception_and_exit(function: Callable) -> Any:
    @wraps(function)
    def wrapper(*args, **kwargs):
        logger.setLevel(kwargs.pop("log_level"))
        try:
            return function(*args, **kwargs)
        except Exception as exception:
            message = _exception_message(exception)
            logger.error(message)
            if kwargs.get("output") == "json":
                click.echo(BaseResponse(fatal_error=message).model_dump_json(indent=2))
            sys.exit(1)

    return wrapper


_shared_options = [
    click.option("-i", "--dataset-id", type=str, help="ID of the dataset.", required=True),
    click.option("-p", "--product-id", type=str, help="ID of the product.", required=True),
    click.option(
        "--save-delivery-json",
        is_flag=True,
        help="Output delivery document to a json file named with the deliveryID.",
    ),
    click.option(
        "--show-less",
        is_flag=True,
        help="Show less output: only print the delivery ID.",
    ),
    click.option(
        "--output",
        type=click.Choice(["text", "json"]),
        default="text",
        show_default=True,
        help="Output format.",
    ),
    click.option(
        "--dry-run",
        is_flag=True,
        help="Validate the upload without performing any actual operation in S3.",
    ),
]

_draft_options = [
    click.option(
        "--delivery-id",
        type=str,
        default=None,
        help="ID of an existing draft delivery. The operations defined are appended to it.",
    ),
]

file_option = click.option(
    "--file",
    required=True,
    help="A path to a yaml file that describes the deliver, "
    "containing a set of operations [upload, delete] and their relative files."
    "See the documentation for the format of the delivery file",
)

pushing_entity_id_option = click.option(
    "-e",
    "--pushing-entity-id",
    envvar="COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID",
    default=None,
    hidden=True,
    help="ADMIN only: act on behalf of this pushing entity.",
)

log_level_option = click.option(
    "--log-level",
    type=click.Choice(LOG_LEVELS, case_sensitive=False),
    envvar="COPERNICUSMARINE_SERVICE_LOG_LEVEL",
    default="INFO",
    show_default=True,
    help="Level of the logs printed to the standard error.",
)

_upload_shared_options = [
    click.option(
        "--raise-on-upload-error",
        is_flag=True,
        help="Raise an exception and stop the delivery if any file fails to upload. "
        "By default, the delivery will continue and skip any files that fail to upload.",
    ),
    click.option(
        "--max-concurrent-uploads",
        type=int,
        default=MAX_CONCURRENT_UPLOADS,
        show_default=True,
        help="The maximum number of parallel threads that will be used to upload files defined in the `sources` attribute. Defaults to 5.",
    ),
    click.option(
        "--chunk-size-mb",
        type=int,
        default=DEFAULT_CHUNK_SIZE_MB,
        show_default=True,
        help="The chunk size (in MB) in which the files will be split into for multipart uploads. Defaults to 16 MB.",
    ),
    click.option(
        "--chunk-concurrency",
        type=int,
        default=CHUNK_CONCURRENCY,
        show_default=True,
        help="Number of parts uploaded in parallel per file (multipart upload).",
    ),
    click.option(
        "--disable-progress-bar",
        is_flag=True,
        default=False,
        show_default=True,
        help="Set this argument if you want to disable the progress bar",
    ),
]


def base_options(func):
    """Prepend in reversed order, as click applies from bottom-up"""
    for option in reversed(_shared_options):
        func = option(func)
    return func


def draft_options(func):
    for option in reversed(_draft_options):
        func = option(func)
    return base_options(func)


def upload_shared_options(func):
    """Prepend in reversed order, as click applies from bottom-up"""
    for option in reversed(_upload_shared_options):
        func = option(func)
    return func


class OrderCommands(click.Group):
    def list_commands(self, ctx: click.Context) -> list[str]:
        return list(self.commands)


@click.group(cls=OrderCommands)
def cli(max_content_width=200) -> None:
    """Pusher command line interface."""


@cli.group("delivery", cls=OrderCommands, invoke_without_command=True, no_args_is_help=True)
@file_option
@draft_options
@upload_shared_options
@pushing_entity_id_option
@click.pass_context
@log_level_option
@log_exception_and_exit
def delivery_group(
    ctx: click.Context,
    file: Path | None,
    dataset_id: str | None,
    product_id: str | None,
    pushing_entity_id: str | None,
    raise_on_upload_error: bool,
    save_delivery_json: bool,
    max_concurrent_uploads: int,
    chunk_size_mb: int,
    chunk_concurrency: int,
    dry_run: bool,
    disable_progress_bar: bool,
) -> None:
    """Perform a delivery with multiple operations [upload, delete].

    Without a subcommand, the whole delivery is performed in one step.
    Use the subcommands to build it in steps through a draft.
    """
    if ctx.invoked_subcommand is None:
        if file is None or dataset_id is None or product_id is None:
            raise click.UsageError("Without a subcommand, --file, --dataset-id and --product-id are required.")
        with open(file) as f:
            delivery_file = DeliveryFile.model_validate(yaml.safe_load(f))

        response_delivery, delivery = _delivery(
            [operation for operation in delivery_file.delivery],
            on_behalf_of=pushing_entity_id,
            dataset_id=dataset_id,
            product_id=product_id,
            raise_on_upload_error=raise_on_upload_error,
            max_concurrent_uploads=max_concurrent_uploads,
            chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
            chunk_concurrency=chunk_concurrency,
            dry_run=dry_run,
            publish=True,
            disable_progress_bar=disable_progress_bar,
        )
        if save_delivery_json and delivery:
            saving_delivery_file(delivery)

        click.echo(message=f"{response_delivery}")


# Group options are only required when no subcommand is given, checked in the callback.
for _param in delivery_group.params:
    _param.required = False


@delivery_group.command("create-draft")
@file_option
@base_options
@upload_shared_options
@pushing_entity_id_option
@click.option(
    "--source",
    type=str,
    multiple=True,
    help=(
        """Relative or absolute path to the file.
        If `anchor` is set, anything before it will be removed.
        Please consider that upon uploading, a prefix consisting of `product_id/dataset_id` is prepended to the final S3 Path."""
    ),
)
@log_exception_and_exit
def create_draft(
    file: Path,
    dataset_id: str,
    product_id: str,
    pushing_entity_id: str | None = None,
    raise_on_upload_error: bool = False,
    save_delivery_json: bool = False,
    max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
    chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
    chunk_concurrency: int = CHUNK_CONCURRENCY,
    dry_run: bool = False,
    show_less: bool = False,
    output: str = "text",
    disable_progress_bar: bool = False,
) -> None:
    """Create a draft delivery from a file. Its delivery ID is printed."""
    with open(file) as f:
        delivery_file = DeliveryFile.model_validate(yaml.safe_load(f))

    response_delivery, delivery = _delivery(
        [operation for operation in delivery_file.delivery],
        on_behalf_of=pushing_entity_id,
        dataset_id=dataset_id,
        product_id=product_id,
        raise_on_upload_error=raise_on_upload_error,
        max_concurrent_uploads=max_concurrent_uploads,
        chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
        chunk_concurrency=chunk_concurrency,
        dry_run=dry_run,
        publish=False,
        disable_progress_bar=disable_progress_bar,
    )
    if save_delivery_json and delivery:
        saving_delivery_file(delivery)

    if output == "json":
        click.echo(
            json.dumps({"delivery_id": response_delivery.delivery_id})
            if show_less
            else response_delivery.model_dump_json(indent=2)
        )
    else:
        click.echo(response_delivery.delivery_id if show_less else f"{response_delivery}")
    if not response_delivery.is_succesful():
        sys.exit(1)


@delivery_group.command("extend-draft")
@file_option
@click.option("--delivery-id", type=str, required=True, help="ID of the draft delivery to extend.")
@base_options
@upload_shared_options
@pushing_entity_id_option
@log_exception_and_exit
def extend_draft(
    file: Path,
    delivery_id: str,
    pushing_entity_id: str | None,
    raise_on_upload_error: bool,
    save_delivery_json: bool,
    max_concurrent_uploads: int,
    chunk_size_mb: int,
    chunk_concurrency: int,
    dry_run: bool,
    disable_progess_bar: bool,
) -> None:
    """Append the operations of a file to an existing draft delivery."""
    with open(file) as f:
        delivery_file = DeliveryFile.model_validate(yaml.safe_load(f))

    draft_delivery = load_draft(get_config(), pushing_entity_id, delivery_id)

    response_delivery, delivery = _delivery(
        [operation for operation in delivery_file.delivery],
        on_behalf_of=pushing_entity_id,
        dataset_id=draft_delivery.dataset_id,
        product_id=draft_delivery.product_id,
        raise_on_upload_error=raise_on_upload_error,
        max_concurrent_uploads=max_concurrent_uploads,
        chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
        chunk_concurrency=chunk_concurrency,
        dry_run=dry_run,
        publish=False,
        draft_delivery=draft_delivery,
        disable_progress_bar=disable_progess_bar,
    )
    if save_delivery_json and delivery:
        saving_delivery_file(delivery)

    click.echo(message=f"{response_delivery}")


@delivery_group.command("publish-draft")
@click.option("--delivery-id", type=str, required=True, help="ID of the draft delivery to publish.")
@click.option("--dataset-id", type=str, required=True, help="ID of the dataset.")
@click.option("--product-id", type=str, required=True, help="ID of the product.")
@click.option("--dry-run", is_flag=True, help="Validate without publishing.")
@pushing_entity_id_option
@log_exception_and_exit
def publish_draft(
    delivery_id: str,
    dataset_id: str,
    product_id: str,
    pushing_entity_id: str | None,
    dry_run: bool = False,
) -> None:
    """Publish a draft delivery, previously saved with --no-publish, as is."""
    delivery = _publish_draft(
        product_id=product_id,
        dataset_id=dataset_id,
        delivery_id=delivery_id,
        dry_run=dry_run,
        on_behalf_of=pushing_entity_id,
    )
    click.echo(message=delivery.get_summary(show_all=False))


@cli.command()
@click.option(
    "--source",
    type=str,
    multiple=True,
    help=(
        """Relative or absolute path to the file.
        If `anchor` is set, anything before it will be removed.
        Please consider that upon uploading, a prefix consisting of `product_id/dataset_id` is prepended to the final S3 Path."""
    ),
)
@click.option(
    "--anchor",
    type=str,
    required=False,
    default=None,
    help=(
        """
        If set, anything before and up to such anchor will be removed
        from the given path upon uploading to the ingestion bucket.
        For more information, please refer to the documentation and, in particular, the `Folder structure and path` section.
        """
    ),
)
@base_options
@upload_shared_options
@pushing_entity_id_option
@log_level_option
@log_exception_and_exit
def upload(
    source: list[str],
    dataset_id: str,
    product_id: str,
    pushing_entity_id: str | None,
    anchor: str | None,
    save_delivery_json: bool = False,
    raise_on_upload_error: bool = False,
    max_concurrent_uploads: int = MAX_CONCURRENT_UPLOADS,
    chunk_size_mb: int = DEFAULT_CHUNK_SIZE_MB,
    chunk_concurrency: int = CHUNK_CONCURRENCY,
    dry_run: bool = False,
    show_less: bool = False,
    output: str = "text",
    disable_progress_bar: bool = False,
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

    response, delivery = _upload(
        product_id=product_id,
        dataset_id=dataset_id,
        files=source,
        anchor=anchor,
        raise_on_upload_error=raise_on_upload_error,
        max_concurrent_uploads=max_concurrent_uploads,
        chunk_size_bytes=megabytes_to_bytes(chunk_size_mb),
        chunk_concurrency=chunk_concurrency,
        dry_run=dry_run,
        on_behalf_of=pushing_entity_id,
        disable_progress_bar=disable_progress_bar,
    )
    if save_delivery_json and delivery:
        saving_delivery_file(delivery)

    if output == "json":
        click.echo(
            json.dumps({"delivery_id": response.delivery_id}) if show_less else response.model_dump_json(indent=2)
        )
    else:
        click.echo(response.delivery_id if show_less else f"{response}")
    if not response.is_succesful():
        sys.exit(1)


@cli.command()
@click.option(
    "--source",
    type=str,
    multiple=True,
    help="S3 Path to the file. `product_id/dataset_id` are prepended by default.",
)
@base_options
@pushing_entity_id_option
@log_level_option
@log_exception_and_exit
def delete(
    source: list[str],
    dataset_id: str,
    product_id: str,
    pushing_entity_id: str | None,
    save_delivery_json: bool = False,
    dry_run: bool = False,
    show_less: bool = False,
    output: str = "text",
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

    response, delivery = _delete(
        product_id=product_id,
        dataset_id=dataset_id,
        files=source,
        dry_run=dry_run,
        on_behalf_of=pushing_entity_id,
    )

    if save_delivery_json:
        saving_delivery_file(delivery)

    if output == "json":
        click.echo(
            json.dumps({"delivery_id": response.delivery_id}) if show_less else response.model_dump_json(indent=2)
        )
    else:
        click.echo(response.delivery_id if show_less else f"{response}")
    if not response.is_succesful():
        sys.exit(1)


def saving_delivery_file(delivery: Delivery) -> None:
    delivery_output_file_name = f"{delivery.delivery_id}.json"
    logger.info(f"Writing delivery file to {delivery_output_file_name}")
    with open(delivery_output_file_name, "w") as output_file:
        output_file.write(
            delivery.model_dump_json(
                indent=2,
            )
        )


@cli.command()
@click.option("-d", "--delivery-id", help="ID of the delivery to check status for.")
@click.option(
    "--delivery-json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to an existing delivery json file",
)
@click.option(
    "--show-all",
    is_flag=True,
    help="Show all operations and file statuses. By default, only summary is shown.",
)
@click.option(
    "--show-less",
    is_flag=True,
    help="Show less output: only print the delivery status.",
)
@click.option(
    "--output",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format.",
)
@pushing_entity_id_option
@log_level_option
@log_exception_and_exit
def status(
    delivery_id: str | None = None,
    delivery_json: Path | None = None,
    pushing_entity_id: str | None = None,
    show_all: bool = False,
    show_less: bool = False,
    output: str = "text",
) -> None:
    """Get the status of a delivery (upload and/or delete). Specify either
    delivery_id or a path to a delivery json file.
    """
    if not delivery_id and not delivery_json:
        raise click.UsageError(message=("Specify either delivery_id or a path to a delivery json file."))
    config = get_config()
    if delivery_json:
        try:
            with open(delivery_json) as delivery_file:
                delivery = Delivery.model_validate(json.load(delivery_file))
        except (json.JSONDecodeError, ValidationError) as e:
            raise click.UsageError(f"Invalid delivery json: {e}")
        delivery_id = delivery.delivery_id

    deliveries = get_deliveries(
        delivery_id=delivery_id,
        config=config,
        on_behalf_of=pushing_entity_id,
    )
    delivery = deliveries[0] if deliveries else None
    if not delivery:
        raise ValueError(f"Delivery with id {delivery_id} not found.")
    if output == "json":
        click.echo(json.dumps({"status": delivery.status.value}) if show_less else delivery.model_dump_json(indent=2))
    else:
        click.echo(delivery.status.value if show_less else delivery.get_summary(show_all=show_all))
    if not delivery.is_succesful():
        sys.exit(1)


@cli.command()
@pushing_entity_id_option
@click.option(
    "--timeframe",
    type=click.Choice(["s", "m", "h", "d", "w", "mo", "y", "all"]),
    default="mo",
    help="The timeframe to filter deliveries by. Defaults to 'mo' (last month).",
)
@log_level_option
@log_exception_and_exit
def list_deliveries(timeframe: TimeframeLiteral, pushing_entity_id: str | None = None) -> None:
    """
    List all deliveries for the pushing entity tied to the current credentials.
    The result is sorted by delivery_id in descending order (most recent first).
    """
    config = get_config()
    deliveries = get_deliveries(
        config=config,
        on_behalf_of=pushing_entity_id,
        timeframe=timeframe,
    )
    print_list_deliveries(deliveries)


def print_list_deliveries(deliveries: list[Delivery]) -> None:
    if not deliveries:
        click.echo("No deliveries found.")
        return
    click.echo("\nDeliveries:\n")
    for delivery in deliveries:
        click.echo(message=f"{delivery}")


if __name__ == "__main__":
    cli()
