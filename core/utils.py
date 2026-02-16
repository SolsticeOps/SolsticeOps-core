import subprocess
import os
import logging
import socket

logger = logging.getLogger(__name__)

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
