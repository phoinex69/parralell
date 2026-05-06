from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("products/", views.product_list, name="product-list"),
    path("products/<int:product_id>/", views.product_detail, name="product-detail"),
    path("checkout/", views.checkout, name="checkout"),
    path("tasks/", views.task_list, name="task-list"),
]
