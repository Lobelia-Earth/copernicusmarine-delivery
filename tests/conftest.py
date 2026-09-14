import json
import os
import random
from typing import Generator
from urllib.parse import parse_qsl

import boto3
import freezegun
import httpx
import pytest
import yaml

from pusher.core_functions.constants import (
    PUSHING_ENTITIES_PATH,
)
from pusher.environment_variables import (
    COPERNICUSMARINE_PASSWORD,
    COPERNICUSMARINE_USERNAME,
)
from pusher.s3_client import S3Client, get_s3_ingestion_client

random.seed(42)

_MANIFESTS_PATH_PREFIX = "deliveries/{pushing_entity_id}/"
_MANIFESTS_PATH = "deliveries/{pushing_entity_id}/{delivery_id}.json"
_PUSHING_ENTITY_ID = "TEST-ENTITY-FR"
_BUCKET_NAME = f"mdl-ing-{_PUSHING_ENTITY_ID.lower()}"

_PUSHING_ENTITIES_DICT = {
    "pushing-entities": [
        {
            "name": "GLO-MERCATOR-TOULOUSE-FR",
            "bucket": "mdl-ing-glo-mercator-toulouse-fr",
            "products": [
                {"name": "product1", "datasets": ["dataset1", "dataset2"]},
            ],
        },
        {
            "name": _PUSHING_ENTITY_ID,
            "bucket": _BUCKET_NAME,
            "products": [
                {"name": "product1", "datasets": ["dataset1", "dataset2"]},
            ],
        },
    ]
}

_DEFAULT_PUSHING_ENTITIES_YAML = yaml.dump(_PUSHING_ENTITIES_DICT).encode()
_BOTO_KWARGS = {
    "aws_access_key_id": "test",
    "aws_secret_access_key": "test",
    "region_name": "us-east-1",
}

# not freezing inside threading
freezegun.configure(
    default_ignore_list=[
        "nose.plugins",
        "six.moves",
        "django.utils.six.moves",
        "google.gax",
        # "threading",
        "Queue",
        "selenium",
        "_pytest.terminal.",
        "_pytest.runner.",
        "gi",
    ]
)


@pytest.fixture(autouse=True)
def mock_pushing_entities(monkeypatch):
    original_get_file_stream = S3Client.get_file_stream

    def _get_file_stream(self, path_to_file: str, **kwargs):
        if path_to_file == PUSHING_ENTITIES_PATH:
            return _DEFAULT_PUSHING_ENTITIES_YAML
        return original_get_file_stream(self, path_to_file, **kwargs)

    monkeypatch.setattr(S3Client, "get_file_stream", _get_file_stream)


@pytest.fixture(scope="session")
def ministack_endpoint() -> str:
    return os.environ.get("S3_ENDPOINT_URL", "http://localhost:4566")


@pytest.fixture
def s3_client(ministack_endpoint: str):
    return boto3.client("s3", endpoint_url=ministack_endpoint, **_BOTO_KWARGS)


@pytest.fixture
def ingestion_bucket(s3_client) -> Generator[str, None]:
    s3_client.create_bucket(Bucket=_BUCKET_NAME)
    yield _BUCKET_NAME
    _cleanup_bucket(s3_client, _BUCKET_NAME)


def _cleanup_bucket(s3_client, bucket: str) -> None:
    try:
        s3_client.head_bucket(Bucket=bucket)
    except s3_client.exceptions.ClientError:
        return
    for obj in s3_client.list_objects_v2(Bucket=bucket).get("Contents", []):
        s3_client.delete_object(Bucket=bucket, Key=obj["Key"])
    s3_client.delete_bucket(Bucket=bucket)


@pytest.fixture
def glo_mercator_bucket(s3_client) -> Generator[str, None]:
    bucket = "mdl-ing-glo-mercator-toulouse-fr"
    s3_client.create_bucket(Bucket=bucket)
    yield bucket
    _cleanup_bucket(s3_client, bucket)


@pytest.fixture
def service(
    ingestion_bucket: str, ministack_endpoint: str, set_env, ingestion_service
) -> S3Client:
    return get_s3_ingestion_client(
        pushing_entity_id=_PUSHING_ENTITY_ID,
        bucket_name=_BUCKET_NAME,
        token="test-token",
    )


@pytest.fixture
def cli_env(ministack_endpoint: str) -> dict:
    return {
        "OPDV_ACCESS_KEY_ID": "test",
        "OPDV_SECRET_ACCESS_KEY": "test",
        "OPDV_S3_ENDPOINT": ministack_endpoint,
        "ENVIRONMENT": "local",
    }


@pytest.fixture(autouse=False)
def set_env(monkeypatch, cli_env):
    for key, value in cli_env.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def skip_delivery_ids_validation(monkeypatch):
    from pusher.core_functions import core_functions

    monkeypatch.setattr(core_functions, "validate_delivery_ids", lambda *a, **kw: None)


def _mock_keycloak_handler(request: httpx.Request) -> httpx.Response | None:
    """Mocks the external Keycloak provider (discovery + token endpoint). Not ours to control."""
    path = request.url.path

    if path == "/.well-known/openid-configuration" and request.method == "GET":
        return httpx.Response(
            200,
            json={"token_endpoint": "https://mock_url/token"},
        )

    if path == "/token" and request.method == "POST":
        body = dict(parse_qsl(request.content.decode()))
        if (
            body.get("username") == COPERNICUSMARINE_USERNAME
            and body.get("password") == COPERNICUSMARINE_PASSWORD
        ):
            return httpx.Response(200, json={"access_token": "test-token"})
        return httpx.Response(401, json={"error": "Invalid credentials"})

    return None


@pytest.fixture
def mock_keycloak():
    return _mock_keycloak_handler


@pytest.fixture
def ingestion_service(s3_client, mock_keycloak, monkeypatch):
    """Patches http_client with an httpx-backed mock transport that mimics the ingestion service.

    - POST /delivery: accepts a delivery JSON, saves it to S3, returns 201.
    - GET /delivery/{pushing_entity_id}: returns all stored delivery for the entity.
    - GET /.well-known/config: returns the oidc config needed to authenticate.
    - POST /credentials: returns temporary S3 credentials for the pushing entity.

    Keycloak calls (discovery + token) are mocked separately by `mock_keycloak`.
    """

    def _handler(request: httpx.Request) -> httpx.Response:
        keycloak_response = mock_keycloak(request)
        if keycloak_response is not None:
            return keycloak_response

        path = request.url.path

        if path == "/delivery" and request.method == "POST":
            body = json.loads(request.content)
            bearer = request.headers.get("Authorization")
            if bearer != "Bearer test-token":
                return httpx.Response(401, json={"error": "Invalid bearer token"})
            delivery_id = body["delivery_id"]
            pushing_entity_id = body["pushing_entity_id"]
            bucket = next(
                pe["bucket"]
                for pe in _PUSHING_ENTITIES_DICT["pushing-entities"]
                if pe["name"] == pushing_entity_id
            )
            # Ensure bucket exists (idempotent in localstack)
            try:
                s3_client.create_bucket(Bucket=bucket)
            except s3_client.exceptions.BucketAlreadyOwnedByYou:
                pass
            key = _MANIFESTS_PATH.format(
                pushing_entity_id=pushing_entity_id, delivery_id=delivery_id
            )
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(body),
            )
            return httpx.Response(201, json=body)

        if path.startswith("/delivery/") and request.method == "GET":
            pushing_entity_id = path.split("/")[2]
            if not pushing_entity_id:
                return httpx.Response(400, json={"error": "Missing pushing_entity_id"})
            bearer = request.headers.get("Authorization")
            if bearer != "Bearer test-token":
                return httpx.Response(401, json={"error": "Invalid bearer token"})
            bucket = next(
                pe["bucket"]
                for pe in _PUSHING_ENTITIES_DICT["pushing-entities"]
                if pe["name"] == pushing_entity_id
            )
            prefix = _MANIFESTS_PATH_PREFIX.format(pushing_entity_id=pushing_entity_id)
            deliveries = []
            resp = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            for obj in resp.get("Contents", []):
                data = s3_client.get_object(Bucket=bucket, Key=obj["Key"])
                deliveries.append(json.loads(data["Body"].read()))
            return httpx.Response(200, json={"deliveries": deliveries})

        if path.startswith("/.well-known/config") and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "oidc_config": {
                        "oidc_provider_url": "mock_url",
                        "oidc_client_id": "mock_client",
                        "grant_type": "all-granted",
                        "scope": "sky",
                    }
                }
            )

        if path.startswith("/credentials") and request.method == "POST":
            bearer = request.headers.get("Authorization")
            if bearer != "Bearer test-token":
                return httpx.Response(401, json={"error": "Invalid bearer token"})
            return httpx.Response(
                200,
                json={
                    "access_key_id": "test",
                    "secret_access_key": "test",
                    "session_token": "test",
                },
            )

        return httpx.Response(404)

    mock_client = httpx.Client(transport=httpx.MockTransport(_handler))
    monkeypatch.setattr("pusher.http_client.http_client", mock_client)
    monkeypatch.setattr("pusher.core_functions.delivery.http_client", mock_client)
    monkeypatch.setattr("pusher.core_functions.core_functions.http_client", mock_client)
    monkeypatch.setattr("pusher.s3_client.http_client", mock_client)

    yield mock_client

    mock_client.close()
    for bucket in [_BUCKET_NAME, "mdl-ing-glo-mercator-toulouse-fr"]:
        _cleanup_bucket(s3_client, bucket)
