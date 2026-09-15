import time

from delivery_common.domain import PushingEntity
from pusher.core_functions.domain import GetConfigResponse
from pusher.environment_variables import (
    COPERNICUSMARINE_PASSWORD,
    COPERNICUSMARINE_USERNAME,
    INGESTION_SERVICE_URL,
)
from pusher.http_client import http_client

_token_cache: dict = {}


def login(config: GetConfigResponse) -> str:
    now = time.time()
    if (
        _token_cache.get("access_token")
        and now < _token_cache["access_expires_at"] - 30
    ):
        return _token_cache["access_token"]

    discovery_response = http_client.get(
        f"https://{config.oidc_config.oidc_provider_url}/.well-known/openid-configuration"
    )
    discovery_response.raise_for_status()

    token_endpoint = discovery_response.json()["token_endpoint"]

    if (
        _token_cache.get("refresh_token")
        and now < _token_cache["refresh_expires_at"] - 30
    ):
        data = {
            "grant_type": "refresh_token",
            "client_id": config.oidc_config.oidc_client_id,
            "refresh_token": _token_cache["refresh_token"],
        }
    else:
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


def get_pushing_entity_config(pushing_entity_id: str, token: str) -> PushingEntity:
    pushing_entity_config_response = http_client.get(
        f"{INGESTION_SERVICE_URL}/.well-known/pushing-entity-config/{pushing_entity_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    pushing_entity_config_response.raise_for_status()
    return PushingEntity.model_validate_json(pushing_entity_config_response.content)
