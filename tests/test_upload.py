import random

from freezegun import freeze_time

from pusher import upload

MOCK_FILES = ["tests/resources/file1.txt", "tests/resources/file2.txt"]
PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"


# TODO: work on the test files to be more representative
# of the actual use case.
@freeze_time("2012-01-14 12:00:01")
def test_manifest(snapshot, tmp_path):
    random.seed(42)

    response = upload(
        pushing_entity_id=PUSHING_ENTITY_ID,
        source=MOCK_FILES,
        dataset_id="dataset1",
        product_id="product1",
    )
    result = response.model_dump()
    for op in result.get("operations", []):
        op["files"] = sorted(op["files"], key=lambda f: f["s3_path"])
    assert result == snapshot
