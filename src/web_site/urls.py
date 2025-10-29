"""URL configuration for the web_site application."""

from django.urls import path

from . import views

urlpatterns = [
    # 1. Main
    path("main", views.MainPageView.as_view(), name="main"),
    path("about", views.AboutPageView.as_view(), name="about"),
    path("services", views.ServicePageView.as_view(), name="services"),
    path("tariffs", views.TariffsPageView.as_view(), name="tariffs"),
    path("contact", views.ContactPageView.as_view(), name="contact"),
]
