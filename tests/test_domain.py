import pytest
from pydantic import ValidationError

from delivery_common.domain import (
    DeleteFile,
    DeliveryFile,
    InvalidDeliveryIdsError,
    PushingEntities,
    UploadFile,
)

PUSHING_ENTITIES = PushingEntities.model_validate(
    {
        "pushing-entities": [
            {
                "name": "ENTITY-A",
                "bucket": "bucket-a",
                "products": [{"name": "product-a", "datasets": ["dataset-a1", "dataset-a2"]}],
            },
            {
                "name": "ENTITY-B",
                "bucket": "bucket-b",
                "products": [{"name": "product-b", "datasets": ["dataset-b1"]}],
            },
        ]
    }
)

VALID_KEY_SUFFIXES = [
    "file.nc",
    "subfolder/file.nc",
    "a/b/c/file.txt",
    "dataset1/region/africa/file.nc",
]

FORBIDDEN_KEY_SUFFIXES = [
    "../file.nc",
    "subfolder/../file.nc",
    "a/../../file.nc",
    "subfolder//file.nc",
    "//file.nc",
    "s3://bucket/file.nc",
    "https://example.com/file.nc",
    "C:/file.nc",
]


@pytest.mark.parametrize("key_suffix", VALID_KEY_SUFFIXES)
def test_valid_key_suffix_is_accepted(key_suffix):
    assert DeliveryFile(key_suffix=key_suffix).key_suffix == key_suffix


@pytest.mark.parametrize("key_suffix", FORBIDDEN_KEY_SUFFIXES)
def test_forbidden_key_suffix_raises(key_suffix):
    with pytest.raises(ValidationError):
        DeliveryFile(key_suffix=key_suffix)


@pytest.mark.parametrize(
    ("key_suffix", "pattern"),
    [
        ("../file.nc", "../"),
        ("dir//file.nc", "//"),
        ("s3://bucket/file.nc", "//"),
        ("C:/file.nc", ":/"),
    ],
)
def test_error_message_mentions_forbidden_pattern(key_suffix, pattern):
    with pytest.raises(ValidationError) as exc_info:
        DeliveryFile(key_suffix=key_suffix)
    assert pattern in str(exc_info.value)


def test_absolute_path_raises_validation_error():
    with pytest.raises(ValidationError):
        DeliveryFile(key_suffix="/home/user/projects/file.nc")


def test_delete_file_enforces_key_suffix():
    with pytest.raises(ValidationError):
        DeleteFile(key_suffix="../file.nc")


@pytest.mark.parametrize(
    ("product_id", "dataset_id", "expected_name"),
    [
        ("product-a", "dataset-a1", "ENTITY-A"),
        ("product-a", "dataset-a2", "ENTITY-A"),
        ("product-b", "dataset-b1", "ENTITY-B"),
    ],
)
def test_resolve_returns_owning_pushing_entity(product_id, dataset_id, expected_name):
    assert PUSHING_ENTITIES.resolve(product_id, dataset_id).name == expected_name


@pytest.mark.parametrize(
    ("product_id", "dataset_id"),
    [
        ("product-a", "dataset-b1"),
        ("product-b", "dataset-a1"),
        ("unknown-product", "dataset-a1"),
        ("product-a", "unknown-dataset"),
    ],
)
def test_resolve_raises_when_pair_is_not_owned(product_id, dataset_id):
    with pytest.raises(InvalidDeliveryIdsError):
        PUSHING_ENTITIES.resolve(product_id, dataset_id)


def test_upload_file_enforces_key_suffix():
    with pytest.raises(ValidationError):
        UploadFile(
            key_suffix="../file.nc",
            file_size_mb=1,
            checksum="abc",
            upload_start_time=None,
            upload_end_time=None,
        )
