# payments/models.py

from django.db import models
from customers.models import Customer      # 🔥 ADD
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

    # 🔥 NEW: Payment is primarily based on CUSTOMER
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    # 🔥 KEEP: invoice optional (auto allocation / manual link)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True
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
        if self.invoice:
            return f"Payment #{self.id} - Invoice #{self.invoice_id}"
        return f"Payment #{self.id} - Customer {self.customer.name}"

    # 🔥 IMPORTANT: invoice irundha mattum status update
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.invoice:
            self.invoice.update_status_from_payments()

    def delete(self, *args, **kwargs):
        inv = self.invoice
        super().delete(*args, **kwargs)
        if inv:
            inv.update_status_from_payments()
