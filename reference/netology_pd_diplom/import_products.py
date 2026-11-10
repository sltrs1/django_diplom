import os
import django
import yaml

# Настраиваем окружение
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netology_pd_diplom.settings')
django.setup()

from backend.models import (
    Shop, Category, Product, ProductInfo, Parameter, ProductParameter
)

def import_shop_from_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)

    # 1. Создаём или получаем магазин
    shop_name = data.get('shop')
    if not shop_name:
        print("В файле отсутствует поле 'shop'. Импорт прерван.")
        return

    shop, created = Shop.objects.get_or_create(name=shop_name)
    if created:
        print(f"Создан магазин: {shop.name}")
    else:
        print(f"Магазин уже существует: {shop.name}")

    # 2. Обрабатываем категории
    # YAML содержит список категорий с полями id и name.
    # В модели Category нет поля для внешнего id, поэтому
    # используем name как уникальный идентификатор.
    categories_map = {}  # сопоставляем id из YAML с объектами Category
    for cat_data in data.get('categories', []):
        category, _ = Category.objects.get_or_create(name=cat_data['name'])
        category.shops.add(shop)  # привязываем категорию к магазину
        categories_map[cat_data['id']] = category
        print(f"Категория: {category.name}")

    # 3. Обрабатываем товары
    for good in data.get('goods', []):
        # Находим категорию по id из YAML
        category = categories_map.get(good['category'])
        if not category:
            print(f"Категория с id={good['category']} не найдена, товар пропущен.")
            continue

        # Создаём или получаем продукт
        # Уникальность продукта определяется названием и категорией
        product, _ = Product.objects.get_or_create(
            name=good['name'],
            category=category
        )

        # Создаём или обновляем информацию о товаре в магазине
        product_info, _ = ProductInfo.objects.update_or_create(
            product=product,
            shop=shop,
            external_id=good['id'],
            defaults={
                'model': good.get('model', ''),
                'quantity': good.get('quantity', 0),
                'price': good.get('price', 0),
                'price_rrc': good.get('price_rrc', 0),
            }
        )

        # 4. Обрабатываем параметры товара
        # Параметры в YAML — это словарь, где ключ — название параметра,
        # а значение — его значение.
        for param_name, param_value in good.get('parameters', {}).items():
            # Приводим значение к строке, так как поле value в модели — CharField
            value_str = str(param_value)

            parameter, _ = Parameter.objects.get_or_create(name=param_name)

            # Обновляем или создаём связь параметра с товаром
            ProductParameter.objects.update_or_create(
                product_info=product_info,
                parameter=parameter,
                defaults={'value': value_str}
            )

    print("Импорт завершён успешно.")

if __name__ == '__main__':
    import_shop_from_yaml('backend/fixtures/shop1.yaml')