from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from .models import Invoice, InvoiceItem
from .forms import InvoiceForm
from products.models import Product


# LIST VIEW
def invoice_list(request):
    invoices = Invoice.objects.select_related("customer").order_by("-id")
    return render(request, "invoices/invoice_list.html", {
        "invoices": invoices
    })


# DETAIL VIEW
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related("customer").prefetch_related("items__product"),
        pk=pk
    )
    return render(request, "invoices/invoice_detail.html", {
        "invoice": invoice
    })


# CREATE VIEW
def invoice_create(request):
    products = Product.objects.all().order_by("name")

    if request.method == "POST":
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.total_amount = Decimal("0.00")
            invoice.save()

            product_ids = request.POST.getlist("product")
            quantities = request.POST.getlist("quantity")

            total = Decimal("0.00")

            for p_id, qty_str in zip(product_ids, quantities):
                if not p_id or not qty_str:
                    continue

                product = Product.objects.get(id=p_id)
                qty = int(qty_str)

                price = product.product_price
                amount = price * qty
                total += amount

                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=qty,
                    price=price,
                    amount=amount
                )

            invoice.total_amount = total
            invoice.save()

            return redirect("invoice_list")
    else:
        form = InvoiceForm()

    return render(request, "invoices/invoice_form.html", {
        "form": form,
        "products": products
    })


# DELETE VIEW (optional but useful)
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    invoice.delete()
    return redirect("invoice_list")