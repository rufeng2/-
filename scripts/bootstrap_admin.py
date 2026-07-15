"""Create the initial local administrator as an explicit deployment action."""
import asyncio

from sqlalchemy import select

from backend.config import settings
from backend.db.models import User
from backend.db.session import AsyncSessionLocal
from backend.security.production_config import assert_production_settings
from backend.utils.auth import hash_password


async def bootstrap() -> None:
    assert_production_settings(settings)
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))).scalar_one_or_none()
        if existing:
            print("Administrator already exists")
            return
        db.add(User(
            username=settings.ADMIN_USERNAME,
            password=hash_password(settings.ADMIN_PASSWORD),
            display_name="System Administrator",
            role="admin",
            must_change_password=True,
        ))
        await db.commit()
        print("Administrator created; password rotation is required at first login")


if __name__ == "__main__":
    asyncio.run(bootstrap())
