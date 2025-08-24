"""URL configuration for the authentication app."""

from django.contrib.auth import views as auth_views
from django.urls import path
from django.urls import reverse_lazy

from . import views

urlpatterns = [
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page=reverse_lazy("login")),
        name="logout",
    ),
    path("", views.CustomLoginView.as_view(), name="login"),
]
