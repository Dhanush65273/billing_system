# invoices/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import Invoice, InvoiceItem


class InvoiceForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )

    class Meta:
        model = Invoice
        fields = ["customer", "date", "tax_percent", "discount_amount", "status"]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select"}),
            "tax_percent": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "discount_amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ["product", "quantity", "unit_price"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=3,        # 3 rows like your video
    can_delete=True,
)