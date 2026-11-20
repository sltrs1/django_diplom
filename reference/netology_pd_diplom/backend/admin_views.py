import logging
import uuid
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView

from .forms import CreateOrderForm, ImportProductsForm, OrderItemForm, UpdatePricesForm
from .models import Order, OrderItem, ProductInfo
from .tasks import do_import

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 МБ


@method_decorator(staff_member_required, name="dispatch")
class ImportProductsView(FormView):
    template_name = "admin/backend/import_products.html"
    form_class = ImportProductsForm

    def get_success_url(self):
        return reverse("admin:backend_shop_changelist")

    def form_valid(self, form):
        yaml_file = form.cleaned_data["yaml_file"]

        # ---- 1. Валидация размера --------------------------------------
        if yaml_file.size == 0:
            form.add_error("yaml_file", "Файл пустой.")
            return self.form_invalid(form)
        if yaml_file.size > MAX_UPLOAD_SIZE:
            form.add_error(
                "yaml_file",
                f"Размер файла не должен превышать "
                f"{MAX_UPLOAD_SIZE // (1024 * 1024)} МБ.",
            )
            return self.form_invalid(form)

        # ---- 2. Сохранение файла в media/imports/ ----------------------
        # UUID в имени гарантирует уникальность и не даёт перезаписать
        # ранее загруженный файл с тем же именем.
        filename = f"imports/{uuid.uuid4().hex}_{yaml_file.name}"
        try:
            saved_path = default_storage.save(filename, yaml_file)
        except Exception as exc:
            logger.exception("Не удалось сохранить YAML-файл: %s", filename)
            form.add_error(None, f"Не удалось сохранить файл: {exc}")
            return self.form_invalid(form)

        logger.info(
            "Import file saved: path=%s size=%s user=%s",
            saved_path,
            yaml_file.size,
            self.request.user.username,
        )

        # ---- 3. Постановка задачи в Celery ----------------------------
        try:
            # 3a. URL, который увидит браузер (для отладки/логов)
            external_url = self.request.build_absolute_uri(
                f"{settings.MEDIA_URL}{saved_path}"
            )
            # 3b. URL, по которому задача достучится до web-контейнера
            internal_host = getattr(settings, "CELERY_IMPORT_HOST", "web")
            internal_url = self._replace_host(external_url, internal_host)

            logger.info(
                "Dispatching do_import: external=%s internal=%s user_id=%s",
                external_url,
                internal_url,
                self.request.user.id,
            )

            task = do_import.delay(internal_url, self.request.user.id)
        except Exception as exc:
            # Откат: удаляем уже сохранённый файл, чтобы не копить мусор
            logger.exception("Не удалось поставить do_import в очередь")
            try:
                default_storage.delete(saved_path)
            except Exception:
                logger.exception("Не удалось удалить YAML после ошибки: %s", saved_path)
            form.add_error(
                None,
                f"Не удалось поставить задачу в очередь: {exc}. "
                f"Проверьте, что Redis и Celery-воркер запущены.",
            )
            return self.form_invalid(form)

        # ---- 4. Уведомление администратора ----------------------------
        messages.success(
            self.request,
            f"Импорт поставлен в очередь. ID задачи: {task.id}. "
            f"Статус выполнения — в разделе «Celery Results» "
            f"или в логах контейнера celery.",
        )
        return super().form_valid(form)

    @staticmethod
    def _replace_host(url: str, new_host: str) -> str:
        """Заменяет хост в URL, сохраняя схему, порт и путь.

        Пример:
            _replace_host('http://localhost:8000/media/x.yaml', 'web')
            → 'http://web:8000/media/x.yaml'
        """
        parsed = urlparse(url)
        netloc = f"{new_host}:{parsed.port}" if parsed.port else new_host
        return urlunparse(parsed._replace(netloc=netloc))


@method_decorator(staff_member_required, name="dispatch")
class UpdatePricesView(FormView):
    template_name = "admin/backend/update_prices.html"
    form_class = UpdatePricesForm
    success_url = "/admin/backend/productinfo/"

    def form_valid(self, form):
        percent = form.cleaned_data["percent"]
        category = form.cleaned_data["category"]
        qs = ProductInfo.objects.all()
        if category:
            qs = qs.filter(product__category=category)
        for info in qs:
            info.price = int(info.price * (1 + percent / 100))
            info.price_rrc = int(info.price_rrc * (1 + percent / 100))
            info.save()
        messages.success(self.request, f"Цены обновлены для {qs.count()} записей.")
        return super().form_valid(form)


@method_decorator(staff_member_required, name="dispatch")
class CreateOrderView(FormView):
    template_name = "admin/backend/create_order.html"
    form_class = CreateOrderForm
    success_url = "/admin/backend/order/"

    def form_valid(self, form):
        order = form.save()
        messages.success(self.request, f"Заказ #{order.id} создан.")
        return redirect("admin:backend_order_change", order.id)


@method_decorator(staff_member_required, name="dispatch")
class StockReportView(TemplateView):
    template_name = "admin/backend/stock_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = (
            ProductInfo.objects.select_related("product", "shop", "product__category")
            .prefetch_related("product_parameters__parameter")
            .order_by("shop__name", "product__name")
        )
        rows = []
        for info in qs:
            params = {
                pp.parameter.name: pp.value for pp in info.product_parameters.all()
            }
            rows.append(
                {
                    "id": info.id,
                    "product_name": info.product.name,
                    "category": info.product.category.name
                    if info.product.category
                    else "—",
                    "shop": info.shop.name,
                    "price": info.price,
                    "price_rrc": info.price_rrc,
                    "quantity": info.quantity,
                    "article": params.get("article", "—"),
                    "model": params.get("model", "—"),
                }
            )
        context["rows"] = rows
        context["total"] = len(rows)
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = ProductInfo.objects.select_related(
            "product", "shop"
        ).all()
        return context
