# backend/admin.py
from django.contrib import admin
from django.urls import path

from . import admin_views
from .models import (
    Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter,
    Contact, Order, OrderItem,
)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'user')
    list_filter = ('state',)
    search_fields = ('name',)
    change_list_template = 'admin/backend/shop/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-products/',
                self.admin_site.admin_view(admin_views.ImportProductsView.as_view()),
                name='shop-import-products',
            ),
        ]
        return custom_urls + urls


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)

@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ('product', 'shop', 'price', 'price_rrc', 'quantity')
    list_filter = ('shop', 'product__category')
    search_fields = ('product__name',)
    list_select_related = ('product', 'shop')
    change_list_template = 'admin/backend/productinfo/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'update-prices/',
                self.admin_site.admin_view(admin_views.UpdatePricesView.as_view()),
                name='productinfo-update-prices',
            ),
            path(
                'stock-report/',
                self.admin_site.admin_view(admin_views.StockReportView.as_view()),
                name='productinfo-stock-report',
            ),
        ]
        return custom_urls + urls


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    list_display = ('product_info', 'parameter', 'value')
    list_filter = ('parameter',)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'street', 'phone')
    search_fields = ('user__username', 'phone')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'state', 'dt')
    list_filter = ('state',)
    search_fields = ('user__username',)
    change_list_template = 'admin/backend/order/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'create-order/',
                self.admin_site.admin_view(admin_views.CreateOrderView.as_view()),
                name='order-create',
            ),
        ]
        return custom_urls + urls


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_info', 'quantity')
    list_filter = ('order__state',)