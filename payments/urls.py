# payments/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ---------- Payments CRUD ----------
    path("", views.payment_list, name="payment_list"),
    path("add/", views.payment_create, name="payment_create"),
    path("edit/<int:pk>/", views.payment_edit, name="payment_edit"),
    path("delete/<int:pk>/", views.payment_delete, name="payment_delete"),

    # ---- Customer report ----
    path("reports/customers/", views.customer_report, name="customer_report"),
    path("reports/customers/csv/", views.customer_report_csv, name="customer_report_csv"),

    # ---------- Payments Report ----------
    path("reports/", views.payment_report, name="payment_report"),
    path("reports/csv/", views.payment_report_csv, name="payment-report-csv"),

    # ---------- Monthly Report ----------
    path("reports/monthly/", views.monthly_report, name="monthly_report"),
    path("reports/monthly/csv/", views.monthly_report_csv, name="monthly_report_csv"),


    # ---------- Product-wise Report ----------
    path("reports/products/", views.product_report, name="product_report"),
    path("reports/products/csv/", views.product_report_csv, name="product-report-csv"),

    # ---------- Invoice Report ----------
# Invoice wise report
    path("reports/invoices/", views.invoice_report, name="invoice_report"),
    path("reports/invoices/csv/", views.invoice_report_csv, name="invoice_report_csv"),

    # ---------- Outstanding Report ----------
   path("reports/outstanding/", views.outstanding_report, name="outstanding_report"),
   path("reports/outstanding/csv/", views.outstanding_report_csv, name="outstanding_report_csv"),

    # ---------- customer summary Report ---------
     path("reports/customer-summary/", views.customer_summary_report, name="customer_summary_report"),
     path("reports/customer-summary/csv/", views.customer_summary_csv, name="customer_summary_csv",),

]
