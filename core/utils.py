import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def run_sudo_command(cmd, input_data=None, timeout=30, capture_output=True, shell=False, env=None, log_errors=True):
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
