"""Integrate with admin module."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as OriginalUserAdmin
from django.utils.translation import gettext_lazy as _
from django_celery_beat.admin import PeriodicTaskAdmin as OriginalPeriodicTaskAdmin
from django_celery_beat.models import PeriodicTask

from .models import User


@admin.register(User)
class UserAdmin(OriginalUserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    list_display = ("email", "first_name", "last_name", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("id",)


class PeriodicTaskAdmin(OriginalPeriodicTaskAdmin):
    list_filter = ()


admin.site.unregister(PeriodicTask)
admin.site.register(PeriodicTask, PeriodicTaskAdmin)
