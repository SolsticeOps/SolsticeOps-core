from django.contrib import admin

admin.site.site_header = "SolsticeOps Administration"
admin.site.index_title = "Infrastructure Management"
from django.contrib.auth.admin import UserAdmin
from .models import User, Tool

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Fields', {'fields': ('is_devops_admin',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extra Fields', {'fields': ('is_devops_admin',)}),
    )
    list_display = ['username', 'email', 'is_devops_admin', 'is_staff']

@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'version', 'last_updated']
    list_filter = ['status']
    search_fields = ['name']
