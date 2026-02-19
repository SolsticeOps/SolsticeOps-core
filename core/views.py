import psutil
import platform
import cpuinfo
import os
import subprocess
import re
import threading
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.conf import settings
from .models import Tool
from .plugin_system import plugin_registry
from .utils import run_command

logger = logging.getLogger(__name__)

def _trigger_server_restart():
    """Helper to trigger a server reload/restart after adding a module."""
    try:
        # 1. Touch settings.py to trigger runserver/gunicorn reload if supported
        settings_file = os.path.join(settings.BASE_DIR, 'solstice_ops', 'settings.py')
        os.utime(settings_file, None)
        
        # 2. Try to restart via systemctl if running as a service
        # We do this in a separate thread to allow the current request to complete
        def restart_service():
            import time
            time.sleep(1) # Give some time for the redirect to be sent
            try:
                subprocess.run(['systemctl', 'restart', 'solstice-ops'], check=False)
            except:
                pass
        
        threading.Thread(target=restart_service).start()
    except Exception as e:
        logger.error(f"Error triggering restart: {e}")

def get_hw_info_sudo():
    """Fetches detailed HW info using sudo dmidecode."""
    cache_key = 'hw_info_sudo'
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    data = {'ram_slots': [], 'motherboard': 'Unknown'}
    try:
        # Motherboard
        mb_out = run_command(['dmidecode', '-s', 'baseboard-product-name'], timeout=2).decode().strip()
        if mb_out:
            data['motherboard'] = mb_out
        
        # RAM Slots
        ram_out = run_command(['dmidecode', '-t', 'memory'], timeout=2).decode()
        # Simple regex to find Size and Speed for each handle
        sizes = re.findall(r'Size: (\d+ [GM]B)', ram_out)
        speeds = re.findall(r'Configured Memory Speed: (\d+ MT/s)', ram_out)
        
        for i, size in enumerate(sizes):
            speed = speeds[i] if i < len(speeds) else "Unknown"
            data['ram_slots'].append({'slot': i, 'size': size, 'speed': speed})
    except:
        pass
    
    cache.set(cache_key, data, 3600) # Cache for 1 hour
    return data

def get_server_stats():
    cores_usage = psutil.cpu_percent(interval=None, percpu=True)
    
    # RAM segments
    vm = psutil.virtual_memory()
    ram_segments = [
        {'label': 'Used', 'val': vm.used, 'percent': (vm.used / vm.total) * 100, 'color': '#7c3aed'},
    ]
    if hasattr(vm, 'buffers') and hasattr(vm, 'cached'):
        cached_pct = ((vm.buffers + vm.cached) / vm.total) * 100
        ram_segments.append({'label': 'Cache/Buff', 'val': vm.buffers + vm.cached, 'percent': cached_pct, 'color': '#d8b4fe'})
    
    # Disk segments (partitions)
    disks = []
    seen_devices = set()
    for part in psutil.disk_partitions(all=False):
        if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
            continue
        # Filter out loop devices
        if part.device.startswith('/dev/loop'):
            continue
        # Filter out duplicate devices
        if part.device in seen_devices:
            continue
            
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                'device': part.device,
                'mount': part.mountpoint,
                'percent': usage.percent,
                'total_gb': round(usage.total / (1024**3), 1)
            })
            seen_devices.add(part.device)
        except PermissionError:
            continue

    return {
        'cpu_usage': psutil.cpu_percent(interval=None),
        'cpu_cores_usage': cores_usage,
        'cpu_cores_count': len(cores_usage),
        'ram_usage': vm.percent,
        'ram_segments': ram_segments,
        'disks_usage': disks,
        'disks_count': len(disks),
        'disk_usage': psutil.disk_usage('/').percent,
    }

@login_required
def dashboard(request):
    # Hardware Info (cached or static)
    cache_key = 'cpu_info_brand'
    cpu_brand = cache.get(cache_key)
    if not cpu_brand:
        try:
            info = cpuinfo.get_cpu_info()
            cpu_brand = info.get('brand_raw', 'Unknown')
            cache.set(cache_key, cpu_brand, 86400) # Cache for 24 hours
        except:
            cpu_brand = "Unknown"
    
    hw_sudo = get_hw_info_sudo()
    context = {
        'server_info': {
            'os': platform.system(),
            'os_release': platform.release(),
            'cpu_brand': cpu_brand,
            'cpu_count': psutil.cpu_count(),
            'cpu_threads': psutil.cpu_count(logical=True),
            'ram_total': round(psutil.virtual_memory().total / (1024**3), 2),
            'motherboard': hw_sudo['motherboard'],
            'ram_slots': hw_sudo['ram_slots'],
        },
        'stats': get_server_stats(),
        'is_login_page': False,
        'is_admin': False
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def server_stats_partial(request):
    return render(request, 'core/partials/stats.html', {'stats': get_server_stats()})

@login_required
def tool_detail(request, tool_name):
    tool = get_object_or_404(Tool, name=tool_name)
    module = plugin_registry.get_module(tool.name)
    context = {
        'tool': tool,
        'is_login_page': False,
        'is_admin': False,
    }

    if module:
        # Get module specific context with caching
        # Include tab in cache key for HTMX requests
        target = request.GET.get('tab')
        is_hx = request.headers.get('HX-Request')
        
        cache_key = f'module_context_{tool.name}_{request.user.id}'
        if is_hx and target:
            cache_key += f'_{target}'
            # For namespace-specific requests
            namespace = request.GET.get('namespace')
            if namespace:
                cache_key += f'_{namespace}'
        
        module_context = cache.get(cache_key)
            
        if module_context is None:
            module_context = module.get_context_data(request, tool)
            try:
                # Cache for 30s for page loads, 5s for HTMX refreshes
                ttl = 5 if is_hx else 30
                cache.set(cache_key, module_context, ttl)
            except Exception as e:
                logger.warning(f"Failed to cache module context for {tool.name}: {e}")
        
        context.update(module_context)

        # Update tool status based on actual service status
        service_status = module.get_service_status(tool)
        context['service_status'] = service_status
        
        # Add dynamic module properties to context
        context['resource_tabs'] = module.get_resource_tabs()
        context['module'] = module
        context['service_version'] = module.get_service_version() or tool.version

        # Handle HTMX requests
        if is_hx:
            if target == 'status':
                return render(request, 'core/partials/tool_status.html', context)
            
            response = module.handle_hx_request(request, tool, target)
            if response:
                return response
            
            return HttpResponse("", status=204)

    return render(request, 'core/tool_detail.html', context)

@login_required
def install_tool(request, tool_name):
    tool = get_object_or_404(Tool, name=tool_name)
    module = plugin_registry.get_module(tool.name)
    
    if module and hasattr(module, 'install'):
        module.install(request, tool)
        
    return redirect('tool_detail', tool_name=tool_name)

@login_required
def tool_action(request, tool_name, action):
    tool = get_object_or_404(Tool, name=tool_name)
    module = plugin_registry.get_module(tool.name)
    
    if action not in ['start', 'stop', 'restart']:
        return HttpResponse("Invalid action", status=400)
    
    # Try to execute action via module if it has custom implementation
    action_method_name = f"service_{action}"
    if module and hasattr(module, action_method_name):
        getattr(module, action_method_name)(tool)
    else:
        # Default implementation using systemctl
        try:
            run_command(['systemctl', action, tool.name])
        except Exception as e:
            # If systemctl fails, maybe it's not a systemd service
            # We could log this or handle differently
            pass
            
    # Clear cache for this module to reflect changes immediately
    cache_key = f'module_context_{tool.name}_{request.user.id}'
    cache.delete(cache_key)
    
    return redirect('tool_detail', tool_name=tool_name)

@login_required
def add_module(request):
    if request.method == 'POST':
        repo_url = request.POST.get('repo_url')
        if repo_url:
            try:
                # Basic validation: ensure it looks like a git URL
                if not repo_url.endswith('.git') and 'github.com' not in repo_url:
                    return HttpResponse("Invalid repository URL", status=400)
                
                # Extract module name from URL
                module_name = repo_url.split('/')[-1].replace('.git', '').replace('SolsticeOps-', '').lower()
                module_path = os.path.join('modules', module_name)
                
                if os.path.exists(module_path):
                    # If directory exists, try to initialize it in case it's an uninitialized submodule
                    try:
                        run_command(['git', 'submodule', 'update', '--init', module_path], timeout=300)
                        
                        # Install dependencies if requirements.txt exists
                        req_path = os.path.join(module_path, 'requirements.txt')
                        if os.path.exists(req_path):
                            # Use the python from the virtual environment to run pip
                            venv_pip = os.path.join(settings.BASE_DIR, '.venv', 'bin', 'pip')
                            if os.path.exists(venv_pip):
                                run_command([venv_pip, 'install', '-r', req_path], timeout=300)
                        
                        plugin_registry.discover_modules()
                        plugin_registry.sync_tools_with_db(force=True)
                        _trigger_server_restart()
                        
                        return redirect('dashboard')
                    except Exception as e:
                        return HttpResponse(f"Module '{module_name}' already exists and could not be initialized: {str(e)}", status=400)
                
                # Use git submodule add
                try:
                    run_command(['git', 'submodule', 'add', repo_url, module_path], timeout=300)
                except Exception as e:
                    # If 'add' fails because it's already in .gitmodules but not on disk
                    if "already exists in the index" in str(e):
                        run_command(['git', 'submodule', 'update', '--init', module_path], timeout=300)
                    else:
                        raise e
                
                # Trigger module discovery
                plugin_registry.discover_modules()
                plugin_registry.sync_tools_with_db(force=True)
                _trigger_server_restart()
                
                return redirect('dashboard')
            except Exception as e:
                return HttpResponse(f"Error adding module: {str(e)}", status=500)
    return redirect('dashboard')
