"""Authentication API: local accounts, optional LDAP, registration and token checks."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.enterprise_auth import authenticate_ldap
from backend.config import settings
from backend.db.models import User
from backend.db.session import get_db
from backend.schemas.user import LoginRequest, PasswordChangeRequest, RegisterRequest, TokenResponse, UserInfo
from backend.utils.auth import create_access_token, get_current_user, hash_password, verify_password
from backend.utils.logger import logger

router = APIRouter(prefix="/api", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    username, password = req.username.strip(), req.password
    user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()

    if settings.LDAP_ENABLED:
        try:
            if await authenticate_ldap(username, password):
                if not user:
                    user = User(username=username, password=hash_password(password), display_name=username, role="user")
                    db.add(user)
                    await db.flush()
                return TokenResponse(msg="LDAP login successful", token=create_access_token(username, user.role), role=user.role, username=username)
        except Exception as exc:
            logger.warning(f"LDAP authentication failed for {username}: {exc}")

    if not user or not verify_password(password, user.password):
        return TokenResponse(code=401, msg="Invalid username or password")
    if not user.is_active:
        return TokenResponse(code=403, msg="Account is disabled")
    return TokenResponse(msg="Login successful", token=create_access_token(username, user.role, user.must_change_password), role=user.role, username=username)


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    username, password = req.username.strip(), req.password
    if len(username) < 3:
        return TokenResponse(code=400, msg="Username must contain at least 3 characters")
    if len(password) < 8:
        return TokenResponse(code=400, msg="Password must contain at least 8 characters")
    if (await db.execute(select(User).where(User.username == username))).scalar_one_or_none():
        return TokenResponse(code=400, msg="Username already exists")
    user = User(username=username, password=hash_password(password), display_name=req.display_name or username)
    db.add(user)
    await db.flush()
    logger.info(f"User registered: {username}")
    return TokenResponse(msg="Registration successful", token=create_access_token(username), role="user", username=username)


@router.get("/verify", response_model=TokenResponse)
async def verify_token(user: dict = Depends(get_current_user)):
    return TokenResponse(msg="Token is valid", token="", role=user["role"], username=user["username"])


@router.get("/users/me", response_model=UserInfo)
async def get_my_info(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = (await db.execute(select(User).where(User.username == user["username"]))).scalar_one_or_none()
    if not item:
        return UserInfo()
    return UserInfo(id=str(item.id), username=item.username, display_name=item.display_name, email=item.email, role=item.role, department=str(item.department), is_active=item.is_active)


@router.post("/users/password", response_model=TokenResponse)
async def change_password(req: PasswordChangeRequest, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = (await db.execute(select(User).where(User.username == user["username"]))).scalar_one_or_none()
    if not item or not verify_password(req.current_password, item.password):
        return TokenResponse(code=401, msg="Current password is invalid")
    if req.current_password == req.new_password:
        return TokenResponse(code=400, msg="New password must differ from the current password")
    item.password = hash_password(req.new_password)
    item.must_change_password = False
    await db.flush()
    return TokenResponse(
        msg="Password changed",
        token=create_access_token(item.username, item.role, False),
        role=item.role,
        username=item.username,
    )
