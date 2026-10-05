from typing import Any

from rest_framework import status
from rest_framework.test import APITestCase

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.auths.forms import AdminUserChangeForm, AdminUserCreationForm
from apps.auths.models import User

TEST_PASSWORD = "River!Mountain82-Alpine"


class UserManagerTests(TestCase):
    def create_user(self, **overrides: Any) -> User:
        values = {
            "email": "Alice@EXAMPLE.COM",
            "password": TEST_PASSWORD,
            "first_name": "Alice",
            "last_name": "Author",
        }
        values.update(overrides)
        return User.objects.create_user(**values)

    def test_email_is_lowercase_and_password_is_hashed(self) -> None:
        user = self.create_user()
        self.assertEqual(user.email, "alice@example.com")
        self.assertNotEqual(user.password, TEST_PASSWORD)
        self.assertTrue(user.check_password(TEST_PASSWORD))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.get_full_name(), "Alice Author")

    def test_required_identity_fields(self) -> None:
        for field in ("email", "first_name", "last_name"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.create_user(**{field: " "})

    def test_duplicate_email_is_rejected_case_insensitively(self) -> None:
        self.create_user()
        with self.assertRaises(ValidationError):
            self.create_user(email="ALICE@example.com")

    def test_invalid_email_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.create_user(email="not-an-email")

    def test_superuser_flags_and_password(self) -> None:
        user = User.objects.create_superuser(
            email="admin@example.com",
            password=TEST_PASSWORD,
            first_name="Site",
            last_name="Admin",
        )
        self.assertTrue(user.is_staff and user.is_superuser and user.is_active)
        for flag in ("is_staff", "is_superuser", "is_active"):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                User.objects.create_superuser(
                    email="another@example.com",
                    password=TEST_PASSWORD,
                    first_name="Site",
                    last_name="Admin",
                    **{flag: False},
                )
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="missing@example.com", first_name="Site", last_name="Admin"
            )

    def test_admin_creation_and_edit_forms_work_without_username(self) -> None:
        form = AdminUserCreationForm(
            data={
                "email": "ADMINFORM@example.com",
                "first_name": "Form",
                "last_name": "User",
                "password1": TEST_PASSWORD,
                "password2": TEST_PASSWORD,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "adminform@example.com")
        self.assertTrue(user.check_password(TEST_PASSWORD))
        self.assertNotIn("username", AdminUserChangeForm(instance=user).fields)


class AuthenticationAPITests(APITestCase):
    def setUp(self) -> None:
        self.payload = {
            "email": "New@EXAMPLE.COM",
            "first_name": "New",
            "last_name": "User",
            "password": TEST_PASSWORD,
        }

    def test_registration_hashes_password_and_cannot_grant_staff(self) -> None:
        response = self.client.post(
            reverse("auths:register"),
            {
                **self.payload,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        user = User.objects.get(email="new@example.com")
        self.assertTrue(user.check_password(TEST_PASSWORD))
        self.assertFalse(user.is_staff or user.is_superuser)

    def test_duplicate_and_weak_password_registration(self) -> None:
        self.client.post(reverse("auths:register"), self.payload)
        response = self.client.post(
            reverse("auths:register"),
            {
                **self.payload,
                "email": "NEW@example.com",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(
            reverse("auths:register"),
            {
                **self.payload,
                "email": "weak@example.com",
                "password": "123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_email_login_refresh_and_authenticated_request(self) -> None:
        self.client.post(reverse("auths:register"), self.payload)
        response = self.client.post(
            reverse("auths:token"),
            {
                "email": "NEW@example.com",
                "password": TEST_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refresh = self.client.post(
            reverse("auths:token-refresh"),
            {
                "refresh": response.data["refresh"],
            },
        )
        self.assertEqual(refresh.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.data['access']}")
        response = self.client.post(
            reverse("post-list"),
            {
                "title": "JWT post",
                "slug": "jwt-post",
                "body": "Authenticated.",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_bad_password_inactive_user_and_invalid_refresh_rejected(self) -> None:
        user = User.objects.create_user(**self.payload)
        response = self.client.post(
            reverse("auths:token"),
            {
                "email": user.email,
                "password": "incorrect",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        user.is_active = False
        user.save()
        response = self.client.post(
            reverse("auths:token"),
            {
                "email": user.email,
                "password": TEST_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post(
            reverse("auths:token-refresh"), {"refresh": "invalid"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_email_admin_login_and_user_pages(self) -> None:
        user = User.objects.create_superuser(
            email="admin@example.com",
            password=TEST_PASSWORD,
            first_name="Site",
            last_name="Admin",
        )
        self.assertTrue(self.client.login(email=user.email, password=TEST_PASSWORD))
        for name in ("admin:auths_user_add", "admin:auths_user_changelist"):
            self.assertEqual(
                self.client.get(reverse(name)).status_code, status.HTTP_200_OK
            )
