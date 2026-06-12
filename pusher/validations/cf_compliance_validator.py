"""Validate a netCDF (4?) header and its variables for CF Compliance.
Taken mostly from here: https://cfconventions.org/cf-conventions/cf-conventions.html
TODO: Do all errors mean it completely fails? How strict should this be?"""

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

CFDtype = {
    "string",
    "char",
    "byte",
    "ubyte",
    "short",
    "ushort",
    "int",
    "uint",
    "int64",
    "uint64",
    "float",
    "real",
    "double",
}
_INTEGER_DTYPES = {"byte", "ubyte", "short", "ushort", "int", "uint", "int64", "uint64"}
_NUMERIC_DTYPES = _INTEGER_DTYPES | {"float", "real", "double"}
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_TIME_UNITS_RE = re.compile(r"^\S+\s+since\s+\S+")  # "days since1990-01-01"


@dataclass
class CFVariable:
    name: str
    dtype: str
    dimensions: list[str] = field(default_factory=list)
    units: str | None = None
    long_name: str | None = None
    standard_name: str | None = None
    fill_value: float | int | str | None = None  # _FillValue
    valid_min: float | None = None
    valid_max: float | None = None
    valid_range: list[float] | None = None
    actual_range: list[float] | None = None
    missing_value: Any = None
    scale_factor: float | None = None
    add_offset: float | None = None
    bounds: str | None = None
    positive: Literal["up", "down"] | None = None
    axis: Literal["X", "Y", "Z", "T"] | None = None
    quantization: str | None = None
    quantization_nsb: int | None = None
    quantization_nsd: int | None = None
    aggregated_dimensions: str | None = None
    aggregated_data: str | None = None
    coordinates: str | None = None
    formula_terms: str | None = None
    cell_measures: str | None = None
    extra_attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def is_coordinate_variable(self) -> bool:
        return len(self.dimensions) == 1 and self.dimensions[0] == self.name


@dataclass
class CFHeader:
    conventions: str  # Conventions global attr
    dimensions: dict[str, int | None] = field(
        default_factory=dict
    )  # name -> size (None = unlimited)
    variables: list[CFVariable] = field(default_factory=list)
    title: str | None = None
    institution: str | None = None
    source: str | None = None
    history: str | None = None
    references: str | None = None
    comment: str | None = None
    external_variables: str | None = None
    extra_global_attributes: dict[str, Any] = field(default_factory=dict)


############################
# Variable-level Validations
# ##########################


def validate_name_convention(variable: CFVariable) -> str | None:
    if not _NAME_RE.match(variable.name):
        return f"'{variable.name}': name must start with letter, use only ASCII letters/digits/underscores"


def validate_dtype(variable: CFVariable) -> str | None:
    if variable.dtype not in CFDtype:
        return f"'{variable.name}': unsupported dtype '{variable.dtype}'"


def validate_unique_dimensions(variable: CFVariable) -> str | None:
    if len(variable.dimensions) != len(set(variable.dimensions)):
        return f"'{variable.name}': duplicate dimension names in {variable.dimensions}"


def validate_fill_value_outside_valid_range(variable: CFVariable) -> str | None:
    if variable.fill_value is not None and variable.valid_range is not None:
        fill_value = float(variable.fill_value)
        low, high = variable.valid_range
        if low <= fill_value <= high:
            return f"'{variable.name}': _FillValue ({fill_value}) should be outside valid_range [{low}, {high}]"


def validate_actual_range(variable: CFVariable) -> list[str]:
    errors = []
    if variable.actual_range is not None:
        if len(variable.actual_range) != 2:
            errors.append(f"'{variable.name}': actual_range must be two-element vector")
        elif variable.valid_range is not None:
            ar_min, ar_max = variable.actual_range
            vr_min, vr_max = variable.valid_range
            if not (vr_min <= ar_min and ar_max <= vr_max):
                errors.append(
                    f"'{variable.name}': actual_range [{ar_min}, {ar_max}] not within valid_range [{vr_min}, {vr_max}]"
                )
    return errors


def validate_quantization(variable: CFVariable) -> list[str]:
    errors = []
    if variable.quantization is not None:
        if variable.dtype in _INTEGER_DTYPES:
            errors.append(
                f"'{variable.name}': quantization not allowed on integer dtype '{variable.dtype}'"
            )
        if variable.quantization_nsb is None and variable.quantization_nsd is None:
            errors.append(
                f"'{variable.name}': quantized variable requires quantization_nsb or quantization_nsd"
            )
    return errors


def validate_aggregation(variable: CFVariable) -> list[str]:
    errors = []
    is_aggregation = (
        variable.aggregated_dimensions is not None
        or variable.aggregated_data is not None
    )
    if is_aggregation:
        if variable.dimensions:
            errors.append(
                f"'{variable.name}': aggregation variable must be scalar (zero dimensions)"
            )
        if variable.aggregated_dimensions is None:
            errors.append(
                f"'{variable.name}': aggregation variable requires aggregated_dimensions"
            )
        if variable.aggregated_data is None:
            errors.append(
                f"'{variable.name}': aggregation variable requires aggregated_data"
            )
    return errors


############################
# Header-level Validations
# ##########################


def validate_conventions(header: CFHeader) -> str | None:
    if "CF-" not in header.conventions:
        return f"Conventions '{header.conventions}' must reference a CF version (e.g. 'CF-1.11')"


def validate_coordinate_variables(header: CFHeader) -> list[str]:
    errors = []
    for variable in header.variables:
        if variable.is_coordinate_variable and variable.dtype not in _NUMERIC_DTYPES:
            errors.append(
                f"Coordinate variable '{variable.name}' must be numeric, got '{variable.dtype}'"
            )
    return errors


def validate_time_coordinate_units(header: CFHeader) -> list[str]:
    # FIXME: variable.axis and standard names can be standardized instead of hardcoded strings?
    errors = []
    for variable in header.variables:
        is_time = variable.axis == "T" or (
            variable.standard_name and "time" in variable.standard_name
        )
        if is_time:
            if variable.units is None:
                errors.append(
                    f"Time variable '{variable.name}' requires units attribute"
                )
            elif not _TIME_UNITS_RE.match(variable.units):
                errors.append(
                    f"Time variable '{variable.name}': units '{variable.units}' must follow 'X since YYYY-MM-DD'"
                )
    return errors


def validate_vertical_coordinate(header: CFHeader) -> list[str]:
    errors = []
    for variable in header.variables:
        if variable.axis == "Z" and variable.is_coordinate_variable:
            if variable.units is None and variable.positive not in ("up", "down"):
                errors.append(
                    f"Vertical coordinate '{variable.name}' requires units or positive='up'/'down'"
                )
    return errors


def validate_bounds_variables(header: CFHeader) -> list[str]:
    errors = []
    variable_map = {v.name: v for v in header.variables}
    for variable in header.variables:
        if variable.bounds:
            bounds_variable = variable_map.get(variable.bounds)
            if bounds_variable is None:
                errors.append(
                    f"'{variable.name}': bounds variable '{variable.bounds}' not found"
                )
                continue
            expected_ndim = len(variable.dimensions) + 1
            if len(bounds_variable.dimensions) != expected_ndim:
                errors.append(
                    f"Bounds variable '{variable.bounds}' must have {expected_ndim} dims, has {len(bounds_variable.dimensions)}"
                )
            elif (
                bounds_variable.dimensions[: len(variable.dimensions)]
                != variable.dimensions
            ):
                errors.append(
                    f"Bounds variable '{variable.bounds}' leading dims must match '{variable.name}' dims"
                )
    return errors


def validate_quantization_not_on_protected(header: CFHeader) -> list[str]:
    errors = []
    protected: set[str] = set()
    for variable in header.variables:
        if variable.is_coordinate_variable:
            protected.add(variable.name)
        for ref_attr in (
            variable.coordinates,
            variable.formula_terms,
            variable.cell_measures,
        ):
            if ref_attr:
                protected.update(t for t in ref_attr.split() if _NAME_RE.match(t))
    for variable in header.variables:
        if variable.quantization is not None and variable.name in protected:
            errors.append(
                f"'{variable.name}': quantization not allowed on coordinate or referenced variable"
            )
    return errors


header_level_validations: list[Callable] = [
    validate_conventions,
    validate_coordinate_variables,
    validate_time_coordinate_units,
    validate_vertical_coordinate,
    validate_bounds_variables,
    validate_quantization_not_on_protected,
]

variable_level_validations: list[Callable] = [
    validate_name_convention,
    validate_dtype,
    validate_unique_dimensions,
    validate_fill_value_outside_valid_range,
    validate_actual_range,
    validate_quantization,
    validate_aggregation,
]
