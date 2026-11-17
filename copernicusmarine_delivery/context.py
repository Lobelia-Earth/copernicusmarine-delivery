import os
from dataclasses import dataclass

from copernicusmarine_delivery.auth import get_config
from copernicusmarine_delivery.core_functions.domain import GetConfigResponse
from copernicusmarine_delivery.environment_variables import (
    COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID,
)


@dataclass(frozen=True)
class ServiceContext:
    ingestion_service_url: str
    config: GetConfigResponse
    on_behalf_of: str | None = None


def get_ingestion_service_url(staging: bool = False) -> str:
    # A shorcut for testing purposes.
    if url := os.getenv("COPERNICUSMARINE_SERVICE_INGESTION_URL"):
        return url
    if staging:
        return "https://opdv-api-dta.marine.copernicus.eu"
    return "https://opdv-api.marine.copernicus.eu"


def build_context(staging: bool = False, on_behalf_of: str | None = None) -> ServiceContext:
    url = get_ingestion_service_url(staging)
    return ServiceContext(
        ingestion_service_url=url,
        config=get_config(url),
        on_behalf_of=on_behalf_of or COPERNICUSMARINE_SERVICE_PUSHING_ENTITY_ID,
    )
