# payments/forms.py
from django import forms
from .models import Payment


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        # ONLY these fields appear in the form
        fields = ["invoice", "date", "amount", "method"]
        widgets = {
            # HTML5 date picker
            "date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "invoice": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control"}),
            "method": forms.Select(attrs={"class": "form-select"}),
        }
