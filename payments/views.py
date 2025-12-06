from decimal import Decimal
from datetime import datetime
from .forms import PaymentForm
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from collections import defaultdict
from .models import Payment
from customers.models import Customer
from invoices.models import Invoice, InvoiceItem
import csv
from django.utils import timezone
from customers.models import Customer
from products.models import Product
from invoices.models import Invoice
from payments.models import Payment
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Payment
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from invoices.models import InvoiceItem
from django.db.models import Sum
from django.db.models.functions import Coalesce

def dashboard(request):
    """
    Simple home dashboard – counts & total sales.
    """
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()
    total_invoices = Invoice.objects.count()

    total_sales = Invoice.objects.aggregate(
        total=Coalesce(
            Sum("total_amount"),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )["total"]

    context = {
        "total_customers": total_customers,
        "total_products": total_products,
        "total_invoices": total_invoices,
        "total_sales": total_sales,
    }
    return render(request, "dashboard.html", context)



def payment_list(request):
    payments = Payment.objects.select_related("invoice", "invoice__customer").order_by(
        "-date", "-id"
    )
    return render(request, "payments/payment_list.html", {"payments": payments})

def payment_add(request):
    """
    Add Payment page (/payments/add/)
    """
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("payment_list")
    else:
        form = PaymentForm()

    return render(
        request,
        "payments/payment_form.html",
        {"form": form, "title": "Add Payment"},
    )

def payment_edit(request, pk):
    payment = get_object_or_404(Payment, pk=pk)

    if request.method == "POST":
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            return redirect("payment_list")
    else:
        form = PaymentForm(instance=payment)
    return render(request, "payments/payment_form.html", {"form": form})

def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == "POST":
        payment.delete()
        return redirect("payment_list")
    return render(
        request,
        "payments/payment_confirm_delete.html",
        {"payment": payment},
    )

def payment_report(request):
    """
    Simple payments report with date filter and total amount.
    """
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    payments = Payment.objects.select_related("invoice", "invoice__customer")

    if date_from:
        items = items.filter(date__gte=date_from)
    if date_to:
        items = items.filter(date__lte=date_to)

    total_amount = (
        payments.aggregate(total=Sum("amount"))["total"] or 0
    )

    context = {
        "payments": payments,
        "total_amount": total_amount,
        "date_from": date_from,
        "date_to": date_to,
    }
    return render(request, "payments/payment_report.html", context)

# payments/views.py

def product_report(request):
    date_from = request.GET.get("date_from")  # yyyy-mm-dd
    date_to = request.GET.get("date_to")

    # All invoice items with product + invoice joined
    items = InvoiceItem.objects.select_related("product", "invoice")

    # Date filter (based on invoice.date)
    if date_from:
        items = items.filter(invoice_date_gte=date_from)
    if date_to:
        items = items.filter(invoice_date_lte=date_to)

    # Group by product and calculate:
    #   total_quantity = Sum of quantity
    #   total_amount   = Sum(quantity * unit_price)
    product_summary = (
        items.values("product_id", "product_name")
        .annotate(
            total_quantity=Sum("quantity"),
            total_amount=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_price"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            ),
        )
        .order_by("product__name")
    )

    context = {
        "products": product_summary,
        "date_from": date_from,
        "date_to": date_to,
    }
    return render(request, "payments/product_report.html", context)


def product_report_csv(request):
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    items = InvoiceItem.objects.select_related("product", "invoice")

    if date_from:
        items = items.filter(invoice_date_gte=date_from)
    if date_to:
        items = items.filter(invoice_date_lte=date_to)

    product_summary = (
        items.values("product_id", "product_name")
        .annotate(
            total_quantity=Sum("quantity"),
            total_amount=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_price"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            ),
        )
        .order_by("product__name")
    )

    # ---- create CSV response ----
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="product_report.csv"'

    import csv

    writer = csv.writer(response)
    # header
    writer.writerow(["Product", "Total Quantity", "Total Amount (₹)"])

    # data rows
    for row in product_summary:
        writer.writerow([
            row["product__name"],
            row["total_quantity"],
            row["total_amount"],
        ])
        return response

def invoice_report(request):
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    invoices = Invoice.objects.select_related("customer")
    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)

    # amount_paid = sum of successful payments
    invoices = invoices.annotate(
        amount_paid=Coalesce(
            Sum(
                "payments__amount",
                filter=Q(payments__status="paid"),
            ),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    invoices = invoices.annotate(
        balance=ExpressionWrapper(
            F("total_amount") - F("amount_paid"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    totals = invoices.aggregate(
        total_invoices=Coalesce(
            Sum("total_amount"),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        total_paid=Coalesce(
            Sum("amount_paid"),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        total_balance=Coalesce(
            Sum("balance"),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    )

    context = {
        "invoices": invoices.order_by("-date", "-id"),
        "date_from": date_from,
        "date_to": date_to,
        "totals": totals,
    }
    return render(request, "payments/invoice_report.html", context)


def invoice_report_csv(request):
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    invoices = Invoice.objects.select_related("customer")

    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)

    invoices = invoices.annotate(
        amount_paid=Coalesce(
            Sum(
                "payments__amount",
                filter=Q(payments__status="paid"),
            ),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    invoices = invoices.annotate(
        balance=ExpressionWrapper(
            F("total_amount") - F("amount_paid"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    # ---- CSV response ----
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="invoice_report.csv"'

    import csv

    writer = csv.writer(response)
    writer.writerow(
        ["Invoice ID", "Date", "Customer", "Total (₹)", "Paid (₹)", "Balance (₹)", "Status"]
    )

    for inv in invoices.order_by("-date", "-id"):
        writer.writerow(
            [
                inv.id,
                inv.date.strftime("%Y-%m-%d"),
                inv.customer.name,
                inv.total_amount,
                inv.amount_paid,
                inv.balance,
                inv.get_status_display(),
            ]
        )

    return response

def outstanding_report(request):
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    invoices = Invoice.objects.select_related("customer")

    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)

    # amount_paid = sum of successful payments
    invoices = invoices.annotate(
        amount_paid=Coalesce(
            Sum(
                "payments__amount",
                filter=Q(payments__status="paid"),
            ),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    invoices = invoices.annotate(
        balance=ExpressionWrapper(
            F("total_amount") - F("amount_paid"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    # Only invoices where some balance is pending
    invoices = invoices.filter(balance__gt=0)

    totals = invoices.aggregate(
        total_invoices=Coalesce(
            Sum("total_amount"),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        total_paid=Coalesce(
            Sum("amount_paid"),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        total_balance=Coalesce(
            Sum("balance"),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    )

    context = {
        "invoices": invoices.order_by("-date", "-id"),
        "date_from": date_from,
        "date_to": date_to,
        "totals": totals,
    }
    return render(request, "payments/outstanding_report.html", context)

# outstanding report
def outstanding_report_csv(request):
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    invoices = Invoice.objects.select_related("customer")

    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)

    invoices = invoices.annotate(
        amount_paid=Coalesce(
            Sum(
                "payments__amount",
                filter=Q(payments__status="paid"),
            ),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    invoices = invoices.annotate(
        balance=ExpressionWrapper(
            F("total_amount") - F("amount_paid"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    ).filter(balance__gt=0)

    # ---- CSV response ----
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename=\"outstanding_report.csv\"'

    import csv

    writer = csv.writer(response)
    writer.writerow(
        ["Invoice ID", "Date", "Customer", "Total (₹)", "Paid (₹)", "Balance (₹)", "Status"]
    )

    for inv in invoices.order_by("-date", "-id"):
        writer.writerow(
            [
                inv.id,
                inv.date.strftime("%Y-%m-%d"),
                inv.customer.name,
                inv.total_amount,
                inv.amount_paid,
                inv.balance,
                inv.get_status_display(),
            ]
        )

    return response

def payment_report(request):
    """
    Payments report – list + date filter + total amount.
    """
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    payments = Payment.objects.select_related("invoice", "invoice__customer")

    if date_from:
        payments = payments.filter(date__gte=date_from)
    if date_to:
        payments = payments.filter(date__lte=date_to)

    total_amount = payments.aggregate(total=Sum("amount"))["total"] or 0

    context = {
        "payments": payments.order_by("-date", "-id"),
        "total_amount": total_amount,
        "date_from": date_from,
        "date_to": date_to,
    }
    return render(request, "payments/payment_report.html", context)


def payment_report_csv(request):
    """
    Same data as payment_report but as CSV download.
    """
    import csv

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    payments = Payment.objects.select_related("invoice", "invoice__customer")

    if date_from:
        payments = payments.filter(date__gte=date_from)
    if date_to:
        payments = payments.filter(date__lte=date_to)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename=\"payment_report.csv\"'

    writer = csv.writer(response)
    # header
    writer.writerow(["Date", "Invoice ID", "Customer", "Method", "Status", "Amount (₹)"])

    for p in payments.order_by("-date", "-id"):
        invoice_id = p.invoice.id if p.invoice_id else ""
        customer_name = (
            p.invoice.customer.name if p.invoice_id and hasattr(p.invoice, "customer") else ""
        )

        writer.writerow(
            [
                p.date.strftime("%Y-%m-%d"),
                invoice_id,
                customer_name,
                p.get_method_display(),
                p.get_status_display(),
                p.amount,
            ]
        )

    return response