"""Small, explicit role/permission policy used by API dependencies."""
from collections.abc import Callable

from fastapi import Depends, HTTPException

from backend.utils.auth import get_current_user

ROLE_PERMISSIONS = {
    "admin": {"*"},
    "editor": {"documents.read", "documents.write", "documents.delete", "chat.use", "evaluation.run"},
    "viewer": {"documents.read", "chat.use"},
    "user": {"documents.read", "documents.write", "chat.use"},
}


def has_permission(role: str, permission: str) -> bool:
    permissions = ROLE_PERMISSIONS.get(role, set())
    return "*" in permissions or permission in permissions


def require_permission(permission: str) -> Callable:
    async def dependency(user: dict = Depends(get_current_user)) -> dict:
        if not has_permission(user.get("role", ""), permission):
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return user
    return dependency