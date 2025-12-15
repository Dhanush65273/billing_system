from django.db import models

# products/models.py

class Product(models.Model):
    name = models.CharField(max_length=100)

    sku = models.CharField(
        max_length=50,
        unique=True
    )  # 🔥 NEW FIELD

    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"
