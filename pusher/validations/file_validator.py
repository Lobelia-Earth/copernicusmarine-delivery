from pathlib import Path

import netCDF4
import numpy as np
from cloudpathlib import S3Path

from pusher.core_functions.models import InvalidFile, ValidateResult

SUPPORTED_FILE_EXTENTIONS = {".nc"}

# CF attributes that must be representable by the variable's dtype
_CF_RANGE_ATTRS = ("valid_min", "valid_max", "actual_min", "actual_max", "valid_range")


## The below are "file system" generic checks
def file_exists(file_path: Path | S3Path) -> bool:
    return file_path.exists()


def file_not_empty(file_path: Path | S3Path) -> bool:
    return file_path.stat().st_size > 0


def file_type_supported(file_path: Path | S3Path) -> bool:
    return file_path.suffix in SUPPORTED_FILE_EXTENTIONS


## NetCDF / CF Compliance tests


def _open_nc(file_path: Path | S3Path) -> netCDF4.Dataset:
    if isinstance(file_path, S3Path):
        return netCDF4.Dataset("in_memory", memory=file_path.read_bytes())
    return netCDF4.Dataset(str(file_path))


def check_nc_dtype_attribute_overflow(file_path: Path | S3Path) -> str | None:
    """Return error string if any CF range attribute value overflows its variable's dtype.
    e.g. valid_min=-80000 on an int16 variable is not CF compliant and causes
    numpy>=2.0 to raise on cast.
    """
    with _open_nc(file_path) as ds:
        for var_name, var in ds.variables.items():
            if not np.issubdtype(var.dtype, np.integer):
                continue
            info = np.iinfo(var.dtype)
            for attr in _CF_RANGE_ATTRS:
                if attr not in var.ncattrs():
                    continue
                for v in np.atleast_1d(var.getncattr(attr)):
                    if float(v) < info.min or float(v) > info.max:
                        return (
                            f"Variable '{var_name}': attribute '{attr}={v}' overflows "
                            f"dtype {var.dtype} (valid range [{info.min}, {info.max}]). "
                            "Fix: align the attribute type with the variable dtype."
                        )
    return None


def validate_upload_files(files: list[Path | S3Path]) -> ValidateResult:
    valid_files = []
    invalid_files = []
    for file in files:
        if not file_exists(file):
            invalid_files.append(
                InvalidFile(path=file, reason="File path does not exist.")
            )
            continue
        if not file_not_empty(file):
            invalid_files.append(InvalidFile(path=file, reason="File is empty."))
            continue
        if not file_type_supported(file):
            invalid_files.append(
                InvalidFile(
                    path=file,
                    reason=f"File extension not supported. Supported extensions are: {SUPPORTED_FILE_EXTENTIONS}",
                )
            )
            continue
        if file.suffix == ".nc":
            if overflow_error := check_nc_dtype_attribute_overflow(file):
                invalid_files.append(InvalidFile(path=file, reason=overflow_error))
                continue
        valid_files.append(file)
    return ValidateResult(files_valid=valid_files, files_invalid=invalid_files)
