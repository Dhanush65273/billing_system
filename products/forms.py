# products/forms.py

from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "sku", "price", "stock"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "sku": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Eg: IPH16-BLK"
            }),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "stock": forms.NumberInput(attrs={"class": "form-control"}),
        }
