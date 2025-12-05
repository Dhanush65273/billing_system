from django.shortcuts import render, redirect, get_object_or_404
from .models import Product
from .forms import ProductForm

def product_list(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "products/product_list.html", {"products": products})

def product_add(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("product_list")
    else:
        form = ProductForm()
    return render(request, "products/product_form.html", {"form": form, "title": "Add Product"})

def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect("product_list")
    else:
        form = ProductForm(instance=product)
    return render(request, "products/product_form.html", {"form": form, "title": "Edit Product"})

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect("product_list")