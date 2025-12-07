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
from datetime import datetime
from django.db import models
from django.db.models.functions import TruncMonth
from datetime import date
from django.db.models import Sum, Count  

def _parse_date(value):
    """
    '2025-12-07' -> date object.
    Empty / wrong format na None.
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None

def dashboard(request):
    """
    Simple home dashboard - counts & total sales.
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



def product_report(request):
    date_from_str = request.GET.get("date_from")
    date_to_str = request.GET.get("date_to")

    date_from = _parse_date(date_from_str)
    date_to = _parse_date(date_to_str)

    products = Product.objects.all().order_by("name")
    rows = []

    for prod in products:
        items_qs = InvoiceItem.objects.filter(product=prod).select_related("invoice")

        if date_from:
            items_qs = items_qs.filter(invoice_date_gte=date_from)
        if date_to:
            items_qs = items_qs.filter(invoice_date_lte=date_to)

        invoice_ids = items_qs.values_list("invoice_id", flat=True).distinct()
        total_invoices = invoice_ids.count()

        line_total = ExpressionWrapper(
            F("quantity") * F("unit_price"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )

        total_invoice_amount = items_qs.aggregate(
            total=Coalesce(
                Sum(line_total),
                0,
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )["total"]

        total_paid = Payment.objects.filter(
            invoice_id__in=invoice_ids,
            status="paid",
        ).aggregate(
            total=Coalesce(
                Sum("amount"),
                0,
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )["total"]

        # ✅ Always show product, even if 0
        rows.append({
            "product": prod,
            "total_invoices": total_invoices,
            "total_invoice_amount": total_invoice_amount,
            "total_paid": total_paid,
        })

    context = {
        "rows": rows,
        "date_from": date_from_str,
        "date_to": date_to_str,
    }
    return render(request, "payments/product_report.html", context)


def product_report_csv(request):
    date_from_str = request.GET.get("date_from") or ""
    date_to_str = request.GET.get("date_to") or ""

    # "None" -> empty
    if date_from_str == "None":
        date_from_str = ""
    if date_to_str == "None":
        date_to_str = ""

    date_from = _parse_date(date_from_str)
    date_to = _parse_date(date_to_str)

    # Build same rows as product_report view
    products = Product.objects.all().order_by("name")
    rows = []

    line_total = ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )

    for prod in products:
        items_qs = InvoiceItem.objects.filter(product=prod).select_related("invoice")

        if date_from:
            items_qs = items_qs.filter(invoice_date_gte=date_from)
        if date_to:
            items_qs = items_qs.filter(invoice_date_lte=date_to)

        invoice_ids = items_qs.values_list("invoice_id", flat=True).distinct()
        total_invoices = invoice_ids.count()

        total_invoice_amount = items_qs.aggregate(
            total=Coalesce(
                Sum(line_total),
                0,
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )["total"]

        total_paid = Payment.objects.filter(
            invoice_id__in=invoice_ids,
            status="paid",
        ).aggregate(
            total=Coalesce(
                Sum("amount"),
                0,
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )["total"]

        rows.append({
            "product": prod,
            "total_invoices": total_invoices,
            "total_invoice_amount": total_invoice_amount,
            "total_paid": total_paid,
        })

    # Create CSV
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="product_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Product",
        "SKU",
        "Total Invoices",
        "Total Invoice Amount",
        "Total Payments",
    ])

    for row in rows:
        prod = row["product"]
        writer.writerow([
            prod.name,
            getattr(prod, "sku", ""),
            row["total_invoices"],
            row["total_invoice_amount"],
            row["total_paid"],
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

    # ---- per-invoice values ----

    # total_paid = sum of successful payments
    invoices = invoices.annotate(
        total_paid=Coalesce(
            Sum(
                "payments__amount",
                filter=Q(payments__status="paid"),
            ),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    # outstanding = total_amount - total_paid
    invoices = invoices.annotate(
        outstanding=ExpressionWrapper(     # 👈 balance -> outstanding
            F("total_amount") - F("total_paid"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    # ---- overall totals ----

    totals_raw = invoices.aggregate(
        total_invoices=Coalesce(
            Sum("total_amount"),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        total_paid=Coalesce(
            Sum(
                "payments__amount",
                filter=Q(payments__status="paid"),
            ),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    )

    totals = {
        "total_invoices": totals_raw["total_invoices"],
        "total_paid": totals_raw["total_paid"],
        # total balance = invoices – paid
        "total_balance": totals_raw["total_invoices"] - totals_raw["total_paid"],
    }

    context = {
        "invoices": invoices.order_by("-date", "-id"),
        "date_from": date_from,
        "date_to": date_to,
        "totals": totals,
    }
    return render(request, "payments/invoice_report.html", context)


def invoice_report_csv(request):
    date_from_str = request.GET.get("date_from") or ""
    date_to_str = request.GET.get("date_to") or ""

    if date_from_str == "None":
        date_from_str = ""
    if date_to_str == "None":
        date_to_str = ""

    date_from = date_from_str or None
    date_to = date_to_str or None

    invoices = Invoice.objects.select_related("customer")

    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)

    # 🔹 annotation names: total_paid + remaining_balance (NO clash)
    invoices = invoices.annotate(
        total_paid=Coalesce(
            Sum(
                "payments__amount",
                filter=Q(payments__status="paid"),
            ),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    ).annotate(
        remaining_balance=ExpressionWrapper(
            F("total_amount") - F("total_paid"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="invoice_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Invoice ID",
        "Date",
        "Customer",
        "Total Amount",
        "Total Paid",
        "Balance",
        "Status",
    ])

    for inv in invoices.order_by("-date", "-id"):
        writer.writerow([
            inv.id,
            inv.date.strftime("%d-%m-%Y") if inv.date else "",
            inv.customer.name if inv.customer else "",
            inv.total_amount,
            inv.total_paid,            # annotation
            inv.remaining_balance,     # annotation (no property clash)
            inv.get_status_display(),
        ])

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
    Payments report - list + date filter + total amount.
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
    # Get raw strings (can be "None", "", or real date)
    date_from_str = request.GET.get("date_from") or ""
    date_to_str = request.GET.get("date_to") or ""

    # Treat "None" as empty
    if date_from_str == "None":
        date_from_str = ""
    if date_to_str == "None":
        date_to_str = ""

    # If u already have _parse_date helper, use it
    # otherwise just use raw string (YYYY-MM-DD) – DB accepts it
    date_from = date_from_str or None
    date_to = date_to_str or None

    payments = Payment.objects.select_related("invoice__customer")

    if date_from:
        payments = payments.filter(date__gte=date_from)
    if date_to:
        payments = payments.filter(date__lte=date_to)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="payments_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Date", "Invoice ID", "Customer", "Method", "Status", "Amount"])

    for p in payments.order_by("date", "id"):
        writer.writerow([
            p.date.strftime("%d-%m-%Y") if p.date else "",
            p.invoice_id,
            p.invoice.customer.name if p.invoice and p.invoice.customer else "",
            p.get_method_display(),
            p.get_status_display(),
            p.amount,
        ])

    return response

def customer_report(request):
    date_from_str = request.GET.get("date_from")
    date_to_str = request.GET.get("date_to")

    date_from = _parse_date(date_from_str)
    date_to = _parse_date(date_to_str)

    customers = Customer.objects.all().order_by("name")

    rows = []

    for c in customers:
        invoices_qs = Invoice.objects.filter(customer=c)

        # filter by date
        if date_from:
            invoices_qs = invoices_qs.filter(date__gte=date_from)
        if date_to:
            invoices_qs = invoices_qs.filter(date__lte=date_to)

        # 👉 Total invoice count
        total_invoices = invoices_qs.count()

        # 👉 Total invoice amount
        total_invoice_amount = invoices_qs.aggregate(
            total=Coalesce(
                Sum("total_amount"),
                0,
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )["total"]

        # 👉 Total payments made
        total_paid = Payment.objects.filter(
            invoice__in=invoices_qs,
            status="paid",
        ).aggregate(
            total=Coalesce(
                Sum("amount"),
                0,
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )["total"]

        rows.append({
            "customer": c,
            "total_invoices": total_invoices,
            "total_invoice_amount": total_invoice_amount,
            "total_paid": total_paid,
        })

    context = {
        "rows": rows,
        "date_from": date_from_str,
        "date_to": date_to_str,
    }
    return render(request, "payments/customer_report.html", context)


def customer_report_csv(request):
    date_from_str = request.GET.get("date_from") or ""
    date_to_str = request.GET.get("date_to") or ""

    date_from = _parse_date(date_from_str)
    date_to = _parse_date(date_to_str)

    customers = Customer.objects.all().order_by("name")

    rows = []

    for c in customers:
        inv_qs = Invoice.objects.filter(customer=c)
        if date_from:
            inv_qs = inv_qs.filter(date__gte=date_from)
        if date_to:
            inv_qs = inv_qs.filter(date__lte=date_to)

        inv_agg = inv_qs.aggregate(
            total_invoices=Count("id"),
            total_amount=Sum("total_amount"),
        )

        pay_qs = Payment.objects.filter(invoice__customer=c)
        if date_from:
            pay_qs = pay_qs.filter(invoice_date_gte=date_from)
        if date_to:
            pay_qs = pay_qs.filter(invoice_date_lte=date_to)

        total_payments = pay_qs.aggregate(total=Sum("amount"))["total"] or 0

        rows.append({
            "customer": c,
            "total_invoices": inv_agg["total_invoices"] or 0,
            "total_invoice_amount": inv_agg["total_amount"] or 0,
            "total_payments": total_payments,
        })

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=customer_report.csv"
    writer = csv.writer(response)

    writer.writerow([
        "Customer Name",
        "Total Invoices",
        "Total Invoice Amount",
        "Total Payments",
    ])

    for r in rows:
        writer.writerow([
            r["customer"].name,
            r["total_invoices"],
            r["total_invoice_amount"],
            r["total_payments"],
        ])

    return response

def monthly_report(request):
    # Year filter (default: current year)
    year_str = request.GET.get("year") or ""
    try:
        year = int(year_str)
    except:
        year = date.today().year
        year_str = str(year)

    qs = (
        Invoice.objects
        .filter(date__year=year)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(
            total_invoices=Count("id"),
            total_amount=Sum("total_amount"),
        )
        .order_by("month")
    )

    rows = list(qs)

    context = {
        "rows": rows,
        "year": year_str,
    }
    return render(request, "payments/monthly_report.html", context)


def monthly_report_csv(request):
    year_str = request.GET.get("year") or ""
    try:
        year = int(year_str)
    except:
        year = date.today().year
        year_str = str(year)

    qs = (
        Invoice.objects
        .filter(date__year=year)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(
            total_invoices=Count("id"),
            total_amount=Sum("total_amount"),
        )
        .order_by("month")
    )

    rows = list(qs)

    # ---- CSV Response ----
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename=monthly_report_{year}.csv"
    writer = csv.writer(response)

    writer.writerow([
        "Month",
        "Total Invoices",
        "Total Invoice Amount",
    ])

    for r in rows:
        writer.writerow([
            r["month"].strftime("%B %Y") if r["month"] else "",
            r["total_invoices"],
            r["total_amount"],
        ])
    return response