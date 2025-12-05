from django.urls import path
from . import views

urlpatterns = [
    path("", views.payment_list, name="payment_list"),
    path("add/", views.payment_create, name="payment_add"),
    path("<int:pk>/delete/", views.payment_delete, name="payment_delete"),
]