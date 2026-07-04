# apps/memory-api/security.py

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from pydantic import BaseModel

from apps.memory_api.config import settings

# This is the dependency that will be used in the path operations
# It will look for the "Authorization" header, check if it contains "Bearer" and a token, and return the token.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token"
)  # tokenUrl is not used in this flow, but is required


class TokenPayload(BaseModel):
    sub: str
    scope: str


class Auth:
    """
    A class to handle JWT verification.
    """

    def __init__(self):
        self.jwks = None

    async def get_jwks(self):
        """
        Retrieves the JSON Web Key Set (JWKS) from the authentication provider.
        The JWKS contains the public keys used to verify JWTs.
        Caches the JWKS for performance.
        """
        if self.jwks is None:
            # For Auth0, the JWKS URL is at https://<YOUR_DOMAIN>/.well-known/jwks.json
            jwks_url = f"https://{settings.OAUTH_DOMAIN}/.well-known/jwks.json"
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                self.jwks = response.json()
        return self.jwks

    async def verify_token(
        self,
        token: str = Depends(oauth2_scheme),
        security_scopes: SecurityScopes = None,
    ):
        """
        Verifies the JWT token.

        - Decodes the token using the public key from the JWKS.
        - Validates the claims (issuer, audience).
        - Checks if the token has the required scopes.
        """
        if not settings.OAUTH_ENABLED:
            # If OAuth is disabled, we bypass authentication.
            # In a real app, you might want a different behavior, like falling back to an API key.
            return TokenPayload(sub="anonymous", scope="")

        if token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided.",
            )

        jwks = await self.get_jwks()
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header"
            )

        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key",
            )

        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=settings.OAUTH_AUDIENCE,
                issuer=f"https://{settings.OAUTH_DOMAIN}/",
            )
            token_scopes = payload.get("scope", "").split()

            # Check if all required scopes are present in the token
            for scope in security_scopes.scopes:
                if scope not in token_scopes:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions.",
                    )

            return TokenPayload(sub=payload.get("sub"), scope=payload.get("scope"))

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.JWTClaimsError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect claims, please check audience and issuer",
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to parse authentication token",
            )


auth = Auth()
