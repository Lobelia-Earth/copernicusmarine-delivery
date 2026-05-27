import random

from freezegun import freeze_time

from pusher import upload

random.seed(42)  # Set a fixed seed for reproducibility in tests

MOCK_FILES = ["tests/resources/file1.txt", "tests/resources/file2.txt"]


# TODO: work on the test files to be more representative
# of the actual use case.
@freeze_time("2012-01-14 12:00:01")
def test_manifest(snapshot, tmp_path):

    manifest = upload(
        source=MOCK_FILES,
        dataset_id="dataset1",
        product_id="product1",
    )
    assert manifest.model_dump() == snapshot
