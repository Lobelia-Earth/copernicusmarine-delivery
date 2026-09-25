import json
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator
from urllib.parse import parse_qsl

import boto3
import freezegun
import httpx
import pytest
import yaml

from copernicusmarine_delivery.core_functions.core_functions import get_config
from copernicusmarine_delivery.environment_variables import (
    get_copernicusmarine_password,
    get_copernicusmarine_username,
)
from copernicusmarine_delivery.s3_client import S3Client, get_s3_ingestion_client

random.seed(42)

_MANIFESTS_PATH_PREFIX = "deliveries/{pushing_entity_id}/"
_MANIFESTS_PATH = "deliveries/{pushing_entity_id}/{delivery_id}.json"
_PUSHING_ENTITY_ID = "TEST-ENTITY-FR"
_BUCKET_NAME = f"mdl-ing-{_PUSHING_ENTITY_ID.lower()}"
_TOKEN_PUSHING_ENTITY_ID = "GLO-MERCATOR-TOULOUSE-FR"

_PUSHING_ENTITIES_PATH = Path(__file__).parent / "resources" / "pushing_entities.yml"
_PUSHING_ENTITIES_DICT = yaml.safe_load(_PUSHING_ENTITIES_PATH.read_text())

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


@pytest.fixture(scope="session")
def ministack_endpoint() -> str:
    return os.environ.get("S3_ENDPOINT_URL", "http://localhost:4566")


@pytest.fixture(scope="session", autouse=True)
def _warm_obstore_datetime_cache(ministack_endpoint: str) -> None:
    """obstore caches the `datetime.datetime` class (pyo3/jiff) on first use,
    process-wide. If that first use happens inside a frozen test, the cache
    gets poisoned with freezegun's FakeDatetime and every later unfrozen
    obstore call breaks with "'datetime' object is not an instance of
    'FakeDatetime'". Session-scoped (just run once) + autouse => this runs during fixture
    setup for whichever test runs first, i.e. always before @freeze_time
    activates, pinning the cache to the real class.
    """
    from obstore import list as list_obstore
    from obstore.store import S3Store

    def _credential_provider(*_args: object, **_kwargs: object) -> dict:
        return {
            "access_key_id": "test",
            "secret_access_key": "test",
            "token": "test",
            "expires_at": datetime.now(tz=timezone.utc) + timedelta(minutes=30),
        }

    store = S3Store.from_url(
        url="s3://obstore-datetime-cache-warmup",
        config={"endpoint": ministack_endpoint},
        credential_provider=_credential_provider,
        client_options={"allow_http": True},
    )
    try:
        next(iter(list_obstore(store=store, chunk_size=1)), None)
    except Exception:
        pass


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
    ingestion_bucket: str, ministack_endpoint: str, ingestion_service
) -> S3Client:
    return get_s3_ingestion_client(
        pushing_entity_id=_PUSHING_ENTITY_ID,
        bucket_name=_BUCKET_NAME,
        config=get_config(),
        endpoint_url=ministack_endpoint,
    )


@pytest.fixture
def skip_delivery_ids_validation(monkeypatch):
    from copernicusmarine_delivery.core_functions import core_functions

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
            body.get("username") == get_copernicusmarine_username()
            and body.get("password") == get_copernicusmarine_password()
        ):
            return httpx.Response(
                200,
                json={
                    "access_token": "test-token",
                    "expires_in": 300,
                    "refresh_token": "refresh-token",
                    "refresh_expires_in": 600,
                },
            )
        return httpx.Response(401, json={"error": "Invalid credentials"})

    return None


@pytest.fixture
def mock_keycloak():
    return _mock_keycloak_handler


def validate_test_token_header(request) -> httpx.Response | None:
    bearer = request.headers.get("Authorization")
    if bearer != "Bearer test-token":
        return httpx.Response(401, json={"error": "Invalid bearer token"})


@pytest.fixture
def ingestion_service(s3_client, mock_keycloak, monkeypatch):
    """Patches http_client with an httpx-backed mock transport that mimics the ingestion service.

    - POST /delivery: accepts a delivery JSON, saves it to S3, returns 201.
    - GET /delivery: returns all stored deliveries for the entity resolved from the token.
    - GET /.well-known/config: returns the oidc config needed to authenticate.
    - GET /credentials: returns temporary S3 credentials for the entity resolved from the token.

    Keycloak calls (discovery + token) are mocked separately by `mock_keycloak`.
    """

    def _handler(request: httpx.Request) -> httpx.Response:
        keycloak_response = mock_keycloak(request)
        if keycloak_response is not None:
            return keycloak_response

        path = request.url.path

        if path == "/delivery" and request.method == "POST":
            if invalid_token_response := validate_test_token_header(request):
                return invalid_token_response
            body = json.loads(request.content)
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

        if path == "/delivery" and request.method == "GET":
            if invalid_token_response := validate_test_token_header(request):
                return invalid_token_response
            pushing_entity_id = _TOKEN_PUSHING_ENTITY_ID
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
                    },
                    "pushing_entities": _PUSHING_ENTITIES_DICT,
                },
            )

        if path == "/.well-known/pushing-entity-config" and request.method == "GET":
            if invalid_token_response := validate_test_token_header(request):
                return invalid_token_response
            pushing_entity = next(
                pe
                for pe in _PUSHING_ENTITIES_DICT["pushing-entities"]
                if pe["name"] == _TOKEN_PUSHING_ENTITY_ID
            )
            return httpx.Response(
                200,
                json={
                    "pushing_entity": pushing_entity,
                    "s3_endpoint_url": os.environ.get(
                        "S3_ENDPOINT_URL", "http://localhost:4566"
                    ),
                },
            )

        if path == "/credentials" and request.method == "GET":
            if invalid_token_response := validate_test_token_header(request):
                return invalid_token_response
            return httpx.Response(
                200,
                json={
                    "access_key_id": "test",
                    "secret_access_key": "test",
                    "session_token": "test",
                    "expiration": str(
                        datetime.now(tz=timezone.utc) + timedelta(minutes=30)
                    ),
                },
            )

        return httpx.Response(404)

    mock_client = httpx.Client(transport=httpx.MockTransport(_handler))
    monkeypatch.setattr(
        "copernicusmarine_delivery.http_client.http_client", mock_client
    )
    monkeypatch.setattr(
        "copernicusmarine_delivery.core_functions.delivery.http_client", mock_client
    )
    monkeypatch.setattr("copernicusmarine_delivery.auth.http_client", mock_client)
    monkeypatch.setattr("copernicusmarine_delivery.s3_client.http_client", mock_client)

    yield mock_client

    mock_client.close()
    for bucket in [_BUCKET_NAME, "mdl-ing-glo-mercator-toulouse-fr"]:
        _cleanup_bucket(s3_client, bucket)
