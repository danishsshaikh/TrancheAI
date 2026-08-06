from __future__ import annotations

import os
from uuid import uuid4

from sqlalchemy import select

from app.core.enums import Role
from app.db.session import SessionLocal
from app.models.domain import UserModel
from app.services.security import hash_password


def bootstrap_admin() -> None:
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    full_name = os.environ.get("BOOTSTRAP_ADMIN_NAME", "TrancheAI Administrator")
    if not email or not password:
        raise SystemExit("BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD are required.")
    with SessionLocal() as session:
        existing = session.scalar(select(UserModel).where(UserModel.email == email))
        if existing is not None:
            print(f"Administrator already exists: {email}")
            return
        user = UserModel(id=str(uuid4()), email=email, full_name=full_name, password_hash=hash_password(password), role=Role.ADMINISTRATOR.value)
        session.add(user)
        session.commit()
        print(f"Created Administrator: {email}")


if __name__ == "__main__":
    bootstrap_admin()
