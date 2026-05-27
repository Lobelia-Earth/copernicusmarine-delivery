"""Python API for the pusher package."""

from pathlib import Path

from pusher.core_functions import upload as _upload


def upload(source: Path, destination: str) -> None:
    """Upload ``source`` to ``destination``."""
    _upload(source=source, destination=destination)
