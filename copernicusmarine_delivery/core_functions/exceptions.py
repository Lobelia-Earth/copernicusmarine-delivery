class NoSuchBucketException(Exception):
    """Raised when the expected ingestion bucket for the given Pushing Entity does not exist."""


class ConnectionRefusedException(Exception):
    """Raised when trying the connection to the ingestion bucket for the given Pushing Entity is refused."""
