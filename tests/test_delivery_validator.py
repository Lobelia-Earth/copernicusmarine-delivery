import pytest
import yaml

from delivery_common.domain import PushingEntities
from delivery_common.validation import validate_delivery_ids
from pusher.core_functions.delivery_validator import duplicate_files
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
    result = validate_delivery_ids(
        pushing_entity_id="UNKNOWN-ENTITY",
        product_id="product1",
        dataset_id="dataset1",
        pushing_entities=_PUSHING_ENTIES,
    )
    assert result is not None
    assert "UNKNOWN-ENTITY" in result.reason


def test_invalid_product_id():
    result = validate_delivery_ids(
        pushing_entity_id="TEST-ENTITY-FR",
        product_id="nonexistent-product",
        dataset_id="dataset1",
        pushing_entities=_PUSHING_ENTIES,
    )
    assert result is not None
    assert "nonexistent-product" in result.reason


def test_invalid_dataset_id():
    result = validate_delivery_ids(
        pushing_entity_id="TEST-ENTITY-FR",
        product_id="product1",
        dataset_id="nonexistent-dataset",
        pushing_entities=_PUSHING_ENTIES,
    )
    assert result is not None
    assert "nonexistent-dataset" in result.reason


def test_duplicate_files():
    result = duplicate_files(["test.txt", "test.txt"])
    assert result is not None
    assert result == ["test.txt"]

    result = duplicate_files(["test.txt", "test.txt", "test1.txt", "test2.txt"])
    assert result is not None
    assert result == ["test.txt"]
