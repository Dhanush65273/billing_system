# invoices/views.py
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from .models import Invoice
from .forms import InvoiceForm, InvoiceItemFormSet


def invoice_list(request):
    q = request.GET.get("q", "").strip()
    invoices = Invoice.objects.select_related("customer").order_by("-date", "-id")

    if q:
        invoices = invoices.filter(
            Q(id__icontains=q) |
            Q(customer_name_icontains=q)
        )

    context = {
        "invoices": invoices,
        "search_query": q,
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
    invoice = get_object_or_404(
        Invoice.objects.select_related("customer"), pk=pk
    )
    return render(request, "invoices/invoice_detail.html", {"invoice": invoice})