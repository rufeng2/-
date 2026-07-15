"""Optional OIDC and LDAP enterprise authentication."""
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
import jwt
from jwt import InvalidTokenError
from ldap3 import Connection, Server
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import User
from backend.db.session import get_db
from backend.utils.auth import create_access_token, hash_password

router = APIRouter(prefix="/api/sso", tags=["enterprise-auth"])


async def authenticate_ldap(username: str, password: str) -> bool:
    if not settings.LDAP_ENABLED or not settings.LDAP_SERVER:
        return False
    server = Server(settings.LDAP_SERVER, use_ssl=settings.LDAP_USE_SSL, connect_timeout=5)
    dn = settings.LDAP_USER_DN_TEMPLATE.format(username=username)
    connection = Connection(server, user=dn, password=password, auto_bind=True, receive_timeout=5)
    connection.unbind()
    return True


@router.get("/config")
async def sso_config():
    return {"oidc": settings.OIDC_ENABLED, "ldap": settings.LDAP_ENABLED}


@router.get("/oidc/login")
async def oidc_login():
    if not settings.OIDC_ENABLED:
        raise HTTPException(404, "OIDC is disabled")
    async with httpx.AsyncClient(timeout=10) as client:
        discovery = (await client.get(settings.OIDC_ISSUER.rstrip("/") + "/.well-known/openid-configuration")).json()
    state = jwt.encode({"nonce": secrets.token_urlsafe(16)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    query = urlencode({
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "state": state,
    })
    return RedirectResponse(discovery["authorization_endpoint"] + "?" + query)


@router.get("/oidc/callback")
async def oidc_callback(code: str = Query(...), state: str = Query(...), db: AsyncSession = Depends(get_db)):
    if not settings.OIDC_ENABLED:
        raise HTTPException(404, "OIDC is disabled")
    try:
        jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except InvalidTokenError as exc:
        raise HTTPException(400, "Invalid OIDC state") from exc
    async with httpx.AsyncClient(timeout=15) as client:
        discovery = (await client.get(settings.OIDC_ISSUER.rstrip("/") + "/.well-known/openid-configuration")).json()
        token = (await client.post(discovery["token_endpoint"], data={
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": settings.OIDC_REDIRECT_URI,
            "client_id": settings.OIDC_CLIENT_ID,
            "client_secret": settings.OIDC_CLIENT_SECRET,
        })).json()
        userinfo = (await client.get(discovery["userinfo_endpoint"], headers={"Authorization": f"Bearer {token['access_token']}"})).json()
    username = str(userinfo.get("preferred_username") or userinfo.get("email") or userinfo["sub"])[:64]
    user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if not user:
        user = User(username=username, password=hash_password(secrets.token_urlsafe(32)), display_name=userinfo.get("name", username), email=userinfo.get("email", ""), role="user")
        db.add(user)
        await db.flush()
    access_token = create_access_token(username, user.role)
    return RedirectResponse(f"/login?token={access_token}&role={user.role}")
