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
# payments/views.py
from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404

from .models import Payment
from invoices.models import Invoice

def update_invoice_status(invoice):
    # 🔥 invoice None-na simply exit
    if invoice is None:
        return

    total_amount = invoice.grand_total

    total_paid = (
        Payment.objects
        .filter(invoice=invoice, status="paid")
        .aggregate(total=Sum("amount"))
        .get("total") or Decimal("0")
    )

    if total_paid <= 0:
        invoice.status = "unpaid"
    elif total_paid < total_amount:
        invoice.status = "partial"
    else:
        invoice.status = "paid"

    invoice.save(update_fields=["status"])


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
    
    
from datetime import date
from decimal import Decimal

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce

from customers.models import Customer
from products.models import Product
from invoices.models import Invoice
from payments.models import Payment


@login_required   # 🔥 THIS IS THE KEY LINE
def dashboard(request):
    today = date.today()

    # ----- BASIC COUNTS -----
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()
    total_invoices = Invoice.objects.count()
    total_payments_count = Payment.objects.count()

    # ----- SALES TOTALS -----
    all_invoices = Invoice.objects.all()

    total_sales = Decimal("0.00")
    today_sales = Decimal("0.00")
    month_sales = Decimal("0.00")

    for inv in all_invoices:
        # support both grand_total property & old total_amount
        grand = getattr(inv, "grand_total", inv.total_amount or Decimal("0.00"))

        total_sales += grand

        if inv.date == today:
            today_sales += grand

        if inv.date.year == today.year and inv.date.month == today.month:
            month_sales += grand

    # ----- PAYMENTS TOTAL (actual received) -----
    total_payments = Payment.objects.filter(status="paid").aggregate(
        total=Coalesce(
            Sum("amount"),
            Decimal("0.00"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )["total"]

    context = {
        "total_customers": total_customers,
        "total_products": total_products,
        "total_invoices": total_invoices,
        "total_payments_count": total_payments_count,

        "total_sales": total_sales,
        "today_sales": today_sales,
        "month_sales": month_sales,
        "total_payments": total_payments,
    }

    return render(request, "dashboard.html", context)

def payment_list(request):
    payments = (
        Payment.objects
        .filter(invoice__isnull=False)   # 🔥 IMPORTANT FIX
        .select_related("invoice", "invoice__customer")
        .order_by("-date", "-id")
    )

    return render(
        request,
        "payments/payment_list.html",
        {"payments": payments}
    )


def payment_edit(request, pk):
    payment = get_object_or_404(Payment, pk=pk)

    if request.method == "POST":
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            # keep it paid
            payment.status = "paid"
            payment.save()

            payment.invoice.update_status_from_payments()
            return redirect("payment_list")
    else:
        form = PaymentForm(instance=payment)

    return render(request, "payments/payment_form.html", {"form": form, "title": "Edit Payment"})

def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)

    # 🔥 invoice reference save pannrom
    invoice = payment.invoice

    if request.method == "POST":
        payment.delete()

        # 🔥 invoice irundha mattum status update
        if invoice is not None:
            update_invoice_status(invoice)

        return redirect("payment_list")

    return render(
        request,
        "payments/payment_confirm_delete.html",
        {
            "payment": payment,
        }
    )

# payments/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Payment
from .forms import PaymentForm

def auto_allocate_customer_payment(customer, payment_date, method, amount):
    """
    Customer payment amount ah oldest unpaid/partial invoices ku FIFO la adjust pannum.
    Remaining amount irundha advance ah save pannum.
    """
    remaining = Decimal(amount)

    invoices = (
        Invoice.objects
        .filter(
            customer=customer,
            status__in=["unpaid", "partial"]
        )
        .order_by("date", "id")
    )

    for invoice in invoices:
        if remaining <= 0:
            break

        balance = invoice.balance
        if balance <= 0:
            continue

        allocate = min(balance, remaining)

        Payment.objects.create(
            customer=customer,
            invoice=invoice,
            date=payment_date,
            amount=allocate,
            method=method,
            status="paid",
        )

        invoice.update_status_from_payments()
        remaining -= allocate

    # 🔥 advance amount
    if remaining > 0:
        Payment.objects.create(
            customer=customer,
            invoice=None,
            date=payment_date,
            amount=remaining,
            method=method,
            status="paid",
            is_advance=True,
            notes="Advance payment",
        )

def payment_create(request):
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            base_payment = form.save(commit=False)

            # 🔥 DO NOT save base payment directly
            auto_allocate_customer_payment(
                customer=base_payment.customer,
                payment_date=base_payment.date,
                method=base_payment.method,
                amount=base_payment.amount,
            )

            return redirect("payment_list")
    else:
        form = PaymentForm()

    return render(
        request,
        "payments/payment_form.html",
        {
            "form": form,
            "title": "Add Payment",
        },
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
            items_qs = items_qs.filter(invoice__date__gte=date_from)
        if date_to:
            items_qs = items_qs.filter(invoice__date__lte=date_to)

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
    products = Product.objects.all().order_by("name")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="product_report.csv"'
    writer = csv.writer(response)

    writer.writerow([
        "Product",
        "Invoices Count",
        "Invoice Amount (₹)",
        "Payments Received (₹)",
    ])

    for p in products:
        items = InvoiceItem.objects.filter(product=p)

        invoice_ids = items.values_list("invoice_id", flat=True).distinct()

        total_amount = sum(
            (i.invoice.grand_total for i in items if i.invoice),
            Decimal("0")
        )

        total_paid = Payment.objects.filter(
            invoice_id__in=invoice_ids,
            status="paid"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        writer.writerow([
            p.name,
            invoice_ids.count(),
            f"{total_amount:.2f}",
            f"{total_paid:.2f}",
        ])

    return response


from decimal import Decimal
from django.db.models import Sum, Q, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from invoices.models import Invoice
from django.shortcuts import render


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

    # order invoices for display
    invoices = invoices.order_by("-date", "-id")

    # ---- overall totals (manual using grand_total + balance) ----
    total_amount = Decimal("0.00")
    total_paid_sum = Decimal("0.00")
    total_balance_sum = Decimal("0.00")

    for inv in invoices:
        # invoice total – use grand_total property if available
        grand = getattr(inv, "grand_total", inv.total_amount or Decimal("0.00"))
        paid = inv.total_paid or Decimal("0.00")
        balance = grand - paid

        total_amount += grand
        total_paid_sum += paid
        total_balance_sum += balance

    totals = {
        "total_amount": total_amount,      # sum of inv.grand_total
        "total_paid": total_paid_sum,      # sum of paid amounts
        "total_balance": total_balance_sum # sum(grand_total - paid)
    }

    context = {
        "invoices": invoices,
        "date_from": date_from,
        "date_to": date_to,
        "totals": totals,
    }
    return render(request, "payments/invoice_report.html", context)



def invoice_report_csv(request):
    date_from = request.GET.get("date_from") or ""
    date_to = request.GET.get("date_to") or ""

    invoices = (
        Invoice.objects
        .select_related("customer")
        .prefetch_related("payments")
        .order_by("date", "id")
    )

    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="invoice_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Invoice ID",
        "Date",
        "Customer",
        "Invoice Total (₹)",
        "Paid Amount (₹)",
        "Balance (₹)",
        "Status",
    ])

    for inv in invoices:
        writer.writerow([
            inv.id,
            inv.date.strftime("%d-%m-%Y") if inv.date else "",
            inv.customer.name if inv.customer else "",
            f"{inv.grand_total:.2f}",
            f"{inv.amount_paid:.2f}",
            f"{inv.balance:.2f}",
            inv.get_status_display(),
        ])

    return response


def _get_outstanding_rows():
    """
    Returns list of dicts for invoices where balance > 0
    Using Invoice.grand_total / amount_paid / balance.
    """
    rows = []

    invoices = (
        Invoice.objects
        .select_related("customer")
        .prefetch_related("items")
        .order_by("date", "id")
    )

    for inv in invoices:
        total = inv.grand_total
        paid = inv.amount_paid
        balance = inv.balance

        if balance <= 0:
            # fully paid or overpaid → not outstanding
            continue

        rows.append({
            "invoice": inv,
            "total": total,
            "paid": paid,
            "balance": balance,
        })

    return rows


from django.shortcuts import render

def outstanding_report(request):
    rows = _get_outstanding_rows()

    context = {
        "rows": rows,
    }
    return render(request, "payments/outstanding_report.html", context)

def outstanding_report_csv(request):
    rows = _get_outstanding_rows()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="outstanding_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Invoice ID",
        "Date",
        "Customer",
        "Invoice Total (₹)",
        "Paid (₹)",
        "Outstanding (₹)",
        "Status",
    ])

    for r in rows:
        inv = r["invoice"]
        writer.writerow([
            inv.id,
            inv.date.strftime("%d-%m-%Y"),
            inv.customer.name,
            f"{r['total']:.2f}",
            f"{r['paid']:.2f}",
            f"{r['balance']:.2f}",
            inv.get_status_display(),
        ])

    return response

from django.db.models import Sum
from .models import Payment

def payment_report(request):
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    payments = (
        Payment.objects
        .filter(invoice__isnull=False)
        .select_related("invoice__customer")
        .order_by("-date", "-id")
    )

    if date_from and date_from != "None":
        payments = payments.filter(date__gte=date_from)
    if date_to and date_to != "None":
        payments = payments.filter(date__lte=date_to)

    total_amount = payments.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    return render(
        request,
        "payments/payment_report.html",
        {
            "payments": payments,
            "total_amount": total_amount,
            "date_from": date_from,
            "date_to": date_to,
        }
    )


def payment_report_csv(request):
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    payments = Payment.objects.filter(
        invoice__isnull=False
    ).select_related("invoice__customer")

    if date_from:
        payments = payments.filter(date__gte=date_from)
    if date_to:
        payments = payments.filter(date__lte=date_to)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="payment_report.csv"'
    writer = csv.writer(response)

    writer.writerow([
        "Date",
        "Invoice ID",
        "Customer",
        "Method",
        "Amount (₹)",
    ])

    for p in payments.order_by("date", "id"):
        writer.writerow([
            p.date.strftime("%d-%m-%Y"),
            p.invoice.id,
            p.invoice.customer.name,
            p.get_method_display(),
            f"{p.amount:.2f}",
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
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    customers = Customer.objects.all().order_by("name")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="customer_report.csv"'
    writer = csv.writer(response)

    writer.writerow([
        "Customer",
        "Total Invoices",
        "Total Billed (₹)",
        "Total Paid (₹)",
        "Outstanding (₹)",
    ])

    for c in customers:
        invoices = Invoice.objects.filter(customer=c)

        if date_from:
            invoices = invoices.filter(date__gte=date_from)
        if date_to:
            invoices = invoices.filter(date__lte=date_to)

        total_billed = sum((i.grand_total for i in invoices), Decimal("0"))
        total_paid = sum((i.amount_paid for i in invoices), Decimal("0"))
        outstanding = total_billed - total_paid

        writer.writerow([
            c.name,
            invoices.count(),
            f"{total_billed:.2f}",
            f"{total_paid:.2f}",
            f"{outstanding:.2f}",
        ])

    return response


from datetime import date
from decimal import Decimal
import csv

from django.http import HttpResponse
from django.shortcuts import render

from invoices.models import Invoice


def _build_monthly_data(year: int):
    """Year-ku month wise count + grand_total sum build pannum helper."""
    invoices_qs = Invoice.objects.filter(date__year=year)

    buckets = {}  # key = month_start_date, value = dict with totals

    for inv in invoices_qs:
        # same month key (1st day of that month)
        month_start = inv.date.replace(day=1)

        if month_start not in buckets:
            buckets[month_start] = {
                "month": month_start,
                "total_invoices": 0,
                "total_amount": Decimal("0.00"),
            }

        buckets[month_start]["total_invoices"] += 1

        # inv.grand_total property la irukka real amount use pannrom
        gt = getattr(inv, "grand_total", None)
        if gt is None:
            gt = Decimal("0.00")

        buckets[month_start]["total_amount"] += gt

    # sort by month
    monthly_data = sorted(buckets.values(), key=lambda b: b["month"])
    return monthly_data


def monthly_report(request):
    year = request.GET.get("year")
    if not year:
        year = date.today().year
    else:
        try:
            year = int(year)
        except ValueError:
            year = date.today().year

    monthly_data = _build_monthly_data(year)

    context = {
        "year": year,
        "monthly_data": monthly_data,
    }
    return render(request, "payments/monthly_report.html", context)


def monthly_report_csv(request):
    year = request.GET.get("year")
    year = int(year) if year and year.isdigit() else date.today().year

    monthly_data = _build_monthly_data(year)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="monthly_report_{year}.csv"'

    writer = csv.writer(response)
    writer.writerow(["S.No", "Month", "Invoices", "Total Amount (₹)"])

    for idx, row in enumerate(monthly_data, start=1):
        writer.writerow([
            idx,
            row["month"].strftime("%b %Y"),
            row["total_invoices"],
            f"{row['total_amount']:.2f}",
        ])

    return response

from decimal import Decimal
from django.db.models import Sum
from customers.models import Customer
from invoices.models import Invoice
from .models import Payment

def customer_summary_report(request):
    # get selected customer id from query string
    customer_id = request.GET.get("customer") or ""
    customers = Customer.objects.all().order_by("name")

    selected_customer = None
    invoices = []
    payments = []
    summary = None

    if customer_id:
        try:
            selected_customer = customers.get(id=customer_id)
        except Customer.DoesNotExist:
            selected_customer = None
        else:
            # all invoices for that customer
            invoices = (
                Invoice.objects
                .filter(customer=selected_customer)
                .prefetch_related("items")
                .order_by("date", "id")
            )

            # total billed = sum of grand_total
            total_billed = sum((inv.grand_total for inv in invoices), Decimal("0"))

            # total outstanding = sum of invoice balances
            total_outstanding = sum((inv.balance for inv in invoices), Decimal("0"))

            # all PAID payments for that customer's invoices
            payments = (
                Payment.objects
                .filter(invoice__customer=selected_customer, status="paid")
                .select_related("invoice")
                .order_by("date", "id")
            )

            total_paid = (
                payments.aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )

            summary = {
                "total_invoices": len(invoices),
                "total_billed": total_billed,
                "total_paid": total_paid,
                "total_outstanding": total_outstanding,
            }

    context = {
        "customers": customers,
        "customer_id": customer_id,
        "selected_customer": selected_customer,
        "summary": summary,
        "invoices": invoices,
        "payments": payments,
    }
    return render(request, "payments/customer_summary.html", context)


from django.http import HttpResponse
import csv
from decimal import Decimal

# ... already have Customer, Invoice, Payment imports ...


def customer_summary_csv(request):
    customer_id = request.GET.get("customer")

    customer = get_object_or_404(Customer, id=customer_id)

    invoices = (
        Invoice.objects
        .filter(customer=customer)
        .order_by("date", "id")
    )

    payments = (
        Payment.objects
        .filter(invoice__customer=customer, status="paid")
        .select_related("invoice")
        .order_by("date", "id")
    )

    # ---- SUMMARY TOTALS ----
    total_invoices = invoices.count()
    total_billed = sum((inv.grand_total for inv in invoices), Decimal("0"))
    total_paid = sum((inv.amount_paid for inv in invoices), Decimal("0"))
    total_outstanding = total_billed - total_paid

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="customer_summary_{customer.id}.csv"'
    )

    writer = csv.writer(response)

    # ---- HEADER ----
    writer.writerow([f"Customer Summary - {customer.name}"])
    writer.writerow([])

    # ---- SUMMARY SECTION ----
    writer.writerow(["Total Invoices", total_invoices])
    writer.writerow(["Total Billed (₹)", f"{total_billed:.2f}"])
    writer.writerow(["Total Paid (₹)", f"{total_paid:.2f}"])
    writer.writerow(["Outstanding (₹)", f"{total_outstanding:.2f}"])
    writer.writerow([])

    # ---- INVOICES SECTION ----
    writer.writerow(["Invoices"])
    writer.writerow([
        "S.No",
        "Invoice ID",
        "Date",
        "Total (₹)",
        "Paid (₹)",
        "Balance (₹)",
        "Status",
    ])

    for idx, inv in enumerate(invoices, start=1):
        writer.writerow([
            idx,
            inv.id,
            inv.date.strftime("%d-%m-%Y"),
            f"{inv.grand_total:.2f}",
            f"{inv.amount_paid:.2f}",
            f"{inv.balance:.2f}",
            inv.get_status_display(),
        ])

    writer.writerow([])

    # ---- PAYMENTS SECTION ----
    writer.writerow(["Payments"])
    writer.writerow([
        "S.No",
        "Date",
        "Invoice ID",
        "Amount (₹)",
        "Method",
    ])

    for idx, p in enumerate(payments, start=1):
        writer.writerow([
            idx,
            p.date.strftime("%d-%m-%Y"),
            p.invoice.id if p.invoice else "",
            f"{p.amount:.2f}",
            p.get_method_display(),
        ])

    return response

from django.http import JsonResponse
from invoices.models import Invoice

def pending_invoices(request):
    customer_id = request.GET.get("customer_id")

    if not customer_id:
        return JsonResponse({"invoices": []})

    invoices = (
        Invoice.objects
        .filter(
            customer_id=customer_id,
            status__in=["unpaid", "partial"]
        )
        .order_by("date")
    )

    data = []

    for inv in invoices:
        data.append({
            "number": inv.id,  # or invoice number if you add later
            "date": inv.date.strftime("%d-%m-%Y"),
            "total": float(inv.grand_total),      # ✅ property
            "paid": float(inv.amount_paid),       # ✅ property
            "balance": float(inv.balance),        # ✅ property
        })

    return JsonResponse({"invoices": data})
