from django.contrib import admin
from .models import Provider, AssistanceRequest


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("business_name", "service_type", "phone", "is_available")
    list_filter = ("service_type", "is_available")
    search_fields = ("business_name", "phone", "address")


@admin.register(AssistanceRequest)
class AssistanceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "service_needed", "status", "provider", "created_at")
    list_filter = ("status", "service_needed", "created_at")
    search_fields = ("customer__username", "vehicle", "issue_description", "phone")
    readonly_fields = ("created_at", "updated_at")
