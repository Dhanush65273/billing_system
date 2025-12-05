from django.db import models
from invoices.models import Invoice

PAYMENT_METHODS = (
    ("cash", "Cash"),
    ("card", "Card"),
    ("upi", "UPI"),
)

PAYMENT_STATUS = (
    ("success", "Success"),
    ("pending", "Pending"),
    ("failed", "Failed"),
)


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    payment_date = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default="cash")
    status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default="success")

    def _str_(self):
        return f"Payment {self.id} for Invoice {self.invoice_id}"