import pytest

from copernicusmarine_delivery import Delete, DraftDelivery, InvalidDeliverySizeError, list_deliveries
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


def _delete(files: list[str], publish: bool, delivery_id: str | None = None, dry_run: bool = False):
    return delete(
        files=files,
        dataset_id=DATASET_ID,
        product_id=PRODUCT_ID,
        dry_run=dry_run,
        publish=publish,
    )


def test_no_publish_saves_draft_only(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    _, draft = _delete(["a.txt"], publish=False)

    assert list_deliveries(timeframe="all") == []
    # the draft exists: it can be continued
    _delete(["b.txt"], publish=False, delivery_id=draft.delivery_id)


def test_append_then_publish(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    _, draft = _delete(["a.txt"], publish=False)
    _, draft_2 = _delete(["b.txt"], publish=False, delivery_id=draft.delivery_id)
    assert draft_2.delivery_id == draft.delivery_id
    assert list_deliveries(timeframe="all") == []

    published = DraftDelivery(delivery_id=draft.delivery_id).publish()

    assert len(published.operations) == 2
    [stored] = list_deliveries(timeframe="all")
    assert stored.delivery_id == draft.delivery_id
    assert len(stored.operations) == 2


def test_append_without_no_publish_publishes(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    _, draft = _delete(["a.txt"], publish=False)
    _delete(["b.txt"], publish=True, delivery_id=draft.delivery_id)

    [stored] = list_deliveries(timeframe="all")
    assert len(stored.operations) == 2
    # draft consumed by publishing
    with pytest.raises(DraftDeliveryNotFoundError):
        DraftDelivery(delivery_id=draft.delivery_id)


def test_publish_dry_run_does_not_publish(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    _, draft = _delete(["a.txt"], publish=False)
    DraftDelivery(delivery_id=draft.delivery_id).publish(dry_run=True)
    assert list_deliveries(timeframe="all") == []


def test_unknown_draft_raises(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    with pytest.raises(DraftDeliveryNotFoundError):
        _delete(["a.txt"], publish=False, delivery_id="does-not-exist")


def test_draft_of_other_dataset_raises(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    _, draft = _delete(["a.txt"], publish=False)
    wrong_draft = DraftDelivery(product_id=PRODUCT_ID, dataset_id="another-dataset", delivery_id=draft.delivery_id)
    with pytest.raises(DraftDeliveryMismatchError):
        wrong_draft.publish()


def test_draft_delivery_create_extend_publish(glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service):
    draft = DraftDelivery(product_id=PRODUCT_ID, dataset_id=DATASET_ID)
    draft.add(Delete(files=["a.txt"]))
    response = draft.create()
    assert draft.delivery_id == response.delivery_id
    assert draft.operations == []
    assert list_deliveries(timeframe="all") == []

    draft.add(Delete(files=["b.txt"]))
    draft.extend()
    published = draft.publish()

    assert len(published.operations) == 2
    [stored] = list_deliveries(timeframe="all")
    assert stored.delivery_id == draft.delivery_id


def test_draft_delivery_continued_from_delivery_id(
    glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service
):
    first = DraftDelivery(product_id=PRODUCT_ID, dataset_id=DATASET_ID)
    first.add(Delete(files=["a.txt"]))
    first.create()

    second = DraftDelivery(delivery_id=first.delivery_id)
    assert (second.product_id, second.dataset_id) == (PRODUCT_ID, DATASET_ID)
    second.add(Delete(files=["b.txt"]))
    second.extend()

    assert len(second.publish().operations) == 2


def test_draft_delivery_publish_with_unsaved_operations_raises(
    glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service
):
    draft = DraftDelivery(product_id=PRODUCT_ID, dataset_id=DATASET_ID)
    draft.add(Delete(files=["a.txt"]))
    draft.create()
    draft.add(Delete(files=["b.txt"]))
    with pytest.raises(ValueError, match="extend"):
        draft.publish()


def test_draft_delivery_extend_and_publish_need_a_draft(
    glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service
):
    draft = DraftDelivery(product_id=PRODUCT_ID, dataset_id=DATASET_ID)
    draft.add(Delete(files=["a.txt"]))
    with pytest.raises(ValueError, match="No draft to extend"):
        draft.extend()
    with pytest.raises(ValueError, match="No draft to publish"):
        draft.publish()


def test_draft_delivery_needs_ids_or_delivery_id():
    with pytest.raises(ValueError, match="required"):
        DraftDelivery()


def test_draft_delivery_unknown_delivery_id_raises_at_instantiation(
    glo_mercator_bucket, skip_delivery_ids_validation, ingestion_service
):
    with pytest.raises(DraftDeliveryNotFoundError):
        DraftDelivery(delivery_id="does-not-exist")


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
    from copernicusmarine_delivery.core_functions.domain import FileToUpload, ToUploadOperation

    one_more = ToUploadOperation(files=[FileToUpload(file_size_mb=1, local_path="x.txt")], anchor=None)
    with pytest.raises(InvalidDeliverySizeError):
        validate_delivery_sizes(limits, [one_more], draft)
