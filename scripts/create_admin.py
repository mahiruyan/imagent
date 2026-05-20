from __future__ import annotations

import argparse
import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def create_admin(username: str, password: str) -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(User).where(User.username == username))
        if existing:
            existing.password_hash = hash_password(password)
            existing.role = "admin"
            existing.is_active = True
            action = "updated"
        else:
            session.add(
                User(
                    username=username,
                    password_hash=hash_password(password),
                    role="admin",
                    is_active=True,
                )
            )
            action = "created"
        await session.commit()
    print(f"Admin user {action}: {username}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Create or update an admin user.")
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"))
    args = parser.parse_args()
    if not args.username or not args.password:
        raise SystemExit(
            "Provide --username/--password or set ADMIN_USERNAME and ADMIN_PASSWORD."
        )
    asyncio.run(create_admin(args.username, args.password))


if __name__ == "__main__":
    main()
