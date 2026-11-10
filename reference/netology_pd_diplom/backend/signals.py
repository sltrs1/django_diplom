from typing import Type
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created
from backend.models import ConfirmEmailToken, User
from backend.tasks import send_email

new_user_registered = Signal()
new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """Отправляем письмо с токеном для сброса пароля."""
    send_email.delay(
        subject=f"Password Reset Token for {reset_password_token.user}",
        message=reset_password_token.key,
        recipient_list=[reset_password_token.user.email],
    )


@receiver(post_save, sender=User)
def new_user_registered_signal(sender: Type[User], instance: User, created: bool, **kwargs):
    """Отправляем письмо с подтверждением почты."""
    if created and not instance.is_active:
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)
        send_email.delay(
            subject=f"Подтверждение почты для {instance.email}",
            message=token.key,
            recipient_list=[instance.email],
        )


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """Отправляем письмо при изменении статуса заказа."""
    user = User.objects.get(id=user_id)
    send_email.delay(
        subject="Обновление статуса заказа",
        message="Заказ сформирован",
        recipient_list=[user.email],
    )