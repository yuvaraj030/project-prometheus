"""
JWT Authentication — Fix #21
==============================
Provides JWT-based multi-tenant authentication for the Gateway.
  - POST /auth/login  → returns {access_token, tenant_id}
  - Dependency: verify_jwt(token) → extracts tenant_id from token
  - All Gateway routes can use Depends(verify_jwt) instead of the raw API key

Setup:
    export JWT_SECRET=<your-random-secret>   # Required (min 32 chars)
    export JWT_EXPIRY_HOURS=24               # Optional, default 24 h

Usage in gateway.py:
    from jwt_auth import JWTAuth, UserLogin
    auth = JWTAuth()
    app.include_router(auth.router)

    @app.get("/protected", dependencies=[Depends(auth.verify_jwt)])
    async def protected_route():
        ...
"""

import os
import logging
import datetime
from typing import Optional, Dict

logger = logging.getLogger("JWTAuth")

try:
    import jwt as pyjwt          # pip install PyJWT
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("[JWT] 'PyJWT' not installed. Run: pip install PyJWT")

try:
    from fastapi import APIRouter, HTTPException, Depends, Header, status
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


if FASTAPI_AVAILABLE:
    class UserLogin(BaseModel):
        username: str
        password: str
        tenant_id: int = 1


# Default user store (username -> {password, tenant_id, role})
# In production, replace with DB lookup.
_DEFAULT_USERS: Dict[str, Dict] = {
    "admin": {
        "password": os.getenv("AGENT_ADMIN_PASSWORD", "admin"),
        "tenant_id": 1,
        "role": "admin",
    },
}


class JWTAuth:
    """
    JWT Authentication manager.
    Creates a FastAPI router with /auth/login and /auth/refresh endpoints.
    """

    def __init__(self,
                 secret: Optional[str] = None,
                 expiry_hours: int = None,
                 users: Dict = None):
        self.secret = secret or os.getenv("JWT_SECRET", "change-me-jwt-secret")
        self.expiry_hours = expiry_hours or int(os.getenv("JWT_EXPIRY_HOURS", "24"))
        self.users = users or _DEFAULT_USERS
        self.algorithm = "HS256"

        if not JWT_AVAILABLE:
            logger.error("[JWT] PyJWT unavailable — JWT auth disabled.")
            return

        if self.secret == "change-me-jwt-secret":
            logger.warning("[JWT] Using default JWT secret — set JWT_SECRET env var!")

        if FASTAPI_AVAILABLE:
            self.router = self._build_router()
            self.bearer = HTTPBearer(auto_error=False)

    def create_token(self, tenant_id: int, username: str, role: str = "user") -> str:
        """Create a signed JWT for the given user."""
        if not JWT_AVAILABLE:
            return ""
        payload = {
            "sub": username,
            "tenant_id": tenant_id,
            "role": role,
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=self.expiry_hours),
        }
        return pyjwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict:
        """Decode and validate a JWT. Raises ValueError on failure."""
        if not JWT_AVAILABLE:
            raise ValueError("PyJWT not installed")
        try:
            return pyjwt.decode(token, self.secret, algorithms=[self.algorithm])
        except pyjwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except pyjwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")

    def verify_jwt(self):
        """FastAPI dependency: extracts and validates Bearer JWT from Authorization header."""
        if not (JWT_AVAILABLE and FASTAPI_AVAILABLE):
            # If JWT not available, pass-through (no auth)
            async def _noop(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
                return {"tenant_id": 1, "role": "admin"}
            return _noop

        async def _verify(credentials: Optional[HTTPAuthorizationCredentials] = Depends(self.bearer)):
            if not credentials:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token provided")
            try:
                payload = self.decode_token(credentials.credentials)
                return payload
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
        return _verify

    def _build_router(self) -> APIRouter:
        router = APIRouter(prefix="/auth", tags=["authentication"])

        @router.post("/login")
        async def login(credentials: UserLogin):
            user = self.users.get(credentials.username)
            if not user or user["password"] != credentials.password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password",
                )
            # Override tenant_id with user's assigned tenant
            tenant_id = user.get("tenant_id", credentials.tenant_id)
            token = self.create_token(
                tenant_id=tenant_id,
                username=credentials.username,
                role=user.get("role", "user"),
            )
            return {
                "access_token": token,
                "token_type": "bearer",
                "tenant_id": tenant_id,
                "expires_in_hours": self.expiry_hours,
            }

        @router.post("/refresh")
        async def refresh(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
            if not credentials:
                raise HTTPException(status_code=401, detail="No token")
            try:
                payload = self.decode_token(credentials.credentials)
                new_token = self.create_token(
                    tenant_id=payload["tenant_id"],
                    username=payload["sub"],
                    role=payload.get("role", "user"),
                )
                return {"access_token": new_token, "token_type": "bearer"}
            except ValueError as e:
                raise HTTPException(status_code=401, detail=str(e))

        @router.get("/me")
        async def me(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
            if not credentials:
                raise HTTPException(status_code=401, detail="No token")
            try:
                payload = self.decode_token(credentials.credentials)
                return {"username": payload["sub"], "tenant_id": payload["tenant_id"], "role": payload.get("role")}
            except ValueError as e:
                raise HTTPException(status_code=401, detail=str(e))

        return router
