from django import forms
from .models import ProductInfo, Order, OrderItem, Shop

class ImportProductsForm(forms.Form):
    """Форма для загрузки YAML-файла с товарами."""
    yaml_file = forms.FileField(
        label='YAML-файл',
        help_text='Выберите файл в формате YAML для импорта товаров.'
    )
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.all(),
        label='Магазин',
        help_text='Товары будут привязаны к выбранному магазину.'
    )

class UpdatePricesForm(forms.Form):
    """Форма для массового изменения цен (например, наценка в процентах)."""
    percent = forms.DecimalField(
        label='Наценка, %',
        max_digits=5,
        decimal_places=2,
        help_text='Укажите процент, на который нужно увеличить цену (может быть отрицательным).'
    )
    category = forms.ModelChoiceField(
        queryset=ProductInfo.objects.none(),  # будет заполнен в __init__
        label='Категория (необязательно)',
        required=False,
        help_text='Если выбрана, цены изменятся только для товаров этой категории.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Category
        self.fields['category'].queryset = Category.objects.all()

class CreateOrderForm(forms.ModelForm):
    """Форма для ручного создания заказа в админке."""
    class Meta:
        model = Order
        fields = ['user', 'contact', 'state']
        widgets = {
            'user': forms.Select(attrs={'class': 'admin-autocomplete'}),
            'contact': forms.Select(attrs={'class': 'admin-autocomplete'}),
        }

class OrderItemForm(forms.ModelForm):
    """Форма для добавления позиции в заказ."""
    class Meta:
        model = OrderItem
        fields = ['product_info', 'quantity']
        widgets = {
            'product_info': forms.Select(attrs={'class': 'admin-autocomplete'}),
        }
