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

    @property
    def get_name_display(self):
        from .plugin_system import plugin_registry
        module = plugin_registry.get_module(self.name)
        if module:
            return module.module_name
        return self.name.capitalize()

    @property
    def get_icon_class(self):
        from .plugin_system import plugin_registry
        module = plugin_registry.get_module(self.name)
        if module:
            return module.get_icon_class()
        return self.name

class DockerRegistry(models.Model):
    """Model representing a Docker registry."""
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=255, help_text="Registry URL (e.g., index.docker.io/v1/)")
    username = models.CharField(max_length=100, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True, help_text="Password or API Token")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
