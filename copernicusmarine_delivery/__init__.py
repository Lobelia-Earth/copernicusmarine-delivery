"""Copernicus Marine Delivery package."""

from copernicusmarine_delivery.auth import AuthenticationError
from copernicusmarine_delivery.core_functions.delivery import TimeframeLiteral
from copernicusmarine_delivery.core_functions.domain import (
    ErrorFile,
    InvalidFilesError,
    NoIngestionBucketError,
    NoSuccessfulUploadsError,
    ResponseDelete,
    ResponseDelivery,
    ResponseUpload,
    S3KeySuffix,
)
from copernicusmarine_delivery.python_interface import (
    Delete,
    Delivery,
    Upload,
    delivery_status,
    list_deliveries,
)
from copernicusmarine_delivery.versioner import __version__
from delivery_common.domain import DeleteFile, DeliveryStatus, InvalidDeliveryIdsError

# we have some naming problems with Delivery
# being the model and the python interface class.
# TODO: solve this when we have a name for the package.
from delivery_common.domain import Delivery as DeliveryModel

__all__ = [
    # Operations
    "Delete",
    "Delivery",
    "Upload",
    "delivery_status",
    "list_deliveries",
    # Responses and the types they use
    "ResponseDelete",
    "ResponseDelivery",
    "ResponseUpload",
    "DeliveryModel",
    "DeliveryStatus",
    "DeleteFile",
    "ErrorFile",
    "S3KeySuffix",
    "TimeframeLiteral",
    # Exceptions
    "AuthenticationError",
    "InvalidDeliveryIdsError",
    "InvalidFilesError",
    "NoIngestionBucketError",
    "NoSuccessfulUploadsError",
    "__version__",
]
