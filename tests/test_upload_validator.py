from pathlib import Path

import netCDF4
import numpy as np
import pytest

from pusher.validations.file_validator import (
    check_nc_dtype_attribute_overflow,
    validate_upload_files,
)


@pytest.fixture()
def nc_file_overflow_valid_min(tmp_path: Path) -> Path:
    """int16 variable with valid_min=-80000, overflows int16 range [-32768, 32767]."""
    path = tmp_path / "overflow_valid_min.nc"
    with netCDF4.Dataset(str(path), "w") as ds:
        ds.createDimension("x", 10)
        v = ds.createVariable("temp", np.int16, ("x",))
        v.valid_min = np.int32(-80000)
    return path


@pytest.fixture()
def nc_file_overflow_valid_max(tmp_path: Path) -> Path:
    """int16 variable with valid_max=80000, overflows int16 range [-32768, 32767]."""
    path = tmp_path / "overflow_valid_max.nc"
    with netCDF4.Dataset(str(path), "w") as ds:
        ds.createDimension("x", 10)
        v = ds.createVariable("temp", np.int16, ("x",))
        v.valid_max = np.int32(80000)
    return path


@pytest.fixture()
def nc_file_overflow_valid_range(tmp_path: Path) -> Path:
    """int16 variable with valid_range containing an out-of-range value."""
    path = tmp_path / "overflow_valid_range.nc"
    with netCDF4.Dataset(str(path), "w") as ds:
        ds.createDimension("x", 10)
        v = ds.createVariable("temp", np.int16, ("x",))
        v.valid_range = np.array([-80000, 80000], dtype=np.int32)
    return path


@pytest.fixture()
def nc_file_compliant(tmp_path: Path) -> Path:
    """int16 variable with attributes within range."""
    path = tmp_path / "compliant.nc"
    with netCDF4.Dataset(str(path), "w") as ds:
        ds.createDimension("x", 10)
        v = ds.createVariable("temp", np.int16, ("x",))
        v.valid_min = np.int16(-30000)
        v.valid_max = np.int16(30000)
    return path


@pytest.fixture()
def nc_file_float_variable(tmp_path: Path) -> Path:
    """float32 variable — overflow check should be skipped."""
    path = tmp_path / "float_var.nc"
    with netCDF4.Dataset(str(path), "w") as ds:
        ds.createDimension("x", 10)
        v = ds.createVariable("temp", np.float32, ("x",))
        v.valid_min = np.float32(-1e10)
    return path


class TestCheckNcDtypeAttributeOverflow:
    def test_overflow_valid_min(self, nc_file_overflow_valid_min: Path):
        result = check_nc_dtype_attribute_overflow(nc_file_overflow_valid_min)
        assert result is not None
        assert "valid_min" in result
        assert "-80000" in result
        assert "int16" in result

    def test_overflow_valid_max(self, nc_file_overflow_valid_max: Path):
        result = check_nc_dtype_attribute_overflow(nc_file_overflow_valid_max)
        assert result is not None
        assert "valid_max" in result
        assert "80000" in result

    def test_overflow_valid_range(self, nc_file_overflow_valid_range: Path):
        result = check_nc_dtype_attribute_overflow(nc_file_overflow_valid_range)
        assert result is not None
        assert "valid_range" in result

    def test_compliant_file(self, nc_file_compliant: Path):
        assert check_nc_dtype_attribute_overflow(nc_file_compliant) is None

    def test_float_variable_skipped(self, nc_file_float_variable: Path):
        assert check_nc_dtype_attribute_overflow(nc_file_float_variable) is None


class TestValidateUploadFilesNcCompliance:
    def test_overflow_file_lands_in_invalid(self, nc_file_overflow_valid_min: Path):
        result = validate_upload_files([nc_file_overflow_valid_min])
        assert len(result.files_invalid) == 1
        assert len(result.files_valid) == 0
        assert "valid_min" in result.files_invalid[0].reason

    def test_compliant_file_is_valid(self, nc_file_compliant: Path):
        result = validate_upload_files([nc_file_compliant])
        assert len(result.files_valid) == 1
        assert len(result.files_invalid) == 0
