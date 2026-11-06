from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Computer, IssueCategory, Location, MaintenanceRequest, Notification, RequestUpdate, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("System role", {"fields": ("role", "department")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("System role", {"fields": ("role", "department")}),)
    list_display = ("username", "first_name", "last_name", "role", "is_active")


admin.site.register([Location, Computer, IssueCategory, MaintenanceRequest, RequestUpdate, Notification])
