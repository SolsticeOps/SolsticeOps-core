import json
import logging
import os
from .utils import run_command

logger = logging.getLogger(__name__)

def get_kubeconfig():
    """Returns the path to the kubeconfig file if it exists and is accessible by the current process."""
    paths = [
        '/etc/kubernetes/admin.conf',
        '/etc/rancher/k3s/k3s.yaml',
        '/var/snap/microk8s/current/credentials/client.config',
        os.path.expanduser('~/.kube/config'),
        '/root/.kube/config'
    ]
    for p in paths:
        if os.path.exists(p) and os.access(p, os.R_OK) and os.path.getsize(p) > 0:
            return p
    return None

class K8sObject:
    def __init__(self, attrs):
        self.attrs = attrs

    def __getattr__(self, item):
        try:
            attrs = object.__getattribute__(self, 'attrs')
        except AttributeError:
            raise AttributeError(item)

        if item == 'name':
            return attrs.get('metadata', {}).get('name')
        if item == 'namespace':
            return attrs.get('metadata', {}).get('namespace')
        if item == 'uid':
            return attrs.get('metadata', {}).get('uid')
        
        if item in attrs:
            return attrs[item]
            
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

class Pod(K8sObject):
    @property
    def status(self):
        return self.attrs.get('status', {}).get('phase', 'unknown')

    def logs(self, tail=None, timestamps=False):
        cmd = ['kubectl', 'logs', self.name]
        if self.namespace:
            cmd.extend(['-n', self.namespace])
        if tail:
            cmd.extend(['--tail', str(tail)])
        if timestamps:
            cmd.append('--timestamps')
        
        env = os.environ.copy()
        kconfig = get_kubeconfig()
        if kconfig:
            env['KUBECONFIG'] = kconfig
        return run_command(cmd, env=env)

class Deployment(K8sObject):
    @property
    def replicas(self):
        return self.attrs.get('spec', {}).get('replicas', 0)

class Service(K8sObject):
    pass

class Node(K8sObject):
    pass

class ConfigMap(K8sObject):
    pass

class Secret(K8sObject):
    pass

class Event(K8sObject):
    pass

class Manager:
    def __init__(self, resource_type, cls):
        self.resource_type = resource_type
        self.cls = cls

    def _get_env(self):
        env = os.environ.copy()
        kconfig = get_kubeconfig()
        if kconfig:
            env['KUBECONFIG'] = kconfig
        return env

    def list(self, namespace=None, all_namespaces=False):
        cmd = ['kubectl', 'get', self.resource_type, '-o', 'json']
        if all_namespaces:
            cmd.append('-A')
        elif namespace:
            cmd.extend(['-n', namespace])
        
        try:
            output = run_command(cmd, env=self._get_env())
            data = json.loads(output)
            return [self.cls(item) for item in data.get('items', [])]
        except:
            return []

    def get(self, name, namespace=None):
        cmd = ['kubectl', 'get', self.resource_type, name, '-o', 'json']
        if namespace:
            cmd.extend(['-n', namespace])
        try:
            output = run_command(cmd, env=self._get_env(), log_errors=False)
            if output:
                return self.cls(json.loads(output))
        except:
            pass
        return None

    def delete(self, name, namespace=None):
        cmd = ['kubectl', 'delete', self.resource_type, name]
        if namespace:
            cmd.extend(['-n', namespace])
        run_command(cmd, env=self._get_env())

class PodManager(Manager):
    def __init__(self):
        super().__init__('pod', Pod)

class DeploymentManager(Manager):
    def __init__(self):
        super().__init__('deployment', Deployment)
    
    def scale(self, name, replicas, namespace=None):
        cmd = ['kubectl', 'scale', 'deployment', name, f'--replicas={replicas}']
        if namespace:
            cmd.extend(['-n', namespace])
        run_command(cmd, env=self._get_env())

    def restart(self, name, namespace=None):
        cmd = ['kubectl', 'rollout', 'restart', 'deployment', name]
        if namespace:
            cmd.extend(['-n', namespace])
        run_command(cmd, env=self._get_env())

class ServiceManager(Manager):
    def __init__(self):
        super().__init__('service', Service)

class NodeManager(Manager):
    def __init__(self):
        super().__init__('node', Node)

class ConfigMapManager(Manager):
    def __init__(self):
        super().__init__('configmap', ConfigMap)

class SecretManager(Manager):
    def __init__(self):
        super().__init__('secret', Secret)

class EventManager(Manager):
    def __init__(self):
        super().__init__('event', Event)

class K8sCLI:
    def __init__(self):
        self.pods = PodManager()
        self.deployments = DeploymentManager()
        self.services = ServiceManager()
        self.nodes = NodeManager()
        self.configmaps = ConfigMapManager()
        self.secrets = SecretManager()
        self.events = EventManager()

    def info(self):
        try:
            env = os.environ.copy()
            kconfig = get_kubeconfig()
            if kconfig:
                env['KUBECONFIG'] = kconfig
            output = run_command(['kubectl', 'version', '-o', 'json'], env=env)
            return json.loads(output)
        except:
            return {}

    def get_context(self):
        try:
            env = os.environ.copy()
            kconfig = get_kubeconfig()
            if kconfig:
                env['KUBECONFIG'] = kconfig
            output = run_command(['kubectl', 'config', 'current-context'], env=env)
            return output.decode().strip()
        except:
            return 'N/A'

    def get_namespaces(self):
        try:
            env = os.environ.copy()
            kconfig = get_kubeconfig()
            if kconfig:
                env['KUBECONFIG'] = kconfig
            output = run_command(['kubectl', 'get', 'namespaces', '-o', 'json'], env=env)
            data = json.loads(output)
            return [item.get('metadata', {}).get('name') for item in data.get('items', [])]
        except:
            return []
