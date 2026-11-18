from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    AuthenticationForm,
    BaseUserCreationForm,
    UserChangeForm,
)

from .models import User, normalize_email


class SignUpForm(BaseUserCreationForm):
    """Customer sign-up: first name, last name, email and password (all required).

    Passwords go through the four default validators in AUTH_PASSWORD_VALIDATORS.
    """

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }
        error_messages = {
            "email": {"unique": "An account with this email already exists. Try logging in."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Start on the first field in reading order, not on email.
        self.fields["email"].widget.attrs.pop("autofocus", None)
        self.fields["first_name"].widget.attrs["autofocus"] = True
        for name in ("password1", "password2"):
            self.fields[name].widget.attrs["autocomplete"] = "new-password"

    def clean_email(self) -> str:
        return normalize_email(self.cleaned_data.get("email"))


class EmailAuthenticationForm(AuthenticationForm):
    """Login by email, plus "Remember me".

    A failed login always shows the same message, whether or not the email
    has an account.
    """

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    remember_me = forms.BooleanField(
        label="Remember me for two weeks",
        required=False,
        help_text="Leave this unticked on a shared computer.",
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "The email or password is incorrect. Please try again.",
    }

    def clean_username(self) -> str:
        return normalize_email(self.cleaned_data.get("username"))


class AdminSignUpForm(AdminUserCreationForm):
    """Django admin's "add user" form for the email-login User."""

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class AdminUserChangeForm(UserChangeForm):
    """Django admin's "change user" form for the email-login User."""

    class Meta:
        model = User
        fields = "__all__"
