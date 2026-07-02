import random

from freezegun import freeze_time

from pusher.core_functions.core_functions import delivery

mock_files = ["tests/resources/file1.txt", "tests/resources/file2.txt"]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"


@freeze_time("2012-01-14 12:00:01")
def test_delivery_python_interface(
    snapshot, glo_mercator_bucket, set_env, skip_delivery_ids_validation
):
    random.seed(42)
    operations = [
        ("delete", mock_files),
        ("upload", mock_files),
    ]

    response, manifest = delivery(
        operations=operations,  # type: ignore
        pushing_entity_id=PUSHING_ENTITY_ID,
        dataset_id="dataset1",
        product_id="product1",
    )
    assert response.model_dump_json(indent=2) == snapshot
    assert manifest is not None
    assert manifest.model_dump_json(indent=2) == snapshot


@freeze_time("2012-01-14 12:00:01")
def test_delivery_early_exit_with_validation_error(
    snapshot, glo_mercator_bucket, set_env, skip_delivery_ids_validation
):
    random.seed(42)
    operations = [("delete", mock_files), ("upload", mock_files + ["extra_file.txt"])]

    response, manifest = delivery(
        operations=operations,  # type: ignore
        pushing_entity_id=PUSHING_ENTITY_ID,
        dataset_id="dataset1",
        product_id="product1",
    )
    assert response.model_dump_json(indent=2) == snapshot
    assert manifest is None
