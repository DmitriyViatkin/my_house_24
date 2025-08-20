"""URL routing for the core application."""

from django.urls import path

from . import view_ajax
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
    path("house/add_house", views.HouseAddView.as_view(), name="add_house"),
    path(
        "house/update_house/<int:pk>/",
        views.HouseUpdateView.as_view(),
        name="update_house",
    ),
    path(
        "house/delete_house/<int:pk>/",
        views.HouseDeleteView.as_view(),
        name="delete_house",
    ),
    # 6. message
    path("message", views.MessagesView.as_view(), name="message"),
    # 7. ticket
    path("ticket", views.TicketView.as_view(), name="ticket"),
    # 8. users
    path("users", views.UsersView.as_view(), name="users"),
    path("users/user_create", views.CreateOwnerFlat.as_view(), name="user_create"),
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
    path("tariff/", views.TariffServiceFormView.as_view(), name="new_tariff"),
    path(
        "tariff/delete/<int:pk>/",
        views.TariffDeleteView.as_view(),
        name="delete_tariff",
    ),
    path(
        "tariff/update/<int:pk>/",
        views.TariffUpdateView.as_view(),
        name="update_tariff",
    ),
    path("tariff/copy<int:pk>/", views.TariffCopyView.as_view(), name="copy_tariff"),
    # 16 .website/ role
    path("role", views.RoleView.as_view(), name="role"),
    # 17 .website/ user-admin
    path("user-admin", views.UserAdminView.as_view(), name="user-admin"),
    path(
        "user_list_ajax",
        view_ajax.UserAjaxDatatableView.as_view(),
        name="user_list_ajax",
    ),
    path("create_staff", views.UserCreateStaff.as_view(), name="create_staff"),
    path("user_update/<int:pk>/", views.UserUpdateStaff.as_view(), name="user_update"),
    path("user_delete/<int:pk>/", views.UserDeleteStaff.as_view(), name="user_delete"),
    # 18.website/ payment-articles
    path("paymentd_detail/", views.PaymentDetailView.as_view(), name="payment_detail"),
    path(
        "payment-articles/",
        views.PaymentArticlesView.as_view(),
        name="payment-articles",
    ),
    path(
        "payment-articles/create/",
        views.CreatePaymentArticlesView.as_view(),
        name="payment-articles-create",
    ),
    path(
        "edit_payment_article/<int:pk>/",
        views.EditPaymentArticlesView.as_view(),
        name="edit_payment_article",
    ),
    path(
        "delete_payment_article/<int:pk>/",
        views.PaymentArticlesDeleteView.as_view(),
        name="delete_payment_article",
    ),
    # 19. invoice
    path("invoice", views.InvoiceView.as_view(), name="invoice"),
    # 21. account
    path("account", views.PersonalaccountView.as_view(), name="account"),
    # 22
    path("login/admin/", views.AdminLoginView.as_view(), name="admin_login"),
]
