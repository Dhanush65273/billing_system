from django.shortcuts import render, redirect, get_object_or_404
from .models import Payment
from .forms import PaymentForm
from invoices.models import Invoice


def payment_list(request):
    payments = Payment.objects.select_related("invoice", "invoice__customer").order_by("-id")
    return render(request, "payments/payment_list.html", {
        "payments": payments
    })


def payment_create(request):
    invoice_id = request.GET.get("invoice_id")

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("payment_list")
    else:
        if invoice_id:
            invoice = get_object_or_404(Invoice, pk=invoice_id)
            form = PaymentForm(initial={
                "invoice": invoice,
                "amount": invoice.total_amount,
            })
        else:
            form = PaymentForm()

    return render(request, "payments/payment_form.html", {
        "form": form
    })


def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    payment.delete()
    return redirect("payment_list")