# invoices/views.py

from decimal import Decimal
from pathlib import Path
from django.db import transaction
from django.db.models import Sum, Value, DecimalField, Q
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string

from xhtml2pdf import pisa

from .models import Invoice, InvoiceItem
from .forms import InvoiceForm, InvoiceItemFormSet
from products.models import Product
from payments.models import Payment
import os
from django.conf import settings
from xhtml2pdf import pisa
from django.template.loader import get_template


# ======================================================
# CREATE INVOICE
# ======================================================
def invoice_create(request):
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save()

                items = formset.save(commit=False)
                for item in items:
                    item.invoice = invoice

                    if not item.unit_price:
                        item.unit_price = item.product.price or 0

                    item.save()

                for obj in formset.deleted_objects:
                    obj.delete()

                invoice.recompute_total()
                invoice.update_status_from_payments()

            return redirect("invoice_list")
    else:
        form = InvoiceForm()
        formset = InvoiceItemFormSet()

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "items": formset,
            "products": Product.objects.all(),
            "title": "Create Invoice",
        },
    )


# ======================================================
# COMMON TOTAL CALCULATION (ITEM WISE)
# ======================================================
def calculate_invoice_totals(invoice):
    items = invoice.items.all()

    subtotal = Decimal("0.00")
    total_discount = Decimal("0.00")
    total_tax = Decimal("0.00")

    for item in items:
        subtotal += item.unit_price * item.quantity
        total_discount += item.discount_amount or Decimal("0.00")
        total_tax += item.tax_amount or Decimal("0.00")

    grand_total = subtotal - total_discount + total_tax

    total_paid = Payment.objects.filter(
        invoice=invoice, status="paid"
    ).aggregate(
        total=Coalesce(
            Sum("amount"),
            Value(0),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )["total"]

    balance = grand_total - total_paid
    if balance < 0:
        balance = Decimal("0.00")

    return {
        "subtotal": subtotal,
        "total_discount": total_discount,
        "total_tax": total_tax,
        "grand_total": grand_total,
        "total_paid": total_paid,
        "balance": balance,
    }


# ======================================================
# INVOICE DETAIL (VIEW)
# ======================================================
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.all()

    totals = calculate_invoice_totals(invoice)

    return render(
        request,
        "invoices/invoice_detail.html",
        {
            "invoice": invoice,
            "items": items,
            **totals,
        },
    )


# ======================================================
# EDIT INVOICE
# ======================================================
def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()

                items = formset.save(commit=False)
                for item in items:
                    item.invoice = invoice
                    if not item.unit_price:
                        item.unit_price = item.product.price or 0
                    item.save()

                for obj in formset.deleted_objects:
                    obj.delete()

                # 🔥 VERY IMPORTANT
                invoice.recompute_total()
                invoice.update_status_from_payments()
                invoice.save()

            return redirect("invoice_list")

    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice)

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "items": formset,
            "products": Product.objects.all(),
            "title": "Edit Invoice",
        },
    )



# ======================================================
# DELETE INVOICE
# ======================================================
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == "POST":
        invoice.delete()
        return redirect("invoice_list")

    return render(
        request,
        "invoices/invoice_confirm_delete.html",
        {"invoice": invoice},
    )


# ======================================================
# INVOICE LIST
# ======================================================
def invoice_list(request):
    q = request.GET.get("q", "").strip()
    invoices = Invoice.objects.all().order_by("id")

    if q:
        invoices = invoices.filter(
            Q(id__icontains=q) |
            Q(customer__name__icontains=q)
        )

    return render(
        request,
        "invoices/invoice_list.html",
        {
            "invoices": invoices,
            "search_query": q,
        },
    )

import os
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa


def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths
    """
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(
            settings.BASE_DIR,
            'static',
            uri.replace(settings.STATIC_URL, '')
        )
        return path

    return uri


from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from weasyprint import HTML
import os

from .models import Invoice, InvoiceItem


def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    items = InvoiceItem.objects.filter(invoice=invoice)

    # 🔥 totals calculation
    totals = calculate_invoice_totals(invoice)

    # 🔥 logo absolute path
    logo_path = os.path.join(
        settings.BASE_DIR, "static", "images", "logo.png"
    )

    template = get_template("invoices/invoice_pdf.html")

    html_string = template.render({
        "invoice": invoice,
        "items": items,
        "logo_path": logo_path,

        # 🔥 totals passed correctly
        "subtotal": totals["subtotal"],
        "total_discount": totals["total_discount"],
        "total_tax": totals["total_tax"],
        "grand_total": totals["grand_total"],
        "paid": totals["total_paid"],
        "balance": totals["balance"],
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="invoice_{invoice.id}.pdf"'
    )

    HTML(
        string=html_string,
        base_url=settings.BASE_DIR
    ).write_pdf(response)

    return response