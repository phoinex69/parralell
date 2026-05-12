from django.urls import path

from .views import (
    CheckoutView,
    HealthView,
    LoginView,
    OrderListView,
    ProductDetailView,
    ProductListView,
    RegisterView,
    StockUpdateView,
    TaskResultListView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<int:product_id>/", ProductDetailView.as_view(), name="product-detail"),
    path("products/<int:product_id>/stock/", StockUpdateView.as_view(), name="stock-update"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("tasks/results/", TaskResultListView.as_view(), name="task-result-list"),
]
