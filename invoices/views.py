# invoices/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.db.models.functions import Coalesce

from products.models import Product
from .models import Invoice
from .forms import InvoiceForm, InvoiceItemFormSet
from .models import Invoice, InvoiceItem, Product
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce

from decimal import Decimal

from django.db import transaction
from django.shortcuts import redirect, render
from products.models import Product
from .forms import InvoiceForm, InvoiceItemFormSet

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

                    # unit price fallback
                    if not item.unit_price:
                        item.unit_price = item.product.price or 0

                    item.save()

                # delete marked rows
                for obj in formset.deleted_objects:
                    obj.delete()

                # 🔥 recompute & update status
                invoice.recompute_total()
                invoice.update_status_from_payments()

            return redirect("invoice_list")

    else:
        form = InvoiceForm()
        formset = InvoiceItemFormSet()

    products = Product.objects.all()

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "items": formset,
            "products": products,
            "title": "Create Invoice",
        },
    )

from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from payments.models import Payment


def recalculate_invoice_totals(invoice):
    """Recalculate totals & status for a single invoice."""

    items = invoice.items.all()

    # SUBTOTAL
    subtotal = Decimal("0.00")
    for item in items:
        subtotal += item.unit_price * item.quantity

    # DISCOUNT & TAX
    discount = invoice.discount_amount or Decimal("0.00")
    tax_percent = invoice.tax_percent or Decimal("0.00")

    taxable_amount = subtotal - discount
    if taxable_amount < 0:
        taxable_amount = Decimal("0.00")

    tax_amount = (taxable_amount * tax_percent) / Decimal("100")
    grand_total = taxable_amount + tax_amount

    # PAYMENTS (only 'paid' payments)
    paid_qs = Payment.objects.filter(invoice=invoice, status="paid")

    total_paid = paid_qs.aggregate(
        total=Coalesce(
            Sum("amount"),
            Value(0),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )["total"]

    balance = grand_total - total_paid

    # STATUS LOGIC
    if total_paid <= 0:
        invoice.status = "unpaid"
    elif balance <= 0:
        invoice.status = "paid"
    else:
        invoice.status = "partial"

    invoice.save(update_fields=["status"])

    # return numbers so others can use
    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax_percent": tax_percent,
        "tax_amount": tax_amount,
        "grand_total": grand_total,
        "total_paid": total_paid,
        "balance": balance,
    }

from decimal import Decimal

from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from payments.models import Payment


def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.all()

    totals = recalculate_invoice_totals(invoice)
    # ---------- SUBTOTAL ----------
    subtotal = Decimal("0.00")
    for item in items:
        subtotal += item.unit_price * item.quantity

    # ---------- DISCOUNT & TAX ----------
    discount = invoice.discount_amount or Decimal("0.00")
    tax_percent = invoice.tax_percent or Decimal("0.00")

    taxable_amount = subtotal - discount
    if taxable_amount < 0:
        taxable_amount = Decimal("0.00")

    tax_amount = (taxable_amount * tax_percent) / Decimal("100")

    # GRAND TOTAL = items - discount + tax
    grand_total = taxable_amount + tax_amount

    # ---------- PAYMENTS ----------
    # change 'paid' to your actual status value if different
    payments = Payment.objects.filter(invoice=invoice, status="paid")

    total_paid = payments.aggregate(
        total=Coalesce(
            Sum("amount"),
            Value(0),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )["total"]

    balance = grand_total - total_paid
    if balance < 0:
        balance = Decimal("0.00")

    # NOTE: we DO NOT assign to invoice.amount_paid / invoice.balance here,
    # because they are properties (read-only)

    return render(
        request,
        "invoices/invoice_detail.html",
        {
            "invoice": invoice,
            "items": items,
            "subtotal": subtotal,
            "discount": discount,
            "tax_percent": tax_percent,
            "tax_amount": tax_amount,
            "grand_total": grand_total,
            "total_paid": total_paid,
            "balance": balance,
        },
    )




from django.shortcuts import render, redirect, get_object_or_404
# ... other imports


def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == "POST":
        invoice.delete()
        return redirect("invoice_list")   # list page-ku thirumba

    # GET request na simple confirm page show pannalaam (optional)
    return render(request, "invoices/invoice_confirm_delete.html", {
        "invoice": invoice,
    })

# invoices/views.py
from django.db.models import Q
from django.shortcuts import render
from .models import Invoice


def invoice_list(request):
    q = request.GET.get("q", "").strip()

    invoices = Invoice.objects.all().order_by("id")

    if q:
        # If q is a number → also check invoice id
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
        }
    )

# invoices/views.py

from django.shortcuts import render, redirect, get_object_or_404
from .models import Invoice, InvoiceItem
from .forms import InvoiceForm, InvoiceItemFormSet
from products.models import Product

def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()

                # 🔥 THIS IS THE FIX
                invoice.recompute_total()
                invoice.update_status_from_payments()

            return redirect("invoice_list")
    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice)

    products = Product.objects.all()

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "items": formset,
            "products": products,
            "title": "Edit Invoice",
        },
    )

from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa

def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.all()

    html = render_to_string(
        "invoices/invoice_pdf.html",
        {
            "invoice": invoice,
            "items": items,
        }
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{invoice.id}.pdf"'

    pisa.CreatePDF(html, dest=response)
    return response
