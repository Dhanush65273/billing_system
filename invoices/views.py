# invoices/views.py
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from .models import Invoice
from .forms import InvoiceForm, InvoiceItemFormSet
from decimal import Decimal

def invoice_list(request):
    q = request.GET.get("q", "")

    invoices = Invoice.objects.select_related("customer")

    if q:
        invoices = invoices.filter(
            Q(customer__name__icontains=q) |
            Q(id__icontains=q)
        )

    invoices = invoices.order_by("-date")

    context = {
        "invoices": invoices,
        "q": q,
    }
    return render(request, "invoices/invoice_list.html", context)


def invoice_create(request):
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice = form.save()
            formset.instance = invoice
            formset.save()
            # total = items + tax - discount
            invoice.recompute_total()
            return redirect("invoice_list")
    else:
        form = InvoiceForm()
        formset = InvoiceItemFormSet()

    return render(
        request,
        "invoices/invoice_form.html",
        {"form": form, "formset": formset, "title": "New Invoice"},
    )


def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    # Safe defaults
    subtotal = invoice.subtotal or Decimal("0")
    discount = invoice.discount_amount or Decimal("0")
    total = invoice.total_amount or Decimal("0")

    # Base amount = subtotal - discount
    base_amount = subtotal - discount

    # Tax amount = total - base_amount   (total = base + tax)
    tax_amount = total - base_amount

    # Tax % = (tax_amount / base_amount) * 100 (base 0 na 0%)
    if base_amount != 0:
        tax_percent = (tax_amount * Decimal("100")) / base_amount
    else:
        tax_percent = Decimal("0")

    context = {
        "invoice": invoice,
        "tax_amount": tax_amount,
        "tax_percent": tax_percent,
    }
    return render(request, "invoices/invoice_detail.html", context)