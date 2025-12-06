# payments/forms.py
from django import forms
from .models import Payment

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["invoice", "date", "amount", "method", "status", "notes"]
        widgets = {
            "invoice": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "method": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }