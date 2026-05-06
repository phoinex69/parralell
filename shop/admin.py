from django.contrib import admin

from .models import BackgroundTask, Order, OrderItem, Product


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "stock_quantity", "version")
    search_fields = ("name",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_email", "status", "total_amount", "created_at")
    inlines = [OrderItemInline]


@admin.register(BackgroundTask)
class BackgroundTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "status", "attempts", "created_at", "updated_at")
    list_filter = ("kind", "status")

# Register your models here.
