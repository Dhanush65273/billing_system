from django import forms
from .models import Invoice, InvoiceItem


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["customer"]   # date & total auto


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ["product", "quantity"]