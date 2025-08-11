"""URL routing for the core application."""

from django.urls import path

from . import views

app_name = "admin"

urlpatterns = [
    # 1. Statistic
    path("", views.StatisticView.as_view(), name="dashboard"),
    # 2. flat
    path("flat/index", views.ApartmentView.as_view(), name="flat"),
    # 3. cashbox
    path("cashbox", views.CashboxView.as_view(), name="cashbox"),
    # 4. counters
    path("counters", views.CounterView.as_view(), name="counters"),
    # 5. house
    path("house", views.HouseView.as_view(), name="house"),
    # 6. message
    path("message", views.MessagesView.as_view(), name="message"),
    # 7. ticket
    path("ticket", views.TicketView.as_view(), name="ticket"),
    # 8. users
    path("user", views.UsersView.as_view(), name="users"),
    # 9.website/home
    path("website/home", views.HoumeView.as_view(), name="home"),
    # 10.website/about
    path("website/about", views.AboutView.as_view(), name="about"),
    # 11 .website/services
    path("website/services", views.ServicesView.as_view(), name="services"),
    # 12 .website/tariffs
    path("website/tariffs", views.TariffsView.as_view(), name="tariffs"),
    # 13 .website/contact
    path("website/contact", views.ContactView.as_view(), name="contact"),
    # 14 .website/ service
    path("service", views.ServiceView.as_view(), name="service"),
    # 15 .website/ tariff
    path("tariff", views.TariffView.as_view(), name="tariff"),
    # 16 .website/ role
    path("role", views.RoleView.as_view(), name="role"),
    # 17 .website/ user-admin
    path("user-admin", views.UserAdminView.as_view(), name="user-admin"),
    # 18.website/ payment-articles
    path(
        "payment-articles", views.PaymentArticlesView.as_view(), name="payment-articles"
    ),
    # 19. invoice
    path("invoice", views.InvoiceView.as_view(), name="invoice"),
    # 21. account
    path("account", views.PersonalaccountView.as_view(), name="account"),
    # 22
    path("login/admin/", views.AdminLoginView.as_view(), name="admin_login"),
]
