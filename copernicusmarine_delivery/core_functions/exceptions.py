class NoSuchBucketException(Exception):
    """Raised when the expected ingestion bucket for the given Pushing Entity does not exist."""


class ConnectionRefusedException(Exception):
    """Raised when trying the connection to the ingestion bucket for the given Pushing Entity is refused."""


class DraftDeliveryNotFoundError(Exception):
    """Raised when trying to append or push a draft delivery and it could not be found."""


class DraftDeliveryMismatchError(Exception):
    """Raised when the given ids (product_id, dataset_id) do not match the draft delivery to append to or publish."""
