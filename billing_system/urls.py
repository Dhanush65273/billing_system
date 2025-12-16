from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect


# 🔐 Custom Login View
class CustomLoginView(auth_views.LoginView):
    template_name = "registration/login.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


urlpatterns = [
    path("admin/", admin.site.urls),

    # LOGIN / LOGOUT
    path("", CustomLoginView.as_view(), name="login"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # APPS
    path("payments/", include("payments.urls")),
    path("customers/", include("customers.urls")),
    path("products/", include("products.urls")),
    path("invoices/", include("invoices.urls")),
]
