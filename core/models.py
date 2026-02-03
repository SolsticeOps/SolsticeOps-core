from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import Media

class User(AbstractUser):
    """Custom user model for SolsticeOps."""
    is_devops_admin = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username

class Tool(models.Model):
    """Model representing a DevOps tool/service."""
    
    STATUS_CHOICES = [
        ('not_installed', 'Not Installed'),
        ('installing', 'Installing'),
        ('installed', 'Installed'),
        ('error', 'Error'),
    ]

    name = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_installed')
    version = models.CharField(max_length=50, blank=True, null=True)
    current_stage = models.CharField(max_length=255, blank=True, null=True)
    config_data = models.JSONField(default=dict, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_name_display()

    def get_name_display(self):
        from .plugin_system import plugin_registry
        module = plugin_registry.get_module(self.name)
        if module:
            return module.module_name
        return self.name.capitalize()

    def get_icon_class(self):
        from .plugin_system import plugin_registry
        module = plugin_registry.get_module(self.name)
        if module:
            return module.get_icon_class()
        return self.name

    def get_custom_icon_svg(self):
        from .plugin_system import plugin_registry
        module = plugin_registry.get_module(self.name)
        if module:
            return module.get_custom_icon_svg()
        return None
