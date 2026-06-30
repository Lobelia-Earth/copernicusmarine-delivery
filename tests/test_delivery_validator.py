import pytest
import yaml

from pusher.core_functions.delivery_validator import validate_delivery_ids
from pusher.s3_client import S3Client

_PUSHING_ENTITIES_YAML = yaml.dump(
    {
        "pushing-entities": [
            {
                "name": "TEST-ENTITY-FR",
                "products": [
                    {"name": "product1", "datasets": ["dataset1", "dataset2"]}
                ],
            }
        ]
    }
).encode()


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
    )
    assert result is None


def test_invalid_pushing_entity():
    result = validate_delivery_ids(
        pushing_entity_id="UNKNOWN-ENTITY",
        product_id="product1",
        dataset_id="dataset1",
    )
    assert result is not None
    assert "UNKNOWN-ENTITY" in result.reason


def test_invalid_product_id():
    result = validate_delivery_ids(
        pushing_entity_id="TEST-ENTITY-FR",
        product_id="nonexistent-product",
        dataset_id="dataset1",
    )
    assert result is not None
    assert "nonexistent-product" in result.reason


def test_invalid_dataset_id():
    result = validate_delivery_ids(
        pushing_entity_id="TEST-ENTITY-FR",
        product_id="product1",
        dataset_id="nonexistent-dataset",
    )
    assert result is not None
    assert "nonexistent-dataset" in result.reason
