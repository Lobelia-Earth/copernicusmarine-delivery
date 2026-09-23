import time

from copernicusmarine_delivery.core_functions.domain import (
    GetConfigResponse,
    GetPushingEntityConfigResponse,
)
from copernicusmarine_delivery.environment_variables import (
    COPERNICUSMARINE_PASSWORD,
    COPERNICUSMARINE_USERNAME,
    INGESTION_SERVICE_URL,
)
from copernicusmarine_delivery.http_client import http_client
from copernicusmarine_delivery.logger import logger

_token_cache: dict = {}

OIDC_DISCOVERY_URL = "https://{oidc_provider_url}/.well-known/openid-configuration"


def fetch_keycloak_token(config: GetConfigResponse) -> str:
    """Gets the Keycloak token necessary to operate with OPDV using username nd password.
    Small cache built to reuse token whenever possible"""
    now = time.time()
    if (
        _token_cache.get("access_token")
        and now < _token_cache["access_expires_at"] - 30
    ):
        logger.debug("Keycloak Token -> Reusing from cache")
        return _token_cache["access_token"]

    discovery_response = http_client.get(
        OIDC_DISCOVERY_URL.format(
            oidc_provider_url=config.oidc_config.oidc_provider_url
        )
    )
    discovery_response.raise_for_status()

    token_endpoint = discovery_response.json()["token_endpoint"]

    if (
        _token_cache.get("refresh_token")
        and now < _token_cache["refresh_expires_at"] - 30
    ):
        logger.debug("Keycloak Token -> Fetching from refresh token")
        data = {
            "grant_type": "refresh_token",
            "client_id": config.oidc_config.oidc_client_id,
            "refresh_token": _token_cache["refresh_token"],
        }
    else:
        logger.debug("Keycloak Token -> Fetching new access token")
        data = {
            "grant_type": config.oidc_config.grant_type,
            "client_id": config.oidc_config.oidc_client_id,
            "username": COPERNICUSMARINE_USERNAME,
            "password": COPERNICUSMARINE_PASSWORD,
            "scope": config.oidc_config.scope,
        }
    token_response = http_client.post(token_endpoint, data=data)
    token_response.raise_for_status()
    token_response_json = token_response.json()
    _token_cache.update(
        access_token=token_response_json["access_token"],
        access_expires_at=now + token_response_json["expires_in"],
        refresh_token=token_response_json["refresh_token"],
        refresh_expires_at=now + token_response_json["refresh_expires_in"],
    )
    return token_response_json["access_token"]


def get_config() -> GetConfigResponse:
    config_response = http_client.get(f"{INGESTION_SERVICE_URL}/.well-known/config")
    config_response.raise_for_status()
    return GetConfigResponse.model_validate_json(config_response.content)


def get_pushing_entity_config(token: str) -> GetPushingEntityConfigResponse:
    pushing_entity_config_response = http_client.get(
        f"{INGESTION_SERVICE_URL}/.well-known/pushing-entity-config",
        headers={"Authorization": f"Bearer {token}"},
    )
    pushing_entity_config_response.raise_for_status()
    return GetPushingEntityConfigResponse.model_validate_json(
        pushing_entity_config_response.content
    )
