"""URL routing for the core application."""

from django.urls import path

from . import view_ajax
from . import views

app_name = "admin"

urlpatterns = [
    # 1. Statistic
    path("dashboard", views.StatisticView.as_view(), name="dashboard"),
    # 2. flat
    path("flat/index", views.ApartmentView.as_view(), name="flat"),
    path("flath_ajax", view_ajax.FlathAjax.as_view(), name="flath_ajax"),
    path("flat/add_flat/", views.AddApartmentView.as_view(), name="add_flat"),
    path(
        "flat/update/<int:pk>/", views.UpdateApartmentView.as_view(), name="update_flat"
    ),
    path(
        "flat/delete/<int:pk>/", views.DeleteApartmentView.as_view(), name="delete_flat"
    ),
    path("card_flat/<int:pk>/", views.ApartmentDetailView.as_view(), name="card_flat"),
    path("send-invitation/", views.SendInvitation.as_view(), name="send_invitation"),
    # 3. cashbox
    path("cashbox", views.CashboxView.as_view(), name="cashbox"),
    path(
        "cashbox/receipt_statement/",
        views.ReceiptStatementView.as_view(),
        name="receipt_statement",
    ),
path(
    "cashbox/receipt_statement/<int:pk>/",
    views.ReceiptStatementPcView.as_view(),
    name="receipt_statement_pc",
),
    path(
        "cashbox/update_receipt_statement/<int:pk>/",
        views.UpdateReceiptStatementView.as_view(),
        name="update_receipt_statement",
    ),
    path(
        "cashbox/expense_report",
        views.ExpenseReportView.as_view(),
        name="expense_report",
    ),
    path(
        "cashbox/update_expense_report/<int:pk>",
        views.UpdateExpenseReportView.as_view(),
        name="update_expense_report",
    ),
    path("cashbox_list", view_ajax.CashBoxListAjax.as_view(), name="cashbox_list"),
    path("export/cash_box_list/", views.export_cash_box_to_excel, name="cash_box_list"),
    path(
        "admin/export/export_user_cash_box/<int:cashbox_id>/",
        views.export_user_cash_box_to_excel,
        name="export_user_cash_box",
    ),
    # ToDo Coopy  expense
    path(
        "cashbox/expense_report/<int:pk>/copy/",
        views.ExpenseReportCopyView.as_view(),
        name="expense_report_copy",
    ),
    path(
        "cashbox/receipt_statement_copy/<int:pk>/copy/",
        views.ReceiptStatementCopyView.as_view(),
        name="receipt_statement_copy",
    ),
    path(
        "cashbox/cashbox_card/<int:pk>/",
        views.CardCashBoxView.as_view(),
        name="cashbox_card",
    ),
    path(
        "cashbox/cashbox_delete/<int:pk>/delete/",
        views.CashBoxDeleteView.as_view(),
        name="cashbox_delete",
    ),
    # 4. counters
    path("counters_list", views.CounterView.as_view(), name="counters_list"),
    path("counters/counters_add", views.AddCounterView.as_view(), name="counters_add"),
    path(
        "admin/counters/update/<int:pk>/",
        views.UpdateCounterView.as_view(),
        name="counters_update",
    ),
    path(
        "admin/counters/update/",
        views.UpdateCounterView.as_view(),
        name="counters_add_new",
    ),
    path(
        "counters/counters/<int:apartment_id>/",
        views.CounterlistView.as_view(),
        name="counters",
    ),
    path(
        "counters/counters2/<int:apartment_id>/<int:service_id>",
        views.CounterlistView.as_view(),
        name="counters2",
    ),
    path(
        "counters/card_counter/<int:pk>/",
        views.CardCounterView.as_view(),
        name="card_counter",
    ),
    path("counters_ajax", view_ajax.CounterAjax.as_view(), name="counters_ajax"),
    path("counter_ajax", view_ajax.CounteerListAjax.as_view(), name="counter_ajax"),
    path(
        "counter_ajax_items",
        view_ajax.InvoiceCounterAjax.as_view(),
        name="counter_ajax_items",
    ),
    path(
        "invoice/tariff_service_info/",
        views.get_tariff_service_info,
        name="get_tariff_service_info",
    ),
    path(
        "get_apartment_counters/<int:apartment_id>/",
        views.get_apartment_counters,
        name="get_apartment_counters",
    ),
    path(
        "get_tariff_services/<int:tariff_id>/",
        views.get_tariff_services,
        name="get_tariff_services",
    ),
    path(
        "invoice/<int:invoice_id>/download/",
        views.download_invoice_pdf,
        name="download_invoice_pdf",
    ),
    path(
        "admin/invoice/print/<int:invoice_id>/",
        views.send_invoice_email_view,
        name="invoice_send_email",
    ),
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
    path("house_card/<int:pk>/", views.CardHouseView.as_view(), name="house_card"),
    # 6. message
    path("message", views.MessagesView.as_view(), name="message"),
    path(
        "message_detail/<int:pk>",
        views.MessagesDetailView.as_view(),
        name="message_detail",
    ),
    path(
        "message/<int:pk>/delete/",
        views.MessagesDeleteView.as_view(),
        name="message_delete",
    ),
    path(
        "messages/delete-many/",
        views.MessageDeleteManyView.as_view(),
        name="message_delete_many",
    ),
    path("send-message/", views.SendMessageView.as_view(), name="send_message"),
    # ToDo TaskList AjaxDataTable
    # 7. ticket
    path("ticket", views.TicketView.as_view(), name="ticket"),
    path("task_list_ajax", view_ajax.TicketListAjax.as_view(), name="task_list_ajax"),
    path("ticket/add_task", views.AddTicketsAdminView.as_view(), name="add_task"),
    path("card_task/<int:pk>/", views.CardTaskView.as_view(), name="card_task"),
    path(
        "ticket/<int:pk>/edit/",
        views.EditTicketsAdminView.as_view(),
        name="edit_ticket",
    ),
    # 8. users
    path("owners", views.UsersView.as_view(), name="owners"),
    path("owner_create", views.CreateOwnerFlat.as_view(), name="owner_create"),
    path(
        "owner_update/<int:pk>/", views.UpdateOwnerFlat.as_view(), name="owner_update"
    ),
    path(
        "card_user/send_message/<int:user_id>/",
        views.UserSendMessageView.as_view(),
        name="user_send_message",
    ),
    path("card_user/<int:pk>/", views.CardUserView.as_view(), name="card_user"),
    # 9.website/home
    path("website/home", views.HomeView.as_view(), name="home"),
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
    path("card_tariff/<int:pk>/", views.CardTariffView.as_view(), name="card_tariff"),
    # 16 .website/ role
    path("role", views.RoleView.as_view(), name="role"),
    # 17 .website/ user-admin
    path("user-admin", views.UserAdminView.as_view(), name="user-admin"),
    path(
        "user_list_ajax",
        view_ajax.UserAjaxDatatableView.as_view(),
        name="user_list_ajax",
    ),
    path(
        "owner_list_ajax",
        view_ajax.OwnerAjaxDatetableView.as_view(),
        name="owner_list_ajax",
    ),
    path("create_staff", views.UserCreateStaff.as_view(), name="create_staff"),
    path("user_update/<int:pk>/", views.UserUpdateStaff.as_view(), name="user_update"),
    path("user_delete/<int:pk>/", views.UserDeleteStaff.as_view(), name="user_delete"),
    path("card_staff/<int:pk>/", views.CardStaffView.as_view(), name="card_staff"),
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
    # ToDo 19. invoice
    path("invoice", views.InvoiceView.as_view(), name="invoice"),
    path("create_invoice", views.CreateInvoiceView.as_view(), name="create_invoice"),

path(
    "create_invoice_pc/<int:apartment_id>/",
    views.CreateInvoicePcView.as_view(),
    name="create_invoice_pc",
),
    path(
        "invoice/<int:pk>/edit/",
        views.UpdateInvoiceView.as_view(),
        name="invoice_update",
    ),
    path("items_list", view_ajax.InvoiceBoxListAjax.as_view(), name="items_list"),
    path(
        "invoice_card/<int:pk>", views.InvoiceDetailView.as_view(), name="invoice_card"
    ),
    path(
        "invoice/<int:pk>/delete/",
        views.DeleteInvoiceView.as_view(),
        name="invoice-delete",
    ),
    path(
        "invoice/<int:invoice_id>/template_list",
        views.TemplateListView.as_view(),
        name="template_list",
    ),
    path(
        "invoice/template_list/add_template",
        views.AddTemplateView.as_view(),
        name="add_template",
    ),
    path(
        "invoice/<int:invoice_id>/download/excel/",
        views.download_invoice,
        name="download_invoice_excel",
    ),
    # 21. account
    path("account", views.PersonalaccountView.as_view(), name="account"),
    path(
        "ajax_datatable_personal_account",
        view_ajax.PersonalAccountList.as_view(),
        name="ajax_datatable_personal_account",
    ),
    path(
        "account/add_account",
        views.AddPersonalAccountView.as_view(),
        name="add_account",
    ),
    path(
        "account/<int:pk>/edit/",
        views.UpdatePersonalAccountView.as_view(),
        name="update_account",
    ),
    path(
        "account/<int:pk>/delete/",
        views.DeletePersonalAccountView.as_view(),
        name="delete_account",
    ),
    path(
        "account/card/<int:pk>/", views.PersonalAccountDetailView.as_view(), name="card"
    ),
    # 22
    path("export/accounts/", views.export_accounts_view, name="export_accounts"),
    path(
        "ajax/get-sections/", views.get_sections_by_house, name="get_sections_by_house"
    ),
    path(
        "ajax/get-apartments/",
        views.get_apartments_by_section,
        name="get_apartments_by_section",
    ),
    path(
        "ajax/get-apartment-owner/",
        views.get_apartment_owner,
        name="get_apartment_owner",
    ),
    path("ajax_datateble/house", view_ajax.HouseListAjax.as_view(), name="house_list"),
    path(
        "admin/flat/get-sections/",
        views.get_sections_by_house2,
        name="get_sections_by_house2",
    ),
    path("admin/flat/get-floors/", views.get_floors, name="get_floors"),
    path(
        "admin/flat/get-user-account/", views.get_user_account, name="get_user_account"
    ),
    path("send", views.trigger_mass_email, name="send"),
    path(
        "ajax/get-user-apartments/",
        views.get_user_apartments,
        name="get_user_apartments",
    ),
    path("ajax/get-house-workers/", views.get_house_workers, name="get_house_workers"),
    path(
        "user-autocomplete/", views.UserAutocomplete.as_view(), name="user-autocomplete"
    ),
    path(
        "personal-account-autocomplete/",
        views.PersonalAccountAutocomplete.as_view(),
        name="personal-account-autocomplete",
    ),
    path(
        "manager-autocomplete/",
        views.ManagerAutocomplete.as_view(),
        name="manager-autocomplete",
    ),
    path(
        "house-autocomplete/",
        views.HouseAutocomplete.as_view(),
        name="house-autocomplete",
    ),
    path(
        "section-autocomplete/",
        views.SectionAutocomplete.as_view(),
        name="section-autocomplete",
    ),
    path(
        "floor-autocomplete/",
        views.FloorAutocomplete.as_view(),
        name="floor-autocomplete",
    ),
    path(
        "flat-autocomplete/",
        views.ApartmentAutocomplete.as_view(),
        name="flat-autocomplete",
    ),
    path(
        "tariff-autocomplete/",
        views.TariffAutocomplete.as_view(),
        name="tariff-autocomplete",
    ),
    path(
        "account-autocomplete/",
        views.AccountAutocomplete.as_view(),
        name="account-autocomplete",
    ),
    path("ajax/get-owner/", views.get_owner, name="get_owner"),
    path("ajax/get-sections/", views.get_sections_ajax, name="get_sections_ajax"),
    path("ajax/get-apartments/", views.get_apartments_ajax, name="get_apartments_ajax"),
    path(
        "ajax/get-apartment-owner/",
        views.get_apartment_owner_ajax,
        name="get_apartment_owner_ajax",
    ),
path("ajax/check-unit-delete/", views.check_unit_delete, name="check_unit_delete"),
]
