# invoices/models.py
from decimal import Decimal

from django.db import models
from django.db.models import Sum, F

from customers.models import Customer
from products.models import Product

class InvoiceManager(models.Manager):
    """
    Old code Invoice.objects.filter(invoice_date=...) nu use panninAlum
    work aaganum nu alias panni tharom.
    """
    def get_queryset(self):
        # invoice_date alias = date column
        return super().get_queryset().alias(invoice_date=F("date"))

class Invoice(models.Model):
    STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("partial", "Partially Paid"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="invoices"
    )
    date = models.DateField()
    tax_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0  # e.g. 18.00
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="unpaid"
    )

    objects = InvoiceManager()

    def __str__(self):
        return f"Invoice #{self.id} - {self.customer.name}"

    # ---------- helpers ----------

    @property
    def subtotal(self) -> Decimal:
        """Sum of all item line totals (qty * unit_price)."""
        total = self.items.aggregate(
            total=Sum(F("quantity") * F("unit_price"))
        )["total"]
        return total or Decimal("0")

    @property
    def amount_paid(self) -> Decimal:
        """Total of successful payments."""
        total = self.payments.filter(status="paid").aggregate(
            total=Sum("amount")
        )["total"]
        return total or Decimal("0")

    @property
    def balance(self) -> Decimal:
        return self.total_amount - self.amount_paid

    # ---------- business logic ----------

    def recompute_total(self):
        """
        Recalculate invoice.total_amount from items + tax% - discount.
        Call this after saving items.
        """
        sub = self.subtotal
        tax = sub * (self.tax_percent / Decimal("100"))
        self.total_amount = sub + tax - self.discount_amount
        self.save(update_fields=["total_amount"])

    def update_status_from_payments(self):
        """
        Set status based on payments.
        """
        if self.status == "cancelled":
            return

        paid = self.amount_paid

        if paid <= 0:
            self.status = "unpaid"
        elif paid < self.total_amount:
            self.status = "partial"
        else:
            self.status = "paid"

        self.save(update_fields=["status"])


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def line_total(self) -> Decimal:
        return self.quantity * self.unit_price