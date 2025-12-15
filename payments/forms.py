# payments/forms.py
from django import forms
from .models import Payment

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["customer", "date", "amount", "method"]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control"}),
            "method": forms.Select(attrs={"class": "form-select"}),
        }
