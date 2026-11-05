"""Unit tests for Clerk JWT authentication dependency and AuthenticatedUser identity."""

import time
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.api.deps import (
    AuthenticatedUser,
    ClerkJWTVerifier,
    get_current_user,
    get_optional_user,
    parse_user_from_payload,
)
from backend.config import settings


@pytest.fixture(scope="module")
def rsa_keypair() -> tuple[str, str]:
    """Generate in-memory RSA private and public key pair for testing RS256 JWTs."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


@pytest.mark.asyncio
async def test_get_current_user_dev_mode_fallback() -> None:
    """Verify default dev user is provided when authentication is disabled and no token is passed."""
    with patch.object(settings, "auth_enabled", False):
        user = await get_current_user(credentials=None)
        assert isinstance(user, AuthenticatedUser)
        assert user.id == "dev_user_local"
        assert user.email == "developer@lycaon.kitchen"


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_auth_enabled_and_no_token() -> None:
    """Verify 401 is raised when auth is enabled and caller passes no authorization credentials."""
    with patch.object(settings, "auth_enabled", True):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication credentials were not provided" in exc_info.value.detail


def test_parse_user_from_payload() -> None:
    """Verify claims dictionary correctly populates AuthenticatedUser fields."""
    payload: dict[str, Any] = {
        "sub": "user_2xyz123",
        "email": "fenris@lycaon.kitchen",
        "first_name": "Fenris",
        "last_name": "Lycaon",
        "role": "chef",
    }
    user = parse_user_from_payload(payload)
    assert user.id == "user_2xyz123"
    assert user.email == "fenris@lycaon.kitchen"
    assert user.first_name == "Fenris"
    assert user.last_name == "Lycaon"
    assert user.claims["role"] == "chef"


@pytest.mark.asyncio
async def test_verify_valid_rs256_token(rsa_keypair: tuple[str, str]) -> None:
    """Verify valid RS256 token signed by private key passes verification."""
    private_pem, public_pem = rsa_keypair

    now = int(time.time())
    token_claims = {
        "sub": "user_clerk_999",
        "email": "chef@idunn.kitchen",
        "first_name": "Rishabh",
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(token_claims, private_pem, algorithm="RS256", headers={"kid": "test_key_1"})

    mock_key = MagicMock()
    mock_key.key = public_pem
    mock_jwk_client = MagicMock()
    mock_jwk_client.get_signing_key_from_jwt.return_value = mock_key

    with patch.object(ClerkJWTVerifier, "get_client", return_value=mock_jwk_client):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user(credentials)

        assert user.id == "user_clerk_999"
        assert user.email == "chef@idunn.kitchen"
        assert user.first_name == "Rishabh"


@pytest.mark.asyncio
async def test_verify_expired_token_raises_401(rsa_keypair: tuple[str, str]) -> None:
    """Verify expired token raises 401 with expiration error message."""
    private_pem, public_pem = rsa_keypair

    past = int(time.time()) - 3600
    expired_claims = {
        "sub": "user_expired",
        "iat": past - 3600,
        "exp": past,
    }
    token = jwt.encode(
        expired_claims, private_pem, algorithm="RS256", headers={"kid": "test_key_1"}
    )

    mock_key = MagicMock()
    mock_key.key = public_pem
    mock_jwk_client = MagicMock()
    mock_jwk_client.get_signing_key_from_jwt.return_value = mock_key

    with patch.object(ClerkJWTVerifier, "get_client", return_value=mock_jwk_client):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication token has expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_optional_user(rsa_keypair: tuple[str, str]) -> None:
    """Verify get_optional_user returns None without credentials and user with valid token."""
    # When credentials is None, optional user is None
    none_user = await get_optional_user(credentials=None)
    assert none_user is None

    # When credentials are provided, user is extracted
    private_pem, public_pem = rsa_keypair
    now = int(time.time())
    token = jwt.encode(
        {"sub": "user_opt", "email": "opt@kitchen.org", "iat": now, "exp": now + 60},
        private_pem,
        algorithm="RS256",
        headers={"kid": "k1"},
    )
    mock_key = MagicMock()
    mock_key.key = public_pem
    mock_jwk_client = MagicMock()
    mock_jwk_client.get_signing_key_from_jwt.return_value = mock_key

    with patch.object(ClerkJWTVerifier, "get_client", return_value=mock_jwk_client):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        opt_user = await get_optional_user(credentials)
        assert opt_user is not None
        assert opt_user.id == "user_opt"
