from django import forms
from decimal import Decimal
from .models import Payment


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["customer", "date", "amount", "method"]
        widgets = {
            "customer": forms.Select(
                attrs={"class": "form-select"}
            ),
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "method": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    # -------------------------
    # Validations
    # -------------------------
    def clean_amount(self):
        amount = self.cleaned_data.get("amount")

        if amount is None:
            raise forms.ValidationError("Payment amount is required")

        if amount <= Decimal("0"):
            raise forms.ValidationError(
                "Payment amount must be greater than zero"
            )

        return amount

    def clean_customer(self):
        customer = self.cleaned_data.get("customer")

        if customer is None:
            raise forms.ValidationError("Customer is required")

        return customer
