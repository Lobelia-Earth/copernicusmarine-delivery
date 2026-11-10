import pytest

from copernicusmarine_delivery import InvalidDeliverySizeError, list_deliveries, publish_draft
from copernicusmarine_delivery.core_functions.core_functions import delete
from copernicusmarine_delivery.core_functions.delivery import (
    DraftDeliveryMismatchError,
    DraftDeliveryNotFoundError,
)
from copernicusmarine_delivery.core_functions.delivery_validator import validate_delivery_sizes
from copernicusmarine_delivery.core_functions.domain import APILimits
from delivery_common.domain import Delivery, UploadFile, UploadOperation

PRODUCT_ID = "GLOBAL_ANALYSISFORECAST_BGC_001_028"
DATASET_ID = "cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m_202311"


def _delete(files: list[str], no_publish: bool, delivery_id: str | None = None, dry_run: bool = False):
    return delete(
        files=files,
        dataset_id=DATASET_ID,
        product_id=PRODUCT_ID,
        dry_run=dry_run,
        no_publish=no_publish,
        delivery_id=delivery_id,
    )


def test_no_publish_saves_draft_only(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    _, draft = _delete(["a.txt"], no_publish=True)

    assert list_deliveries(timeframe="all") == []
    # the draft exists: it can be continued
    _delete(["b.txt"], no_publish=True, delivery_id=draft.delivery_id)


def test_append_then_publish(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    _, draft = _delete(["a.txt"], no_publish=True)
    _, draft_2 = _delete(["b.txt"], no_publish=True, delivery_id=draft.delivery_id)
    assert draft_2.delivery_id == draft.delivery_id
    assert list_deliveries(timeframe="all") == []

    published = publish_draft(delivery_id=draft.delivery_id, product_id=PRODUCT_ID, dataset_id=DATASET_ID)

    assert len(published.operations) == 2
    [stored] = list_deliveries(timeframe="all")
    assert stored.delivery_id == draft.delivery_id
    assert len(stored.operations) == 2


def test_append_without_no_publish_publishes(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    _, draft = _delete(["a.txt"], no_publish=True)
    _delete(["b.txt"], no_publish=False, delivery_id=draft.delivery_id)

    [stored] = list_deliveries(timeframe="all")
    assert len(stored.operations) == 2
    # draft consumed by publishing
    with pytest.raises(DraftDeliveryNotFoundError):
        publish_draft(delivery_id=draft.delivery_id, product_id=PRODUCT_ID, dataset_id=DATASET_ID)


def test_publish_draft_dry_run_does_not_publish(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    _, draft = _delete(["a.txt"], no_publish=True)
    publish_draft(delivery_id=draft.delivery_id, product_id=PRODUCT_ID, dataset_id=DATASET_ID, dry_run=True)
    assert list_deliveries(timeframe="all") == []


def test_unknown_draft_raises(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    with pytest.raises(DraftDeliveryNotFoundError):
        _delete(["a.txt"], no_publish=True, delivery_id="does-not-exist")


def test_draft_of_other_dataset_raises(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    _, draft = _delete(["a.txt"], no_publish=True)
    with pytest.raises(DraftDeliveryMismatchError):
        publish_draft(delivery_id=draft.delivery_id, product_id=PRODUCT_ID, dataset_id="another-dataset")


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
                    UploadFile(key_suffix=f"f{i}.txt", file_size_mb=1, checksum="x", upload_start_time=None, upload_end_time=None)
                    for i in range(3)
                ]
            )
        ],
    )
    validate_delivery_sizes(limits, [], draft)  # at the limit: fine
    from copernicusmarine_delivery.core_functions.domain import FileToUpload, ToUploadOperation

    one_more = ToUploadOperation(files=[FileToUpload(file_size_mb=1, local_path="x.txt")], anchor=None)
    with pytest.raises(InvalidDeliverySizeError):
        validate_delivery_sizes(limits, [one_more], draft)
