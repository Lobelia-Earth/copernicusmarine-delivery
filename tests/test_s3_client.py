import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from obstore.store import S3Store

from copernicusmarine_delivery.core_functions.constants import DEFAULT_CHUNK_SIZE_MB
from copernicusmarine_delivery.core_functions.core_functions import get_config
from copernicusmarine_delivery.core_functions.domain import ErrorFile, S3File
from copernicusmarine_delivery.core_functions.exceptions import NoSuchBucketException
from copernicusmarine_delivery.core_functions.utils import megabytes_to_bytes
from copernicusmarine_delivery.s3_client import (
    _CLIENT_CONFIG,
    _RETRY_CONFIG,
    OpdvS3CredentialProvider,
    S3Client,
    _make_client,
    get_s3_ingestion_client,
)

RESOURCES = Path("tests/resources/dataset1")


def test_no_such_bucket_raises(ministack_endpoint: str, ingestion_service):
    with pytest.raises(NoSuchBucketException):
        get_s3_ingestion_client(
            pushing_entity_id="TEST-ENTITY-FR",
            bucket_name="nonexistent-entity-bucket-name",
            config=get_config(),
            endpoint_url=ministack_endpoint,
        )


def test_upload_file_success(service: S3Client, s3_client, ingestion_bucket: str):
    key = "data/test/file1.txt"
    result = service.upload_file(
        key=key,
        file=RESOURCES / "file1.txt",
        chunk_size=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        dry_run=False,
        raise_on_error=False,
        use_multipart=True,
    )
    assert isinstance(result, S3File)
    assert result.ingestion_system_s3_path == key
    assert result.e_tag
    s3_client.head_object(Bucket=ingestion_bucket, Key=key)


@pytest.mark.slow
def test_upload_file_nonexistent_returns_error(
    service: S3Client, ingestion_bucket: str
):
    result = service.upload_file(
        key="data/test/missing.nc",
        file=Path("nonexistent/file.nc"),
        chunk_size=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        dry_run=False,
        raise_on_error=False,
        use_multipart=True,
    )
    assert isinstance(result, ErrorFile)


def test_upload_multiple_files(
    service: S3Client,
    s3_client,
    ingestion_bucket: str,
):
    mapping = {
        RESOURCES / "file1.txt": "data/test/file1.txt",
        RESOURCES / "file2.txt": "data/test/file2.txt",
    }
    result = service.upload_multiple_files(
        mapping,
        chunk_size=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        max_concurrent_uploads=10,
        dry_run=False,
        raise_on_error=False,
    )
    assert len(result.successful_files) == 2
    assert len(result.errored_files) == 0
    for f in result.successful_files:
        s3_client.head_object(Bucket=ingestion_bucket, Key=f.ingestion_system_s3_path)


@pytest.mark.slow
def test_upload_multiple_files_partial_failure(
    service: S3Client, ingestion_bucket: str
):
    mapping = {
        RESOURCES / "file1.txt": "data/test/file1.txt",
        Path("nonexistent/file.nc"): "data/test/missing.nc",
    }
    result = service.upload_multiple_files(
        mapping,
        chunk_size=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        max_concurrent_uploads=10,
        dry_run=False,
        raise_on_error=False,
    )
    assert len(result.successful_files) == 1
    assert len(result.errored_files) == 1
    assert result.successful_files[0].ingestion_system_s3_path == "data/test/file1.txt"


def _make_credentials_handler(
    mock_keycloak, ministack_endpoint: str, expiry_seconds: float
):
    """Builds a mock transport handler that counts calls to `/credentials`
    and issues credentials expiring `expiry_seconds` from now. Returns
    (handler, call_counter) where call_counter is a single-item list used as
    a mutable box so the caller can read the live count."""
    call_counter = [0]

    def _handler(request: httpx.Request) -> httpx.Response:
        keycloak_response = mock_keycloak(request)
        if keycloak_response is not None:
            return keycloak_response

        if request.url.path == "/.well-known/config" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "oidc_config": {
                        "oidc_provider_url": "mock_url",
                        "oidc_client_id": "mock_client",
                        "grant_type": "all-granted",
                        "scope": "sky",
                    },
                    "s3_config": {"endpoint_url": ministack_endpoint},
                },
            )

        if request.url.path == "/credentials" and request.method == "GET":
            call_counter[0] += 1
            return httpx.Response(
                200,
                json={
                    "access_key_id": "test",
                    "secret_access_key": "test",
                    "session_token": "test",
                    "expiration": (
                        datetime.now(tz=timezone.utc)
                        + timedelta(seconds=expiry_seconds)
                    ).isoformat(),
                },
            )

        return httpx.Response(404)

    return _handler, call_counter


def _build_service_with_mock_transport(
    handler, monkeypatch, ministack_endpoint: str, ingestion_bucket: str
) -> S3Client:
    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr("copernicusmarine_delivery.auth.http_client", mock_client)
    monkeypatch.setattr("copernicusmarine_delivery.s3_client.http_client", mock_client)
    return get_s3_ingestion_client(
        pushing_entity_id="TEST-ENTITY-FR",
        bucket_name=ingestion_bucket,
        config=get_config(),
        endpoint_url=ministack_endpoint,
    )


def _upload_dummy_file(service: S3Client, key: str) -> None:
    service.upload_file(
        key=key,
        file=RESOURCES / "file1.txt",
        chunk_size=megabytes_to_bytes(DEFAULT_CHUNK_SIZE_MB),
        dry_run=False,
        raise_on_error=True,
        use_multipart=True,
    )


@pytest.mark.parametrize(
    "expiry_seconds,expect_refetch",
    [
        pytest.param(600, False, id="above_min_ttl-caches"),
        pytest.param(60, True, id="below_min_ttl-refetches"),
    ],
)
def test_credential_provider_respects_min_ttl_boundary(
    ministack_endpoint: str,
    ingestion_bucket: str,
    mock_keycloak,
    monkeypatch,
    expiry_seconds: int,
    expect_refetch: bool,
):
    """obstore's token cache (`pyo3-object_store/src/credentials.rs`,
    `TokenCache::default`) only reuses a cached credential while it has more
    than `min_ttl` (default 300s) of remaining life - *unless* the previous
    fetch happened within the last `fetch_backoff` (100ms), in which case it
    reuses the cache regardless of `min_ttl`.

    A 600 seconds expiry should not re-fetch, but a 60 seconds should re-fetch.
    """
    handler, call_counter = _make_credentials_handler(
        mock_keycloak, ministack_endpoint, expiry_seconds=expiry_seconds
    )
    service = _build_service_with_mock_transport(
        handler, monkeypatch, ministack_endpoint, ingestion_bucket
    )

    _upload_dummy_file(service, "data/test/cache1.txt")
    calls_after_first_upload = call_counter[0]
    assert calls_after_first_upload == 1

    time.sleep(0.5)  # clears fetch_backoff without threatening the above-min_ttl case

    _upload_dummy_file(service, "data/test/cache2.txt")
    expected_calls = calls_after_first_upload + (1 if expect_refetch else 0)
    assert call_counter[0] == expected_calls


def _build_service_with_refresh_threshold(
    handler,
    monkeypatch,
    ministack_endpoint: str,
    ingestion_bucket: str,
    refresh_threshold: timedelta,
) -> S3Client:
    """Same wiring as `_build_service_with_mock_transport`, but builds the
    `OpdvS3CredentialProvider` directly so a non-default `refresh_threshold`
    can be passed in. `get_s3_ingestion_client` always uses the production
    default, so this bypasses it to reach the lower-level pieces."""
    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr("copernicusmarine_delivery.auth.http_client", mock_client)
    monkeypatch.setattr("copernicusmarine_delivery.s3_client.http_client", mock_client)

    credential_provider = OpdvS3CredentialProvider(
        "TEST-ENTITY-FR", get_config(), refresh_threshold=refresh_threshold
    )
    store = S3Store.from_url(
        url=f"s3://{ingestion_bucket}",
        config={"endpoint": ministack_endpoint},
        credential_provider=credential_provider,
        retry_config=_RETRY_CONFIG,
        client_options=_CLIENT_CONFIG,
    )
    return _make_client(bucket_name=ingestion_bucket, store=store)


def test_credential_provider_refresh_threshold_overrides_default(
    ministack_endpoint: str,
    ingestion_bucket: str,
    mock_keycloak,
    monkeypatch,
):
    """This proves we can modify obstore's internal `refresh_threshold`.
    In such a way, a credential that is to expire in 60 seconds,
    with a new threshold of 10 (as opposed to 300) will now be used."""
    handler, call_counter = _make_credentials_handler(
        mock_keycloak, ministack_endpoint, expiry_seconds=60
    )
    service = _build_service_with_refresh_threshold(
        handler,
        monkeypatch,
        ministack_endpoint,
        ingestion_bucket,
        refresh_threshold=timedelta(seconds=10),
    )

    _upload_dummy_file(service, "data/test/threshold1.txt")
    calls_after_first_upload = call_counter[0]
    assert calls_after_first_upload == 1

    time.sleep(
        0.5
    )  # clears fetch_backoff; 59.5s remaining is still > our 10s threshold

    _upload_dummy_file(service, "data/test/threshold2.txt")
    assert call_counter[0] == calls_after_first_upload
