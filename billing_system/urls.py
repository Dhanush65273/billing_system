from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔐 ROOT ALWAYS LOGIN
    path("", auth_views.LoginView.as_view(), name="login"),

    # AUTH
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # APPS
    path("payments/", include("payments.urls")),
    path("customers/", include("customers.urls")),
    path("products/", include("products.urls")),
    path("invoices/", include("invoices.urls")),
]
