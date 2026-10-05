"""Creation helpers for email-based users."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from apps.auths.models import User


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email: str) -> str:
        return super().normalize_email(email.strip()).lower()

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        if not email or not email.strip():
            raise ValueError("An email address is required.")
        for name in ("first_name", "last_name"):
            if not extra_fields.get(name, "").strip():
                raise ValueError(f"{name} is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        for flag in ("is_staff", "is_superuser", "is_active"):
            extra_fields.setdefault(flag, True)
            if extra_fields[flag] is not True:
                raise ValueError(f"Superuser must have {flag}=True.")
        if not password:
            raise ValueError("Superuser must have a password.")
        return self.create_user(email, password, **extra_fields)
