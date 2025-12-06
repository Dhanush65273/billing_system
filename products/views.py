from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages

from .models import Product
from .forms import ProductForm


def product_list(request):
    search = request.GET.get('search', '').strip()

    qs = Product.objects.all().order_by('id')

    if search:
        qs = qs.filter(name__icontains=search)

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
    }
    return render(request, 'products/product_list.html', context)


def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added successfully.")
            return redirect('product_list')
    else:
        form = ProductForm()

    return render(
        request,
        'products/product_form.html',
        {'form': form, 'title': 'Add Product'}
    )


def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        'products/product_form.html',
        {'form': form, 'title': 'Edit Product'}
    )


def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted successfully.")
        return redirect('product_list')

    return render(
        request,
        'products/product_confirm_delete.html',
        {'product': product}
    )