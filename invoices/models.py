from django.db import models
from customers.models import Customer
from products.models import Product


class Invoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    invoice_date = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def _str_(self):
        return f"Invoice {self.id} - {self.customer.name}"
    

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        related_name="items",
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)   # one item price
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # qty * price

    def _str_(self):
        return f"{self.product.name} x {self.quantity}"