from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.views import (
    dashboard, server_stats_partial, tool_detail, install_tool
)
from core.plugin_system import plugin_registry

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('tool/<str:tool_name>/', tool_detail, name='tool_detail'),
    path('tool/<str:tool_name>/install/', install_tool, name='install_tool'),
    path('api/stats/', server_stats_partial, name='server_stats_partial'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
]

# Register module URLs
for module in plugin_registry.get_all_modules():
    urlpatterns += module.get_urls()
