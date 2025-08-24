"""URL routing for the core application."""

from django.urls import path

from . import views

urlpatterns = [
    path("cabinet/", views.CabinetView.as_view(), name="cabinet"),
]
