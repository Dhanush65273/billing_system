from django.urls import path
from . import views

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("add/", views.product_add, name="product_add"),
    path("edit/<int:pk>/", views.product_edit, name="product_edit"),
    path("delete/<int:pk>/", views.product_delete, name="product_delete"),
]