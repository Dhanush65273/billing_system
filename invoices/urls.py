from django.urls import path
from . import views

urlpatterns = [
    # /invoices/  → list
    path("", views.invoice_list, name="invoice_list"),

    # /invoices/add/  → create
    path("add/", views.invoice_create, name="invoice_create"),

    # /invoices/5/  → detail
    path("<int:pk>/", views.invoice_detail, name="invoice_detail"),

    path("edit/<int:pk>/", views.invoice_edit, name="invoice_edit"),

    # /invoices/5/delete/  → delete confirm + post
    path("<int:pk>/delete/", views.invoice_delete, name="invoice_delete"),

    path("<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
]
