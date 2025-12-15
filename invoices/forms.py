# invoices/forms.py

from django import forms
from django.forms import inlineformset_factory

from .models import Invoice, InvoiceItem


# =========================
# Invoice Main Form
# =========================
class InvoiceForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        )
    )

    class Meta:
        model = Invoice
        fields = [
            "customer",
            "date",
            "tax_percent",
            "discount_amount",
            "status",
        ]
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
    empty_permitted = True   # 🔥 THIS IS THE KEY
    class Meta:
        model = InvoiceItem
        fields = ["product", "quantity", "unit_price"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get("product")
        quantity = cleaned_data.get("quantity")
        unit_price = cleaned_data.get("unit_price")

        # 🔥 If product empty → skip this row completely
        if not product:
            cleaned_data["DELETE"] = True

        return cleaned_data

InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=3,
    can_delete=True
)
