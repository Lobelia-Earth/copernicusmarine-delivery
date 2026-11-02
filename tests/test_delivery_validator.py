from pathlib import Path

import pytest
import yaml

from copernicusmarine_delivery import InvalidDeliveryIdsError, InvalidFilesError
from copernicusmarine_delivery.core_functions.delivery_validator import (
    validate_delete_files,
    validate_delivery_sizes,
    validate_upload_files,
)
from copernicusmarine_delivery.core_functions.domain import (
    APILimits,
    FileToUpload,
    InvalidDeliverySizeError,
    ToUploadOperation,
)
from copernicusmarine_delivery.core_functions.utils import (
    local_path_to_key_suffix,
)
from copernicusmarine_delivery.s3_client import S3Client
from delivery_common.domain import PushingEntities
from delivery_common.validation import validate_delivery_ids

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

_PUSHING_ENTITY = PushingEntities.from_stream(_PUSHING_ENTITIES_YAML).pushing_entities[0]


@pytest.fixture(autouse=True)
def mock_get_file_stream(monkeypatch):
    monkeypatch.setattr(S3Client, "get_file_stream", lambda self, **kwargs: _PUSHING_ENTITIES_YAML)


def test_valid_delivery_ids():
    result = validate_delivery_ids(
        pushing_entity_id="TEST-ENTITY-FR",
        product_id="product1",
        dataset_id="dataset1",
        pushing_entity=_PUSHING_ENTITY,
    )
    assert result is None


def test_invalid_product_id():
    with pytest.raises(InvalidDeliveryIdsError) as exc_info:
        validate_delivery_ids(
            pushing_entity_id="TEST-ENTITY-FR",
            product_id="nonexistent-product",
            dataset_id="dataset1",
            pushing_entity=_PUSHING_ENTITY,
        )
    assert "nonexistent-product" in str(exc_info.value)


def test_invalid_dataset_id():
    with pytest.raises(InvalidDeliveryIdsError) as exc_info:
        validate_delivery_ids(
            pushing_entity_id="TEST-ENTITY-FR",
            product_id="product1",
            dataset_id="nonexistent-dataset",
            pushing_entity=_PUSHING_ENTITY,
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
    assert local_path_to_key_suffix(local_path, anchor) == expected


def test_missing_anchor_raises(caplog):
    with caplog.at_level("ERROR"):
        with pytest.raises(InvalidFilesError):
            validate_upload_files(
                ["tests/resources/dataset1/file1.txt"],
                "dataset1",
                "product1",
                anchor="does-not-exist",
            )
        assert "does-not-exist" in caplog.text


def test_no_anchor_and_dataset_id_in_path_is_rejected(caplog):
    with caplog.at_level("ERROR"):
        with pytest.raises(InvalidFilesError):
            validate_upload_files(
                ["tests/resources/dataset1/file1.txt"],
                "dataset1",
                "product1",
                anchor=None,
            )
        assert (
            "No anchor specified and product_id (product1) or dataset_id (dataset1) found in local path" in caplog.text
        )


def test_no_anchor_and_absolute_path_is_rejected(caplog):
    path = Path("tests/resources/file1.txt").absolute()
    with caplog.at_level("ERROR"):
        with pytest.raises(InvalidFilesError):
            validate_upload_files(
                [str(path)],
                "dataset1",
                "product1",
                anchor=None,
            )
        assert "Absolute paths are only allowed if an anchor is given" in caplog.text


_LIMITS = APILimits(max_number_of_files_per_delivery=3, max_delivery_size_gb=1, max_file_size_gb=0.5)


def _operation(list_of_file_sizes_mb: list[int]) -> ToUploadOperation:
    return ToUploadOperation(
        files=[
            FileToUpload(file_size_mb=size, local_path=f"file{i}.nc") for i, size in enumerate(list_of_file_sizes_mb)
        ],
        anchor=None,
    )


def test_validate_delivery_sizes_within_limits():
    validate_delivery_sizes(_LIMITS, [_operation([100, 100, 100])])


def test_validate_delivery_sizes_at_limits_is_accepted():
    # 2 * 512 MB = 1 GB (total limit), each file == max file size (0.5 GB)
    validate_delivery_sizes(_LIMITS, [_operation([512, 512])])


def test_validate_delivery_sizes_no_operations():
    validate_delivery_sizes(_LIMITS, [])


def test_validate_delivery_sizes_too_many_files_across_operations():
    with pytest.raises(InvalidDeliverySizeError, match="Maximum number of files exceeded"):
        validate_delivery_sizes(_LIMITS, [_operation([1, 1]), _operation([1, 1])])


def test_validate_delivery_sizes_total_size_exceeded():
    # each file is under the file limit (512 MB), but the total is 1.5 GB > 1 GB
    with pytest.raises(InvalidDeliverySizeError, match="Maximum delivery size exceeded"):
        validate_delivery_sizes(_LIMITS, [_operation([500, 500, 500])])


def test_validate_delivery_sizes_single_file_too_big():
    limits = APILimits(max_number_of_files_per_delivery=3, max_delivery_size_gb=10, max_file_size_gb=0.5)
    with pytest.raises(InvalidDeliverySizeError, match="Maximum file size exceeded") as exc_info:
        validate_delivery_sizes(limits, [_operation([10, 513])])
    assert "file1.nc" in str(exc_info.value)
    assert "file0.nc" not in str(exc_info.value)
