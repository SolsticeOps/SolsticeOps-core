import psutil
import platform
import cpuinfo
import os
import subprocess
import re
import threading
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Tool
from .plugin_system import plugin_registry

def get_hw_info_sudo():
    """Fetches detailed HW info using sudo dmidecode."""
    data = {'ram_slots': [], 'motherboard': 'Unknown'}
    try:
        # Motherboard
        mb_out = subprocess.check_output(['sudo', 'dmidecode', '-s', 'baseboard-product-name'], stderr=subprocess.DEVNULL).decode().strip()
        if mb_out:
            data['motherboard'] = mb_out
        
        # RAM Slots
        ram_out = subprocess.check_output(['sudo', 'dmidecode', '-t', 'memory'], stderr=subprocess.DEVNULL).decode()
        # Simple regex to find Size and Speed for each handle
        sizes = re.findall(r'Size: (\d+ [GM]B)', ram_out)
        speeds = re.findall(r'Configured Memory Speed: (\d+ MT/s)', ram_out)
        
        for i, size in enumerate(sizes):
            speed = speeds[i] if i < len(speeds) else "Unknown"
            data['ram_slots'].append({'slot': i, 'size': size, 'speed': speed})
    except:
        pass
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
    for part in psutil.disk_partitions(all=False):
        if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                'device': part.device,
                'mount': part.mountpoint,
                'percent': usage.percent,
                'total_gb': round(usage.total / (1024**3), 1)
            })
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
    info = cpuinfo.get_cpu_info()
    
    hw_sudo = get_hw_info_sudo()
    context = {
        'server_info': {
            'os': platform.system(),
            'os_release': platform.release(),
            'cpu_brand': info.get('brand_raw', 'Unknown'),
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
        # Get module specific context
        module_context = module.get_context_data(request, tool)
        context.update(module_context)
        
        # Add dynamic module properties to context
        context['resource_tabs'] = module.get_resource_tabs()
        context['module'] = module
        context['service_version'] = module.get_service_version() or tool.version

        # Handle HTMX requests
        if request.headers.get('HX-Request'):
            target = request.GET.get('tab')
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
    
    if module:
        module.install(request, tool)
        
    return redirect('tool_detail', tool_name=tool_name)
