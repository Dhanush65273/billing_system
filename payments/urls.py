# payments/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ---------- Payments CRUD ----------
    path("", views.payment_list, name="payment_list"),
    path("add/", views.payment_add, name="payment_add"),
    path("edit/<int:pk>/", views.payment_edit, name="payment_edit"),
    path("delete/<int:pk>/", views.payment_delete, name="payment_delete"),

    # ---------- Payments Report ----------
    path("reports/", views.payment_report, name="payment_report"),
    path("reports/csv/", views.payment_report_csv, name="payment-report-csv"),

    # ---------- Product-wise Report ----------
    path("reports/products/", views.product_report, name="product_report"),
    path("reports/products/csv/", views.product_report_csv, name="product-report-csv"),

    # ---------- Invoice Report ----------
    path("reports/invoices/", views.invoice_report, name="invoice_report"),
    path("reports/invoices/csv/", views.invoice_report_csv, name="invoice-report-csv"),

    # ---------- Outstanding Report ----------
    path("reports/outstanding/", views.outstanding_report, name="outstanding_report"),
    path("reports/outstanding/csv/", views.outstanding_report_csv, name="outstanding-report-csv"),
]