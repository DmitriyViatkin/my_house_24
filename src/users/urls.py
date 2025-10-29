"""URL patterns for the users application."""

from django.urls import path

from . import views

urlpatterns = [
    path(
        "cabinet/statistic/<int:pk>/", views.StatisticView.as_view(), name="statistic"
    ),
    path("cabinet/", views.CabinetView.as_view(), name="cabinet"),
    path("cabinet/tariff/index/<int:pk>/", views.TariffView.as_view(), name="tariff"),
    path(
        "cabinet/invoices/<int:pk>/",
        views.InvoiceListView.as_view(),
        name="invoice_list",
    ),
    path(
        "cabinet/invoice/<int:pk>/",
        views.InvoiceDetailView.as_view(),
        name="invoice_detail",
    ),
    path(
        "cabinet/invoice/print/<int:pk>/",
        views.InvoicePrintView.as_view(),
        name="invoice_print",
    ),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/tickets_list/", views.ListTicketsView.as_view(), name="tickets_list"),
    path("tickets_list/add_ticket/", views.AddTicketsView.as_view(), name="add_ticket"),
    path(
        "cabinet/user/update/<int:pk>/",
        views.UpdateProfile.as_view(),
        name="update_profile",
    ),
    path("message", views.MessageView.as_view(), name="message"),
    path(
        "message_detail/<int:pk>",
        views.MessagesDetailView.as_view(),
        name="message_detail",
    ),
    path("pay/<int:pk>", views.PayInvoice.as_view(), name="pay"),
    path("pay/step2/<int:pk>/", views.PayInvoiceStep2.as_view(), name="step2"),
]
