# invoices/models.py
from decimal import Decimal

from django.db import models
from django.db.models import Sum, F

from customers.models import Customer
from products.models import Product


class InvoiceManager(models.Manager):
    def get_queryset(self):
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
        max_digits=5, decimal_places=2, default=0
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    # stored value (optional)
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="unpaid"
    )

    objects = InvoiceManager()

    def __str__(self):
        return f"Invoice #{self.id} - {self.customer.name}"

    # ---------- computed values ----------

    @property
    def subtotal(self):
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.line_subtotal
        return total

    @property
    def tax_amount(self):
        return self.subtotal * self.tax_percent / Decimal("100")

    @property
    def grand_total(self):
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.line_total
        return total

    # ✅ THIS WAS MISSING EARLIER (NOW FIXED)
    def recompute_total(self):
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.line_total
        self.total_amount = total
        self.save(update_fields=["total_amount"])

    @property
    def amount_paid(self):
        total = self.payments.filter(status="paid").aggregate(
            total=Sum("amount")
        )["total"]
        return total or Decimal("0")

    @property
    def balance(self):
        return self.grand_total - self.amount_paid

    def update_status_from_payments(self):
        if self.status == "cancelled":
            return

        paid = self.amount_paid
        total = self.grand_total

        if paid <= 0:
            self.status = "unpaid"
        elif paid < total:
            self.status = "partial"
        else:
            self.status = "paid"

        self.save(update_fields=["status"])


class InvoiceItem(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ("percent", "Percentage"),
        ("amount", "Amount"),
    ]

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    tax_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    discount_type = models.CharField(
        max_length=10, choices=DISCOUNT_TYPE_CHOICES, default="amount"
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def line_subtotal(self):
        return self.quantity * self.unit_price

    @property
    def discount_amount(self):
        if self.discount_type == "percent":
            return self.line_subtotal * self.discount_value / Decimal("100")
        return self.discount_value

    @property
    def tax_amount(self):
        taxable = self.line_subtotal - self.discount_amount
        if taxable < 0:
            taxable = Decimal("0")
        return taxable * self.tax_percent / Decimal("100")

    @property
    def line_total(self):
        return self.line_subtotal - self.discount_amount + self.tax_amount

    # ============================
    # Payment Allocation Helpers
    # ============================

    def total_paid_amount(self):
        """
        Total paid amount for this invoice (paid payments only)
        """
        total = self.payments.filter(status="paid").aggregate(
            total=Sum("amount")
        )["total"]
        return total or Decimal("0.00")

    def balance_amount(self):
        """
        Remaining balance for this invoice
        """
        return self.grand_total - self.total_paid_amount()

    def apply_payment(self, amount):
        """
        Apply payment amount to this invoice and update status
        Returns remaining amount (if any)
        """
        if amount <= 0:
            return amount

        balance = self.balance_amount()

        if balance <= 0:
            return amount

        applied = min(balance, amount)

        # create payment entry linked to invoice
        from payments.models import Payment  # local import to avoid circular

        Payment.objects.create(
            customer=self.customer,
            invoice=self,
            amount=applied,
            status="paid",
        )

        # update invoice status
        self.update_status_from_payments()

        return amount - applied

