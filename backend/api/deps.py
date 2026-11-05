"""FastAPI authentication dependencies and Clerk JWT verification."""

from __future__ import annotations

import logging
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWKClient
from pydantic import BaseModel, Field

from ..config import settings

logger = logging.getLogger(__name__)

# Reusable security scheme to extract bearer tokens from request authorization header.
security_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Strongly-typed authenticated caller identity extracted from verified JWT claims."""

    id: str = Field(..., description="Unique caller identifier (Clerk sub claim)")
    email: str | None = Field(default=None, description="Primary email address")
    first_name: str | None = Field(default=None, description="User first name")
    last_name: str | None = Field(default=None, description="User last name")
    claims: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw validated JWT payload claims",
    )


class ClerkJWTVerifier:
    """Validator for Clerk RS256 JSON Web Tokens using remote JWKS public keys."""

    _jwk_clients: dict[str, PyJWKClient] = {}

    @classmethod
    def get_jwks_url(cls) -> str:
        """Resolve public JWKS endpoint URL from configuration.

        Returns:
            Resolved JWKS URL string.
        """
        # Resolve explicit JWKS URL or construct from configured issuer domain.
        if settings.clerk_jwks_url:
            return settings.clerk_jwks_url
        if settings.clerk_issuer:
            issuer = settings.clerk_issuer.rstrip("/")
            return f"{issuer}/.well-known/jwks.json"
        return "https://api.clerk.com/v1/jwks"

    @classmethod
    def get_client(cls, jwks_url: str) -> PyJWKClient:
        """Get or initialize cached PyJWKClient to avoid redundant network roundtrips.

        Args:
            jwks_url: Target JWKS endpoint URL.

        Returns:
            Cached PyJWKClient instance.
        """
        # Cache client instance to reuse cached public keys across requests.
        if jwks_url not in cls._jwk_clients:
            cls._jwk_clients[jwks_url] = PyJWKClient(
                jwks_url,
                cache_jwk_set=True,
                lifespan=3600,
            )
        return cls._jwk_clients[jwks_url]

    @classmethod
    def verify_token(
        cls,
        token: str,
        jwks_url: str | None = None,
        expected_issuer: str | None = None,
    ) -> dict[str, Any]:
        """Verify RS256 signature and return decoded JWT claims.

        Args:
            token: Raw Bearer token string.
            jwks_url: Optional JWKS URL override.
            expected_issuer: Optional issuer claim constraint.

        Returns:
            Decoded claims payload dictionary.

        Raises:
            HTTPException: If token is expired, invalid, or untrusted.
        """
        target_jwks_url = jwks_url or cls.get_jwks_url()
        client = cls.get_client(target_jwks_url)

        try:
            # Match key id in token header to public key in cached key set.
            signing_key = client.get_signing_key_from_jwt(token)
            decode_kwargs: dict[str, Any] = {
                "algorithms": ["RS256"],
                "options": {"verify_aud": False},
            }
            if expected_issuer:
                decode_kwargs["issuer"] = expected_issuer

            return jwt.decode(token, signing_key.key, **decode_kwargs)
        except ExpiredSignatureError as exc:
            logger.info("Bearer token signature expired: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        except (InvalidTokenError, Exception) as exc:
            logger.warning("Failed to verify bearer token: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc


def parse_user_from_payload(payload: dict[str, Any]) -> AuthenticatedUser:
    """Extract strongly-typed AuthenticatedUser from decoded Clerk JWT claims.

    Args:
        payload: Decoded JWT claims dictionary.

    Returns:
        AuthenticatedUser instance.
    """
    user_id = payload.get("sub", "")
    email = payload.get("email")

    # Extract email from Clerk nested primary email identity if missing from root.
    if not email and "email_addresses" in payload:
        addrs = payload.get("email_addresses", [])
        if addrs and isinstance(addrs, list):
            email = addrs[0].get("email_address")

    return AuthenticatedUser(
        id=user_id,
        email=email,
        first_name=payload.get("first_name"),
        last_name=payload.get("last_name"),
        claims=payload,
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security_scheme)],
) -> AuthenticatedUser:
    """Enforce authentication and extract validated caller identity.

    Args:
        credentials: Extracted HTTP Bearer credentials.

    Returns:
        AuthenticatedUser identity.

    Raises:
        HTTPException: If token is absent or invalid when authentication is active.
    """
    # Supply development identity when auth is not configured to ease local development.
    if credentials is None:
        if settings.auth_enabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return AuthenticatedUser(
            id="dev_user_local",
            email="developer@lycaon.kitchen",
            first_name="Local",
            last_name="Developer",
        )

    # Decode and verify token signature using remote Clerk JWKS public keys.
    payload = ClerkJWTVerifier.verify_token(
        credentials.credentials,
        expected_issuer=settings.clerk_issuer,
    )
    return parse_user_from_payload(payload)


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security_scheme)],
) -> AuthenticatedUser | None:
    """Attempt optional authentication extraction without rejecting anonymous callers.

    Args:
        credentials: Optional extracted HTTP Bearer credentials.

    Returns:
        AuthenticatedUser identity if present and valid, otherwise None.
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# Annotated dependency alias for clean endpoint handler signatures.
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
OptionalUser = Annotated[AuthenticatedUser | None, Depends(get_optional_user)]
