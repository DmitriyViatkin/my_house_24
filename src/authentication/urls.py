"""URL configuration for the authentication app."""

from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views

urlpatterns = [
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page=reverse_lazy("login")),
        name="logout",
    ),
    path("", views.CustomLoginView.as_view(), name="login"),
    path("registration", views.RegistrationView.as_view(), name="registration"),

    # --- Восстановление пароля ---
    path(
        "password_reset/",
        views.PasswordResetView.as_view(

        ),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        views.PasswordResetDoneView.as_view(

        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(

        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        views.PasswordResetCompleteView.as_view(

        ),
        name="password_reset_complete",
    ),
    # --- Прочие маршруты ---
    path("private_policy", views.PrivatePolicy.as_view(), name="private_policy"),
]