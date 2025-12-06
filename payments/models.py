# payments/models.py
from django.db import models
from invoices.models import Invoice


class Payment(models.Model):
    STATUS_CHOICES = [
        ("paid", "Paid"),
        ("partial", "Partially Paid"),
        ("failed", "Failed"),
    ]

    METHOD_CHOICES = [
        ("cash", "Cash"),
        ("card", "Card"),
        ("upi", "UPI"),
        ("bank", "Bank Transfer"),
        ("other", "Other"),
    ]

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="paid"
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.id} - Invoice #{self.invoice_id}"

    # 🔥 IMPORTANT: whenever payment changes, update invoice status/balance

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invoice.update_status_from_payments()

    def delete(self, *args, **kwargs):
        inv = self.invoice
        super().delete(*args, **kwargs)
        inv.update_status_from_payments()