import json

import pytest
from click.testing import CliRunner

from copernicusmarine_delivery import Delete, InvalidDeliverySizeError, list_deliveries, publish_draft
from copernicusmarine_delivery import Delivery as PythonDelivery
from copernicusmarine_delivery.command_line_interface import cli
from copernicusmarine_delivery.context import build_context
from copernicusmarine_delivery.core_functions.delivery import (
    DraftDeliveryNotFoundError,
    load_draft,
)
from copernicusmarine_delivery.core_functions.delivery_validator import validate_delivery_sizes
from copernicusmarine_delivery.core_functions.domain import APILimits, FileToUpload, ToUploadOperation
from delivery_common.domain import Delivery, UploadFile, UploadOperation

PRODUCT_ID = "GLOBAL_ANALYSISFORECAST_BGC_001_028"
DATASET_ID = "cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m_202311"
IDS = ["--dataset-id", DATASET_ID, "--product-id", PRODUCT_ID]
FILE_1 = "tests/resources/dataset1/file1.txt"
FILE_2 = "tests/resources/dataset1/file2.txt"


def _run(*args: str):
    return CliRunner().invoke(cli, ["delivery", *args])


def _sources(files: tuple[str, ...]) -> list[str]:
    return [arg for file in files for arg in ("--source", file)]


def _create_draft(*files: str, operation: str = "delete", extra: tuple[str, ...] = ()):
    return _run("create-draft", *IDS, "--operation", operation, *_sources(files), "--show-less", *extra)


def _new_draft(*files: str, operation: str = "delete", extra: tuple[str, ...] = ()) -> str:
    result = _create_draft(*files, operation=operation, extra=extra)
    assert result.exit_code == 0
    return result.stdout.strip()


def _extend_draft(delivery_id: str, *files: str, operation: str = "delete", extra: tuple[str, ...] = ()):
    return _run(
        "extend-draft", "--delivery-id", delivery_id, "--operation", operation, *_sources(files), "--show-less", *extra
    )


def _publish_draft(delivery_id: str, *extra: str):
    return _run("publish-draft", "--delivery-id", delivery_id, *extra)


def _saved_draft(delivery_id: str) -> Delivery:
    return load_draft(ctx=build_context(), delivery_id=delivery_id)


def _delivery_file(tmp_path, operations: list[dict]) -> str:
    path = tmp_path / "delivery.yaml"
    path.write_text(json.dumps({"delivery": operations}))
    return str(path)


def test_create_draft_saves_draft_only(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = _new_draft("a.txt")

    assert list_deliveries(timeframe="all") == []
    draft = _saved_draft(delivery_id)
    assert draft.is_draft is True
    assert len(draft.operations) == 1


def test_create_draft_output_json(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    result = _create_draft("a.txt", extra=("--output", "json"))

    assert result.exit_code == 0
    assert _saved_draft(json.loads(result.stdout)["delivery_id"]).is_draft is True


def test_extend_with_operation(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = _new_draft("a.txt")
    result = _extend_draft(delivery_id, "b.txt")

    assert result.exit_code == 0
    assert result.stdout.strip() == delivery_id
    draft = _saved_draft(delivery_id)
    assert draft.is_draft is True
    assert len(draft.operations) == 2


def test_extend_with_file(tmp_path, glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = _new_draft("a.txt")
    file = _delivery_file(tmp_path, [{"operation": "delete", "files": ["b.txt", "c.txt"]}])

    result = _run("extend-draft", "--delivery-id", delivery_id, "--file", file)

    assert result.exit_code == 0
    assert len(_saved_draft(delivery_id).operations) == 2


def test_upload_draft_extend_then_publish(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = _new_draft(FILE_1, operation="upload", extra=("--anchor", "dataset1"))
    assert _extend_draft(delivery_id, FILE_2, operation="upload", extra=("--anchor", "dataset1")).exit_code == 0
    assert _extend_draft(delivery_id, "old.txt").exit_code == 0
    assert list_deliveries(timeframe="all") == []

    assert _publish_draft(delivery_id).exit_code == 0

    [stored] = list_deliveries(timeframe="all")
    assert stored.delivery_id == delivery_id
    assert stored.is_draft is False
    assert [operation.operation.value for operation in stored.operations] == ["upload", "upload", "delete"]


def test_extend_dry_run_does_not_change_the_draft(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = _new_draft("a.txt")

    assert _extend_draft(delivery_id, "b.txt", extra=("--dry-run",)).exit_code == 0

    assert len(_saved_draft(delivery_id).operations) == 1


def test_publish_dry_run_does_not_publish(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = _new_draft("a.txt")

    assert _publish_draft(delivery_id, "--dry-run").exit_code == 0

    assert list_deliveries(timeframe="all") == []
    assert _extend_draft(delivery_id, "b.txt").exit_code == 0


def test_publish_twice_fails(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = _new_draft("a.txt")
    assert _publish_draft(delivery_id).exit_code == 0

    assert _publish_draft(delivery_id).exit_code == 1
    assert len(list_deliveries(timeframe="all")) == 1


def test_extend_after_publish_fails(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = _new_draft("a.txt")
    assert _publish_draft(delivery_id).exit_code == 0

    assert _extend_draft(delivery_id, "b.txt").exit_code == 1


@pytest.mark.parametrize(
    "args",
    [
        ["create-draft", *IDS],
        ["create-draft", *IDS, "--file", "f.yaml", "--operation", "delete", "--source", "a.txt"],
        ["create-draft", *IDS, "--operation", "delete"],
        ["create-draft", *IDS, "--source", "a.txt"],
        ["create-draft", *IDS, "--operation", "delete", "--source", "a.txt", "--anchor", "x"],
        ["create-draft", *IDS, "--file", "f.yaml", "--anchor", "x"],
        ["create-draft", *IDS, "--operation", "nope", "--source", "a.txt"],
        ["create-draft", *IDS, "--file", "does-not-exist.yaml"],
        ["extend-draft", "--operation", "delete", "--source", "a.txt"],
        ["extend-draft", "--delivery-id", "x", "--file", "f.yaml", "--operation", "delete", "--source", "a.txt"],
        [*IDS],
    ],
    ids=[
        "no file, no operation",
        "file and operation",
        "operation without source",
        "source without operation",
        "anchor with delete",
        "anchor with file",
        "unknown operation",
        "missing delivery file",
        "extend without delivery-id",
        "extend with file and operation",
        "delivery with ids but no file",
    ],
)
def test_bad_arguments_exit(args):
    assert _run(*args).exit_code != 0


def test_upload_of_missing_local_file_exits(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    assert _create_draft("tests/resources/dataset1/nope.txt", operation="upload").exit_code == 1


@pytest.mark.parametrize(
    "file, operation, extra",
    [("a.txt", "delete", ()), (FILE_1, "upload", ("--anchor", "dataset1"))],
)
def test_same_file_twice_in_one_operation_exits(
    file, operation, extra, glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service
):
    assert _create_draft(file, file, operation=operation, extra=extra).exit_code == 1


@pytest.mark.xfail(strict=True, reason="Duplicates are only checked per operation, not across the draft.")
def test_same_file_in_draft_and_in_extend_exits(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = _new_draft("a.txt")

    assert _extend_draft(delivery_id, "a.txt").exit_code == 1


def test_empty_draft_is_accepted(tmp_path, glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    result = _run("create-draft", *IDS, "--file", _delivery_file(tmp_path, []))

    assert result.exit_code == 0


def test_extend_unknown_draft_exits(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    assert _extend_draft("does-not-exist", "a.txt").exit_code == 1


def test_publish_unknown_draft_exits(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    assert _publish_draft("does-not-exist").exit_code == 1


def test_python_create_extend_publish_draft(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = PythonDelivery(operations=[Delete(files=["a.txt"])]).create_draft(PRODUCT_ID, DATASET_ID).delivery_id
    assert list_deliveries(timeframe="all") == []

    PythonDelivery(operations=[Delete(files=["b.txt"])]).extend_draft(delivery_id)
    published = publish_draft(delivery_id)

    assert published.is_draft is False
    assert len(published.operations) == 2
    [stored] = list_deliveries(timeframe="all")
    assert stored.delivery_id == delivery_id


def test_python_empty_draft_can_be_extended_and_published(
    glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service
):
    delivery_id = PythonDelivery().create_draft(PRODUCT_ID, DATASET_ID).delivery_id
    PythonDelivery(operations=[Delete(files=["a.txt"])]).extend_draft(delivery_id)

    assert len(publish_draft(delivery_id).operations) == 1


def test_python_publish_draft_twice_raises(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    delivery_id = PythonDelivery(operations=[Delete(files=["a.txt"])]).create_draft(PRODUCT_ID, DATASET_ID).delivery_id
    publish_draft(delivery_id)

    with pytest.raises(DraftDeliveryNotFoundError):
        publish_draft(delivery_id)


def test_python_unknown_draft_raises(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    with pytest.raises(DraftDeliveryNotFoundError):
        PythonDelivery(operations=[Delete(files=["a.txt"])]).extend_draft("does-not-exist")
    with pytest.raises(DraftDeliveryNotFoundError):
        publish_draft("does-not-exist")


def test_size_limits_count_the_draft_files():
    limits = APILimits(max_number_of_files_per_delivery=3, max_delivery_size_gb=10, max_file_size_gb=1)
    draft = Delivery(
        delivery_id="id",
        pushing_entity_id="pe",
        product_id="p",
        dataset_id="d",
        operations=[
            UploadOperation(
                files=[
                    UploadFile(
                        key_suffix=f"f{i}.txt",
                        file_size_mb=1,
                        checksum="x",
                        upload_start_time=None,
                        upload_end_time=None,
                    )
                    for i in range(3)
                ]
            )
        ],
    )
    validate_delivery_sizes(limits, [], draft)  # at the limit: fine

    one_more = ToUploadOperation(files=[FileToUpload(file_size_mb=1, local_path="x.txt")], anchor=None)
    with pytest.raises(InvalidDeliverySizeError):
        validate_delivery_sizes(limits, [one_more], draft)
