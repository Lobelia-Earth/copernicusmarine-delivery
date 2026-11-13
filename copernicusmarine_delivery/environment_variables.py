import os


def required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is not set.")
    return value


ALLOW_HTTP = bool(os.getenv("ALLOW_HTTP"))
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "https://opdv-api-dta.lobelia.earth")
COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID = os.getenv("COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID", None)
# This becomes the default for Python interface. CLI defaults to INFO in the OPTION definition.
COPERNICUSMARINE_SERVICE_LOG_LEVEL = os.getenv("COPERNICUSMARINE_SERVICE_LOG_LEVEL", "WARNING").upper()


def get_copernicusmarine_username() -> str:
    return required_environment_variable("COPERNICUSMARINE_SERVICE_USERNAME")


def get_copernicusmarine_password() -> str:
    return required_environment_variable("COPERNICUSMARINE_SERVICE_PASSWORD")
