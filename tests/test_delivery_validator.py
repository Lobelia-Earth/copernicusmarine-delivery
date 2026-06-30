from pusher.core_functions.delivery_validator import validate_delivery_ids
from pusher.core_functions.models import Product, PushingEntities, PushingEntity

_PUSHING_ENTITIES = PushingEntities(
    **{
        "pushing-entities": [
            PushingEntity(
                name="TEST-ENTITY-FR",
                products=[Product(name="product1", datasets=["dataset1", "dataset2"])],
            )
        ]
    }
)


def test_valid_delivery_ids():
    result = validate_delivery_ids(
        pushing_entity_id="TEST-ENTITY-FR",
        product_id="product1",
        dataset_id="dataset1",
        pushing_entities=_PUSHING_ENTITIES,
    )
    assert result is None


def test_invalid_pushing_entity():
    result = validate_delivery_ids(
        pushing_entity_id="UNKNOWN-ENTITY",
        product_id="product1",
        dataset_id="dataset1",
        pushing_entities=_PUSHING_ENTITIES,
    )
    assert result is not None
    assert "UNKNOWN-ENTITY" in result.reason


def test_invalid_product_id():
    result = validate_delivery_ids(
        pushing_entity_id="TEST-ENTITY-FR",
        product_id="nonexistent-product",
        dataset_id="dataset1",
        pushing_entities=_PUSHING_ENTITIES,
    )
    assert result is not None
    assert "nonexistent-product" in result.reason


def test_invalid_dataset_id():
    result = validate_delivery_ids(
        pushing_entity_id="TEST-ENTITY-FR",
        product_id="product1",
        dataset_id="nonexistent-dataset",
        pushing_entities=_PUSHING_ENTITIES,
    )
    assert result is not None
    assert "nonexistent-dataset" in result.reason


def test_get_file_called_when_no_pushing_entities(monkeypatch):
    import yaml

    from pusher.s3_client import S3Client

    fake_yaml = yaml.dump(
        {
            "pushing-entities": [
                {
                    "name": "TEST-ENTITY-FR",
                    "products": [{"name": "product1", "datasets": ["dataset1"]}],
                }
            ]
        }
    ).encode()
    monkeypatch.setattr(S3Client, "get_file", lambda self, **kwargs: fake_yaml)

    result = validate_delivery_ids(
        pushing_entity_id="TEST-ENTITY-FR",
        product_id="product1",
        dataset_id="dataset1",
    )
    assert result is None
