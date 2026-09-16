import os


def required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} environment variable is not set.")
    return value


ALLOW_HTTP = bool(os.getenv("ALLOW_HTTP"))
COPERNICUSMARINE_USERNAME = required_environment_variable("COPERNICUSMARINE_USERNAME")
COPERNICUSMARINE_PASSWORD = required_environment_variable("COPERNICUSMARINE_PASSWORD")
INGESTION_SERVICE_URL = os.getenv(
    "INGESTION_SERVICE_URL", "https://opdv-api-dta.lobelia.earth"
)
