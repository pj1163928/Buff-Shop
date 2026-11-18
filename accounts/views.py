from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import EmailAuthenticationForm, SignUpForm


class SignUpView(CreateView):
    """Create a customer account, then log the new customer straight in."""

    form_class = SignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("catalog:index")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object, backend="django.contrib.auth.backends.ModelBackend")
        # Same safe default as login without "Remember me": end at browser close.
        self.request.session.set_expiry(0)
        messages.success(
            self.request, f"Welcome to the Buff Shop, {self.object.first_name}! You're signed up."
        )
        return response


class LoginView(DjangoLoginView):
    """Email login. "Remember me" keeps the session for two weeks."""

    form_class = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        else:
            self.request.session.set_expiry(0)
        return response


class LogoutView(DjangoLogoutView):
    """Log out (POST only) and say so."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have been logged out.")
        return response
