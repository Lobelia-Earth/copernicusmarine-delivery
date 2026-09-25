import os
import sys


def required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(
            f"Error: {name} environment variable is not set. "
            f"Set it before running this command."
        )
    return value


ALLOW_HTTP = bool(os.getenv("ALLOW_HTTP"))
INGESTION_SERVICE_URL = os.getenv(
    "INGESTION_SERVICE_URL", "https://opdv-api-dta.lobelia.earth"
)


def get_copernicusmarine_username() -> str:
    return required_environment_variable("COPERNICUSMARINE_USERNAME")


def get_copernicusmarine_password() -> str:
    return required_environment_variable("COPERNICUSMARINE_PASSWORD")
