from django.db import models
from customers.models import Customer
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

    # 🔥 Payment is CUSTOMER based
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    # 🔥 Invoice optional (used for auto allocation)
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
        max_length=20,
        choices=STATUS_CHOICES,
        default="paid"
    )

    # 🔥 Extra / advance amount flag
    is_advance = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.invoice_id:
            return f"Payment #{self.id} - Invoice #{self.invoice_id}"
        return f"Payment #{self.id} - Customer {self.customer.name}"

    # -----------------------
    # Helpers
    # -----------------------
    def is_linked_to_invoice(self):
        return self.invoice_id is not None

    # -----------------------
    # Save / Delete hooks
    # -----------------------
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # 🔥 Update invoice status only if linked
        if self.invoice_id:
            self.invoice.update_status_from_payments()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)

        if invoice:
            invoice.update_status_from_payments()
