import pytest
import yaml

from delivery_common.domain import PushingEntities
from delivery_common.validation import validate_delivery_ids
from pusher import InvalidDeliveryIdsError, InvalidFilesError
from pusher.core_functions.core_functions import strip_to_anchor
from pusher.core_functions.delivery_validator import (
    validate_delete_files,
    validate_upload_files,
)
from pusher.s3_client import S3Client

_PUSHING_ENTITIES_YAML = yaml.dump(
    {
        "pushing-entities": [
            {
                "name": "TEST-ENTITY-FR",
                "bucket": "mdl-ing-test-entity-fr",
                "products": [
                    {
                        "name": "product1",
                        "datasets": ["dataset1", "dataset2"],
                    }
                ],
            }
        ]
    }
).encode()

_PUSHING_ENTIES = PushingEntities.from_stream(_PUSHING_ENTITIES_YAML)


@pytest.fixture(autouse=True)
def mock_get_file_stream(monkeypatch):
    monkeypatch.setattr(
        S3Client, "get_file_stream", lambda self, **kwargs: _PUSHING_ENTITIES_YAML
    )


def test_valid_delivery_ids():
    result = validate_delivery_ids(
        pushing_entity_id="TEST-ENTITY-FR",
        product_id="product1",
        dataset_id="dataset1",
        pushing_entities=_PUSHING_ENTIES,
    )
    assert result is None


def test_invalid_pushing_entity():
    with pytest.raises(InvalidDeliveryIdsError) as exc_info:
        validate_delivery_ids(
            pushing_entity_id="UNKNOWN-ENTITY",
            product_id="product1",
            dataset_id="dataset1",
            pushing_entities=_PUSHING_ENTIES,
        )
    assert "UNKNOWN-ENTITY" in str(exc_info.value)


def test_invalid_product_id():
    with pytest.raises(InvalidDeliveryIdsError) as exc_info:
        validate_delivery_ids(
            pushing_entity_id="TEST-ENTITY-FR",
            product_id="nonexistent-product",
            dataset_id="dataset1",
            pushing_entities=_PUSHING_ENTIES,
        )
    assert "nonexistent-product" in str(exc_info.value)


def test_invalid_dataset_id():
    with pytest.raises(InvalidDeliveryIdsError) as exc_info:
        validate_delivery_ids(
            pushing_entity_id="TEST-ENTITY-FR",
            product_id="product1",
            dataset_id="nonexistent-dataset",
            pushing_entities=_PUSHING_ENTIES,
        )
    assert "nonexistent-dataset" in str(exc_info.value)


DUPLICATED_FILES = ["file1.txt", "file2.txt", "file1.txt"]
MORE_DUPLICATED_FILES = ["file2.txt"] + [f"file1.txt" for i in range(10)]


@pytest.mark.parametrize("file_list", [DUPLICATED_FILES, MORE_DUPLICATED_FILES])
def test_duplicate_files_upload(file_list, caplog):
    with caplog.at_level("ERROR"):
        with pytest.raises(InvalidFilesError):
            validate_upload_files(file_list, "dataset1", "product1", anchor="does not matter here")
        assert caplog.text.count("Duplicate file path") == 1


@pytest.mark.parametrize("file_list", [DUPLICATED_FILES, MORE_DUPLICATED_FILES])
def test_duplicate_files_delete(file_list, caplog):
    with caplog.at_level("ERROR"):
        with pytest.raises(InvalidFilesError):
            validate_delete_files(file_list)
        assert caplog.text.count("Duplicate file path") == 1


@pytest.mark.parametrize(
    ("local_path", "anchor", "expected"),
    [
        (
            "/home/user/projects/my_dataset/region/africa/file.nc",
            "my_dataset",
            "region/africa/file.nc",
        ),
        ("my_dataset/file.nc", "my_dataset", "file.nc"),
        ("a/b/my_dataset", "my_dataset", "."),
        ("a/my_dataset/b/my_dataset/c.nc", "my_dataset", "b/my_dataset/c.nc"),
    ],
)
def test_strip_to_anchor(local_path, anchor, expected):
    assert strip_to_anchor(local_path, anchor) == expected


def test_missing_anchor_raises(caplog):
    with caplog.at_level("ERROR"):
        with pytest.raises(InvalidFilesError):
            validate_upload_files(
                ["tests/resources/dataset1/file1.txt"], "dataset1", "product1", anchor="does-not-exist"
            )
        assert "does-not-exist" in caplog.text

def test_no_anchor_and_dataset_id_in_path(caplog):
    with caplog.at_level("ERROR"):
        with pytest.raises(InvalidFilesError):
            validate_upload_files(
                ["tests/resources/dataset1/file1.txt"], "dataset1", "product1", anchor=None,
            )
        assert "No anchor specified and product_id (product1) or dataset_id (dataset1) found in local path" in caplog.text