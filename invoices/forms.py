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
            "status",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


# =========================
# Invoice Item Form
# =========================
class InvoiceItemForm(forms.ModelForm):
    empty_permitted = True

    class Meta:
        model = InvoiceItem
        fields = [
            "product",
            "quantity",
            "unit_price",

            # 🔥 ITEM-WISE TAX & DISCOUNT
            "tax_percent",
            "discount_type",
            "discount_value",
        ]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),

            "tax_percent": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "discount_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "discount_value": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get("product")
        quantity = cleaned_data.get("quantity")
        unit_price = cleaned_data.get("unit_price")
        discount_value = cleaned_data.get("discount_value")

        # 🔥 Product illa na → row skip
        if not product:
            cleaned_data["DELETE"] = True
            return cleaned_data

        if quantity is not None and quantity <= 0:
            self.add_error("quantity", "Quantity must be greater than 0")

        if unit_price is not None and unit_price < 0:
            self.add_error("unit_price", "Unit price cannot be negative")

        if discount_value is not None and discount_value < 0:
            self.add_error("discount_value", "Discount cannot be negative")

        return cleaned_data


# =========================
# Formset
# =========================
InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=3,
    can_delete=True
)
