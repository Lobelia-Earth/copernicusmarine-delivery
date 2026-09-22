"""Copernicus Marine Delivery package."""

# we have some naming problems with Delivery
# being the model and the python interface class.
# TODO: solve this when we have a name for the package.
from copernicusmarine_delivery.core_functions.domain import (
    InvalidFilesError,
    NoIngestionBucketError,
    NoSuccessfulUploadsError,
)
from copernicusmarine_delivery.python_interface import (
    Delete,
    Delivery,
    Upload,
    delivery_status,
    list_deliveries,
)
from copernicusmarine_delivery.versioner import __version__
from delivery_common.domain import Delivery as DeliveryModel
from delivery_common.domain import InvalidDeliveryIdsError

__all__ = [
    "Delete",
    "Delivery",
    "Upload",
    "delivery_status",
    "list_deliveries",
    "DeliveryModel",
    "InvalidDeliveryIdsError",
    "NoIngestionBucketError",
    "NoSuccessfulUploadsError",
    "__version__",
    "InvalidFilesError",
]
