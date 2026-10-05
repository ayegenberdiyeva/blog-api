"""Admin forms compatible with AbstractBaseUser and email login."""

from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from apps.auths.models import User


class AdminUserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class AdminUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"
