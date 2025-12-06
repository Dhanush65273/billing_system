from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages

from .models import Customer
from .forms import CustomerForm


def customer_list(request):
    search = request.GET.get('search', '').strip()

    qs = Customer.objects.all().order_by('id')

    if search:
        qs = qs.filter(name__icontains=search)

    paginator = Paginator(qs, 10)  # 10 customers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
    }
    return render(request, 'customers/customer_list.html', context)


def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer added successfully.")
            return redirect('customer_list')
    else:
        form = CustomerForm()

    return render(
        request,
        'customers/customer_form.html',
        {'form': form, 'title': 'Add Customer'}
    )


def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer updated successfully.")
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)

    return render(
        request,
        'customers/customer_form.html',
        {'form': form, 'title': 'Edit Customer'}
    )


def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        customer.delete()
        messages.success(request, "Customer deleted successfully.")
        return redirect('customer_list')

    return render(
        request,
        'customers/customer_confirm_delete.html',
        {'customer': customer}
    )