"""URL routing for the core application."""

from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("cabinet/", views.CabinetView.as_view(), name="cabinet"),
    path("login/", views.CabinetLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
