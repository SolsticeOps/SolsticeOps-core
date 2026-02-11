import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def run_sudo_command(cmd, input_data=None, timeout=30, capture_output=True, shell=False, env=None, log_errors=True):
    """
    Runs a command with sudo, optionally providing a password from .env.
    """
    sudo_password = os.environ.get('SUDO_PASSWORD')
    
    if shell:
        # For shell=True, we wrap the command with sudo
        if sudo_password:
            # Note: shell=True with sudo -S is tricky. We'll use a pipe.
            full_cmd = f"echo '{sudo_password}' | sudo -S {cmd}"
        else:
            full_cmd = f"sudo -n {cmd}"
        
        try:
            if capture_output:
                return subprocess.check_output(full_cmd, input=input_data, stderr=subprocess.STDOUT, timeout=timeout, shell=True, env=env)
            else:
                return subprocess.run(full_cmd, input=input_data, stderr=subprocess.STDOUT, timeout=timeout, check=True, shell=True, env=env)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if log_errors and hasattr(e, 'output') and e.output:
                output_str = e.output.decode().strip()
                # Suppress common status-related "non-errors"
                if output_str not in ['inactive', 'failed', 'deactivating', 'not-found']:
                    logger.error(f"Sudo shell command failed: {output_str}")
            raise e
    else:
        # cmd should be a list
        if not isinstance(cmd, list):
            cmd = [cmd]

        # Remove 'sudo' from cmd if it's already there at the beginning
        if cmd and cmd[0] == 'sudo':
            cmd = cmd[1:]

        if sudo_password:
            # Use -S to read password from stdin
            full_cmd = ['sudo', '-S'] + cmd
            
            password_prefix = f"{sudo_password}\n".encode()
            if input_data:
                if isinstance(input_data, str):
                    input_data = input_data.encode()
                combined_input = password_prefix + input_data
            else:
                combined_input = password_prefix
            
            try:
                if capture_output:
                    return subprocess.check_output(full_cmd, input=combined_input, stderr=subprocess.STDOUT, timeout=timeout, env=env)
                else:
                    return subprocess.run(full_cmd, input=combined_input, stderr=subprocess.STDOUT, timeout=timeout, check=True, env=env)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                if log_errors and hasattr(e, 'output') and e.output:
                    output_str = e.output.decode().strip()
                    # Suppress common status-related "non-errors"
                    if output_str not in ['inactive', 'failed', 'deactivating', 'not-found']:
                        logger.error(f"Sudo command failed: {output_str}")
                raise e
        else:
            # Fallback to non-interactive sudo
            full_cmd = ['sudo', '-n'] + cmd
            try:
                if capture_output:
                    return subprocess.check_output(full_cmd, input=input_data, stderr=subprocess.STDOUT, timeout=timeout, env=env)
                else:
                    return subprocess.run(full_cmd, input=input_data, stderr=subprocess.STDOUT, timeout=timeout, check=True, env=env)
            except subprocess.CalledProcessError as e:
                # If it failed due to password requirement, log a helpful message
                if log_errors and e.returncode == 1 and "sudo: a password is required" in (e.output.decode() if e.output else ""):
                    logger.warning("Sudo command failed because a password is required and SUDO_PASSWORD is not set in .env")
                raise e
