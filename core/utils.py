import subprocess
import os
import logging
import socket

logger = logging.getLogger(__name__)

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

def devops_admin_required(view_func):
    """
    Decorator for views that checks if the user is a DevOps admin or a system admin (staff/superuser).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.can_manage_infrastructure:
            return view_func(request, *args, **kwargs)
        
        if request.headers.get('HX-Request'):
            from django.http import HttpResponse
            return HttpResponse('<div class="alert alert-danger mb-0">Permission denied: DevOps Admin role required.</div>', status=403)
            
        messages.error(request, "You do not have permission to perform this action. DevOps Admin role required.")
        # Try to redirect back to referer or dashboard
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('dashboard')
    return _wrapped_view

def get_primary_ip():
    """
    Returns the primary IP address of the machine by attempting to connect to an external address.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def paginate_list(items, page, per_page, search_query=None, search_fields=None):
    """
    Paginates and filters a list of objects or dictionaries.
    """
    if search_query and search_fields:
        query = search_query.lower()
        filtered_items = []
        for item in items:
            match = False
            for field in search_fields:
                val = item
                # Handle nested access (e.g. 'metadata.name')
                for part in field.split('.'):
                    if isinstance(val, dict):
                        val = val.get(part, '')
                    else:
                        val = getattr(val, part, '')
                
                if query in str(val).lower():
                    match = True
                    break
            if match:
                filtered_items.append(item)
        items = filtered_items

    total_items = len(items)
    try:
        page = int(page)
        per_page = int(per_page)
    except (ValueError, TypeError):
        page = 1
        per_page = 10

    if per_page <= 0:
        per_page = 10
        
    total_pages = (total_items + per_page - 1) // per_page
    if page > total_pages:
        page = max(1, total_pages)
    
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        'items': items[start:end],
        'total_items': total_items,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
        'next_page': page + 1,
        'prev_page': page - 1,
    }

def run_command(cmd, input_data=None, timeout=30, capture_output=True, shell=False, env=None, log_errors=True):
    """
    Runs a command. Assumes the application is already running as root.
    """
    try:
        if capture_output:
            return subprocess.check_output(cmd, input=input_data, stderr=subprocess.STDOUT, timeout=timeout, shell=shell, env=env)
        else:
            return subprocess.run(cmd, input=input_data, stderr=subprocess.STDOUT, timeout=timeout, check=True, shell=shell, env=env)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        if log_errors and hasattr(e, 'output') and e.output:
            output_str = e.output.decode().strip()
            # Suppress common status-related "non-errors"
            if output_str not in ['inactive', 'failed', 'deactivating', 'not-found']:
                logger.error(f"Command failed: {output_str}")
        raise e
