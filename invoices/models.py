# invoices/models.py
from decimal import Decimal

from django.db import models
from django.db.models import Sum, F

from customers.models import Customer
from products.models import Product   # ✅ CORRECT import (remove `from .models import Product`)


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
        max_digits=5, decimal_places=2, default=0  # e.g. 10.00
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    # NOTE: இந்த field optional storage காக மட்டும்.
    # Calculations கீழே உள்ள properties use பண்ணிக்கலாம்.
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="unpaid"
    )

    objects = InvoiceManager()

    def __str__(self):
        return f"Invoice #{self.id} - {self.customer.name}"

    # ---------- helpers (computed values) ----------

    @property
    def subtotal(self) -> Decimal:
        """Sum of all item line totals (qty * unit_price)."""
        total = self.items.aggregate(
            total=Sum(F("quantity") * F("unit_price"))
        )["total"]
        return total or Decimal("0")

    @property
    def taxable_amount(self) -> Decimal:
        """
        Subtotal - discount. இதுக்கு தான் tax calculate பண்ணப் போறோம்.
        """
        amt = self.subtotal - (self.discount_amount or Decimal("0"))
        if amt < 0:
            amt = Decimal("0")
        return amt

    @property
    def tax_amount(self) -> Decimal:
        """
        Tax = taxable_amount * (tax_percent / 100)
        i.e. (subtotal − discount) * tax%.
        """
        return self.taxable_amount * (self.tax_percent / Decimal("100"))

    @property
    def grand_total(self) -> Decimal:
        """
        Final amount customer pay பண்ணணும்:
        (subtotal − discount) + tax_amount
        """
        return self.taxable_amount + self.tax_amount

    @property
    def amount_paid(self) -> Decimal:
        """Total of successful payments (status = paid)."""
        total = self.payments.filter(status="paid").aggregate(
            total=Sum("amount")
        )["total"]
        return total or Decimal("0")

    @property
    def balance(self) -> Decimal:
        """
        Balance = grand_total - amount_paid
        DB field `total_amount` இல்லாமலே correct result கிடைக்கும்.
        """
        return self.grand_total - self.amount_paid
    
    @property
    def total(self):
        """
        Full invoice total = sum(line totals) + tax - discount.
        Used in invoice list and monthly reports.
        """
        from decimal import Decimal

        subtotal = Decimal("0.00")

        # items = related_name in InvoiceItem(invoice=..., related_name="items")
        for item in self.items.all():
            subtotal += item.line_total   # InvoiceItem property

        tax_percent = self.tax_percent or 0
        discount_amount = self.discount_amount or Decimal("0.00")

        tax_amount = subtotal * Decimal(tax_percent) / Decimal("100")

        return subtotal + tax_amount - discount_amount

    # ---------- business logic ----------

    def recompute_total(self):
        """
        Recalculate and store total_amount field from items + tax% - discount.
        Use same logic as grand_total.
        """
        self.total_amount = self.grand_total
        self.save(update_fields=["total_amount"])

    def update_status_from_payments(self):
        """
        Set status based on payments total vs invoice grand_total.
        """
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

    # 🆕 Item-wise tax & discount
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
