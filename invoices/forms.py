# invoices/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import Invoice, InvoiceItem
from products.models import Product   # 🔹 add this


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🟢 ADD PRICE INSIDE <option data-price="...">
        product_field = self.fields['product']
        product_field.widget.attrs.update({"class": "form-select"})

        new_choices = []
        for p in product_field.queryset:
            new_choices.append(
                (p.id, f'{p.name}'),  # normal name, id is value
            )
        product_field.widget.choices = new_choices



InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=3,        # 3 rows
    can_delete=True,
)
