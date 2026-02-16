import os
import json
import collections
import subprocess
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from core.models import Tool
from core.plugin_system import plugin_registry, BaseModule
from core.utils import run_command
from unittest.mock import patch, MagicMock, mock_open, ANY

User = get_user_model()

class MockModule(BaseModule):
    @property
    def module_id(self): return "mock-tool"
    @property
    def module_name(self): return "Mock Tool"

class SyncMockModule(BaseModule):
    @property
    def module_id(self): return "sync-mock"
    @property
    def module_name(self): return "Sync Mock"

    def setUp(self):
        plugin_registry._reset()
        tool = Tool.objects.create(name="test-tool", status="not_installed")
        self.assertEqual(tool.name, "test-tool")
        self.assertEqual(tool.status, "not_installed")
        self.assertEqual(str(tool), "Test-tool")
        self.assertEqual(tool.get_icon_class(), "test-tool")
        self.assertEqual(tool.get_custom_icon_svg(), None)
        
        # Test get_name_display with registered module
        plugin_registry.register(MockModule)
        tool.name = "mock-tool"
        # We need to ensure the registry is used
        self.assertEqual(tool.get_name_display(), "Mock Tool")
        self.assertEqual(str(tool), "Mock Tool")
        
        # Test get_name_display without registered module
        tool.name = "nonexistent-tool"
        self.assertEqual(tool.get_name_display(), "Nonexistent-tool")

class PluginSystemTest(TestCase):
    def test_module_registration(self):
        plugin_registry.register(MockModule)
        module = plugin_registry.get_module("mock-tool")
        self.assertIsNotNone(module)
        self.assertEqual(module.module_name, "Mock Tool")
        
        # Test get_all_modules
        all_mods = plugin_registry.get_all_modules()
        self.assertTrue(any(m.module_id == "mock-tool" for m in all_mods))

    def test_sync_tools_with_db(self):
        plugin_registry.register(SyncMockModule)
        # Force sync
        plugin_registry._synced = False
        plugin_registry.sync_tools_with_db()
        
        tool = Tool.objects.filter(name="sync-mock").first()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.status, "installed")
        
        # Test auto-detection of out-of-the-box modules
        class NoInstallModule(BaseModule):
            @property
            def module_id(self): return "no-install"
            @property
            def module_name(self): return "No Install"
            
        plugin_registry.register(NoInstallModule)
        plugin_registry._synced = False
        plugin_registry.sync_tools_with_db()
        tool = Tool.objects.get(name="no-install")
        self.assertEqual(tool.status, "installed")
        
        # Test auto-detection with get_service_version
        class AutoDetectModule(BaseModule):
            @property
            def module_id(self): return "auto-detect"
            @property
            def module_name(self): return "Auto Detect"
            def get_service_version(self): return "1.0"
            def install(self, req, tool): pass
            
        plugin_registry.register(AutoDetectModule)
        plugin_registry._synced = False
        plugin_registry.sync_tools_with_db()
        tool = Tool.objects.get(name="auto-detect")
        self.assertEqual(tool.status, "installed")

        # Test tool already exists in DB but status is not_installed
        tool.status = 'not_installed'
        tool.save()
        plugin_registry._synced = False
        plugin_registry.sync_tools_with_db()
        tool.refresh_from_db()
        self.assertEqual(tool.status, 'installed')

        # Test missing module in DB
        Tool.objects.filter(name="mock-tool").delete()
        plugin_registry._synced = False
        plugin_registry.sync_tools_with_db()
        self.assertTrue(Tool.objects.filter(name="mock-tool").exists())
        
        # Test tool already exists but module gone (should not fail)
        Tool.objects.create(name="gone-tool", status="installed")
        plugin_registry._synced = False
        plugin_registry.sync_tools_with_db()

    def test_base_module_defaults(self):
        # Test default implementations in BaseModule
        module = MockModule()
        self.assertEqual(module.get_service_version(), None)
        self.assertEqual(module.get_urls(), [])
        self.assertEqual(module.get_websocket_urls(), [])
        self.assertEqual(module.get_icon_class(), "mock-tool")
        self.assertEqual(module.get_custom_icon_svg(), None)
        self.assertEqual(module.get_logs_url(None), None)
        self.assertEqual(module.get_resource_tabs(), [])
        self.assertEqual(module.get_service_status(None), 'running')
        self.assertEqual(module.get_extra_actions_template_name(), None)
        self.assertEqual(module.get_extra_content_template_name(), None)
        self.assertEqual(module.get_resource_header_template_name(), None)
        self.assertEqual(module.get_install_template_name(), None)
        self.assertEqual(module.handle_hx_request(None, None, None), None)
        self.assertEqual(module.get_terminal_session_types(), {})

class CoreViewsTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_superuser(username='admin', password='password', email='admin@test.com')
        self.client.login(username='admin', password='password')

    @patch('core.views.cpuinfo.get_cpu_info')
    @patch('core.views.get_hw_info_sudo')
    def test_dashboard_access(self, mock_hw, mock_cpu_info):
        mock_cpu_info.return_value = {'brand_raw': 'Intel Core i7'}
        mock_hw.return_value = {'motherboard': 'Test MB', 'ram_slots': []}
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/dashboard.html')
        
        # Test cache
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    @patch('core.views.run_command')
    def test_tool_detail_hx_status(self, mock_run):
        mock_run.return_value = b"active"
        tool = Tool.objects.create(name="docker", status="installed")
        response = self.client.get(reverse('tool_detail', kwargs={'tool_name': 'docker'}) + "?tab=status", HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/partials/tool_status.html')

    def test_tool_detail_view(self):
        tool = Tool.objects.create(name="docker", status="installed")
        response = self.client.get(reverse('tool_detail', kwargs={'tool_name': 'docker'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Docker")

    @patch('core.views.run_command')
    def test_tool_action_view(self, mock_run):
        mock_run.return_value = b"active"
        Tool.objects.create(name="generic-tool", status="installed")
        response = self.client.get(reverse('tool_action', kwargs={'tool_name': 'generic-tool', 'action': 'start'}))
        self.assertEqual(response.status_code, 302)
        # Check if it was called with either the list or the specific command
        mock_run.assert_called()
        
        # Test systemctl failure
        mock_run.side_effect = Exception("systemctl fail")
        response = self.client.get(reverse('tool_action', kwargs={'tool_name': 'generic-tool', 'action': 'stop'}))
        self.assertEqual(response.status_code, 302) # Still redirects

        # Test invalid action
        response = self.client.get(reverse('tool_action', kwargs={'tool_name': 'generic-tool', 'action': 'invalid'}))
        self.assertEqual(response.status_code, 400)
        
        # Test nonexistent tool
        response = self.client.get(reverse('tool_action', kwargs={'tool_name': 'nonexistent', 'action': 'start'}))
        self.assertEqual(response.status_code, 404)

    @patch('core.views.run_command')
    def test_tool_action_with_module(self, mock_run):
        # Test tool_action using module method
        class ActionModule(BaseModule):
            started = False
            @property
            def module_id(self): return "action-tool"
            @property
            def module_name(self): return "Action Tool"
            def service_start(self, tool): self.__class__.started = True
            
        plugin_registry.register(ActionModule)
        Tool.objects.create(name="action-tool", status="installed")
        
        response = self.client.get(reverse('tool_action', kwargs={'tool_name': 'action-tool', 'action': 'start'}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ActionModule.started)

    @patch('core.views.run_command')
    def test_install_tool_view(self, mock_run):
        tool = Tool.objects.create(name="docker", status="not_installed")
        response = self.client.get(reverse('install_tool', kwargs={'tool_name': 'docker'}))
        self.assertEqual(response.status_code, 302)

    @patch('core.views.get_server_stats')
    def test_server_stats_partial(self, mock_stats):
        mock_stats.return_value = {'cpu_usage': 10, 'ram_usage': 20, 'disks_usage': []}
        response = self.client.get(reverse('server_stats_partial'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/partials/stats.html')

    def test_add_module_get(self):
        response = self.client.get(reverse('add_module'))
        self.assertEqual(response.status_code, 302) # Redirects to dashboard

    @patch('core.views.run_command')
    def test_add_module_post(self, mock_run):
        mock_run.return_value = b""
        response = self.client.post(reverse('add_module'), {'repo_url': 'https://github.com/SolsticeOps/SolsticeOps-test.git'})
        self.assertEqual(response.status_code, 302)
        
        # Test invalid URL
        response = self.client.post(reverse('add_module'), {'repo_url': 'invalid-url'})
        self.assertEqual(response.status_code, 400)

    @patch('core.views.os.path.exists')
    @patch('core.views.run_command')
    def test_add_module_existing(self, mock_run, mock_exists):
        # We need to be careful with os.path.exists mock as it might be used by other parts
        def exists_side_effect(path):
            if 'modules' in path:
                return True
            return False
        mock_exists.side_effect = exists_side_effect
        mock_run.return_value = b""
        
        # Test existing module
        with patch('core.views.plugin_registry'):
            response = self.client.post(reverse('add_module'), {'repo_url': 'https://github.com/SolsticeOps/SolsticeOps-test.git'})
            # It redirects if initialized successfully
            self.assertEqual(response.status_code, 302)
        
        # Test error during initialization
        # Mock run_command to fail when trying to update submodule
        mock_run.side_effect = Exception("init error")
        response = self.client.post(reverse('add_module'), {'repo_url': 'https://github.com/SolsticeOps/SolsticeOps-test.git'})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"already exists", response.content)

    @patch('core.views.run_command')
    @patch('core.views.plugin_registry')
    def test_add_module_git_index_error(self, mock_registry, mock_run):
        # Test "already exists in the index" error
        # We need to mock os.path.exists to return False so it tries to add
        with patch('core.views.os.path.exists', return_value=False):
            mock_run.side_effect = [Exception("already exists in the index"), b""]
            response = self.client.post(reverse('add_module'), {'repo_url': 'https://github.com/SolsticeOps/SolsticeOps-test.git'})
            self.assertEqual(response.status_code, 302)

    @patch('core.views.run_command')
    def test_add_module_git_error(self, mock_run):
        mock_run.side_effect = Exception("git error")
        response = self.client.post(reverse('add_module'), {'repo_url': 'https://github.com/SolsticeOps/SolsticeOps-test.git'})
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"git error", response.content)

    @patch('core.views.run_command')
    def test_hw_info_sudo_cache(self, mock_run):
        from core.views import get_hw_info_sudo
        # Mock motherboard and RAM info
        mock_run.side_effect = [
            b"Test MB",
            b"Size: 8 GB\nConfigured Memory Speed: 3200 MT/s\nSize: 8 GB\nConfigured Memory Speed: 3200 MT/s"
        ]
        # First call
        info = get_hw_info_sudo()
        self.assertEqual(info['motherboard'], "Test MB")
        self.assertEqual(len(info['ram_slots']), 2)
        self.assertEqual(info['ram_slots'][0]['size'], "8 GB")

    @patch('core.plugin_system.importlib.import_module')
    @patch('core.plugin_system.os.listdir')
    @patch('core.plugin_system.os.path.exists')
    @patch('core.plugin_system.os.path.isdir')
    @patch('core.plugin_system.os.makedirs')
    def test_plugin_discovery(self, mock_makedirs, mock_isdir, mock_exists, mock_listdir, mock_import):
        from core.plugin_system import plugin_registry
        mock_listdir.return_value = ['test_mod', 'fail_mod']
        mock_isdir.return_value = True
        mock_exists.return_value = True
        
        mock_mod = MagicMock()
        mock_mod.Module = MockModule
        
        def import_side_effect(name):
            if 'fail_mod' in name: raise Exception("import fail")
            return mock_mod
            
        mock_import.side_effect = import_side_effect
        
        plugin_registry.discover_modules()
        self.assertIsNotNone(plugin_registry.get_module("mock-tool"))
        
        # Test missing modules dir
        mock_exists.return_value = False
        plugin_registry.discover_modules()
        mock_makedirs.assert_called()

    @patch('core.utils.subprocess.run')
    @patch('core.utils.subprocess.check_output')
    @patch('core.utils.logger')
    def test_run_command_utils(self, mock_logger, mock_sub_output, mock_sub_run):
        from core.utils import run_command
        # Success case
        mock_sub_output.return_value = b"output"
        res = run_command(['ls'])
        self.assertEqual(res, b"output")
        
        # Error case - log_errors=False (re-raises)
        mock_sub_output.side_effect = subprocess.CalledProcessError(1, 'ls', output=b"error")
        with self.assertRaises(subprocess.CalledProcessError):
            run_command(['ls'], log_errors=False)
            
        # Error case - log_errors=True (re-raises, but logs)
        with self.assertRaises(subprocess.CalledProcessError):
            run_command(['ls'], log_errors=True)
        
        # Generic Exception case
        mock_sub_output.side_effect = Exception("generic error")
        with self.assertRaises(Exception):
            run_command(['ls'])
        
        # capture_output=False case
        mock_sub_output.side_effect = None
        run_command(['ls'], capture_output=False)
        mock_sub_run.assert_called()
        
        # Shell case
        run_command("echo test", shell=True)
        mock_sub_output.assert_called()

    @patch('core.terminal_manager.manager.get_session')
    def test_terminal_consumer(self, mock_get_session):
        from core.consumers import TerminalConsumer
        from core.terminal_manager import TerminalSession
        
        mock_session = MagicMock(spec=TerminalSession)
        mock_get_session.return_value = mock_session
        
        consumer = TerminalConsumer()
        consumer.scope = {
            'url_route': {'kwargs': {'session_type': 'system'}},
            'path': '/ws/terminal/system/'
        }
        consumer.accept = MagicMock()
        consumer.close = MagicMock()
        
        # Test connect
        consumer.connect()
        self.assertEqual(consumer.session_id, "system_shell")
        mock_session.register_consumer.assert_called_with(consumer)
        
        # Test receive input
        consumer.receive(text_data=json.dumps({'input': 'ls\n'}))
        mock_session.send_input.assert_called_with('ls\n')
        
        # Test receive resize
        consumer.receive(text_data=json.dumps({'resize': {'rows': 24, 'cols': 80}}))
        mock_session.resize.assert_called_with(24, 80)
        
        # Test receive restart
        with patch('core.terminal_manager.manager.restart_session') as mock_restart:
            consumer.receive(text_data=json.dumps({'restart': True}))
            mock_restart.assert_called_with("system_shell")
            
        # Test disconnect
        consumer.disconnect(1000)
        mock_session.unregister_consumer.assert_called_with(consumer)

        # Test no session
        mock_get_session.return_value = None
        consumer.connect()
        consumer.close.assert_called()

    def test_terminal_manager_singleton(self):
        from core.terminal_manager import manager, TerminalManager
        self.assertIsInstance(manager, TerminalManager)
        
        with patch('core.terminal_manager.SystemSession') as mock_sys:
            sess = manager.get_session("test_unique", "system")
            self.assertIsNotNone(sess)
            # Second call same ID
            sess2 = manager.get_session("test_unique", "system")
            self.assertEqual(sess, sess2)
            
            manager.restart_session("test_unique")
            self.assertIn("test_unique", manager.sessions)

class DockerCLIWrapperTest(TestCase):
    @patch('core.docker_cli_wrapper.run_command')
    def test_container_list(self, mock_run):
        from core.docker_cli_wrapper import DockerCLI
        
        mock_run.side_effect = [
            b"abc123\ndef456", 
            b'[{"Id": "abc123", "Name": "/test1", "State": {"Status": "running"}, "Config": {"Image": "nginx"}}, {"Id": "def456", "Name": "/test2", "State": {"Status": "stopped"}, "Config": {"Image": "redis"}}]'
        ]
        
        client = DockerCLI()
        containers = client.containers.list()
        
        self.assertEqual(len(containers), 2)
        self.assertEqual(containers[0].id, "abc123")
        self.assertEqual(containers[0].name, "test1")
        self.assertEqual(containers[0].status, "running")
        
        # Test list all
        client.containers.list(all=True)
        any_ps_a = any('ps' in str(call) and '-a' in str(call) for call in mock_run.call_args_list)
        self.assertTrue(any_ps_a)

    @patch('core.docker_cli_wrapper.run_command')
    def test_container_methods(self, mock_run):
        from core.docker_cli_wrapper import Container, Image
        container = Container({'Id': 'abc123', 'Name': '/test', 'State': {'Status': 'running'}, 'Config': {'Image': 'nginx'}})
        
        self.assertEqual(container.status, 'running')
        self.assertIsInstance(container.image, Image)
        
        container.start()
        mock_run.assert_called_with(['docker', 'start', 'abc123'])
        
        container.stop()
        mock_run.assert_called_with(['docker', 'stop', 'abc123'])
        
        container.restart()
        mock_run.assert_called_with(['docker', 'restart', 'abc123'])
        
        container.remove(force=True)
        mock_run.assert_called_with(['docker', 'rm', '-f', 'abc123'])
        
        container.logs(tail=10, timestamps=True)
        mock_run.assert_called_with(['docker', 'logs', '--tail', '10', '-t', 'abc123'])
        
        container.exec_run("ls")
        mock_run.assert_called_with(['docker', 'exec', 'abc123', 'ls'], timeout=600)
        
        # Test __getattr__ edge cases
        self.assertEqual(container.id, 'abc123')
        self.assertEqual(container.name, 'test')
        self.assertEqual(container.Config['Image'], 'nginx')
        with self.assertRaises(AttributeError):
            _ = container.nonexistent

    @patch('core.docker_cli_wrapper.run_command')
    def test_docker_cli_info(self, mock_run):
        from core.docker_cli_wrapper import DockerCLI
        mock_run.return_value = b'{"ID": "123"}'
        client = DockerCLI()
        info = client.info()
        self.assertEqual(info['ID'], "123")

    @patch('core.docker_cli_wrapper.run_command')
    def test_container_manager_get(self, mock_run):
        from core.docker_cli_wrapper import DockerCLI
        mock_run.return_value = b'[{"Id": "abc123"}]'
        client = DockerCLI()
        container = client.containers.get("abc123")
        self.assertEqual(container.id, "abc123")
        
        mock_run.return_value = b""
        self.assertIsNone(client.containers.get("nonexistent"))

    @patch('core.docker_cli_wrapper.run_command')
    def test_manager_exists(self, mock_run):
        from core.docker_cli_wrapper import Manager
        m = Manager()
        mock_run.return_value = b"abc123"
        self.assertTrue(m._exists("abc123"))
        
        mock_run.side_effect = Exception()
        self.assertFalse(m._exists("invalid"))

    @patch('core.docker_cli_wrapper.run_command')
    def test_manager_inspect_all(self, mock_run):
        from core.docker_cli_wrapper import Manager, Container
        m = Manager()
        mock_run.return_value = b'[{"Id": "c1"}, {"Id": "c2"}]'
        res = m._inspect_all(["c1", "c2"], Container)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].id, "c1")
        
        mock_run.side_effect = Exception()
        self.assertEqual(m._inspect_all(["c1"], Container), [])
        self.assertEqual(m._inspect_all([], Container), [])

    @patch('core.docker_cli_wrapper.run_command')
    def test_volume_methods(self, mock_run):
        from core.docker_cli_wrapper import Volume
        vol = Volume({'Name': 'test-vol'})
        self.assertEqual(vol.id, 'test-vol')
        self.assertEqual(vol.name, 'test-vol')
        vol.remove(force=True)
        mock_run.assert_called_with(['docker', 'volume', 'rm', '-f', 'test-vol'])

    @patch('core.docker_cli_wrapper.run_command')
    def test_container_manager_run(self, mock_run):
        from core.docker_cli_wrapper import DockerCLI
        mock_run.return_value = b'[{"Id": "new123", "Name": "/new-cont"}]'
        client = DockerCLI()
        
        client.containers.run("nginx", 
            name="new-cont", 
            ports={'80/tcp': 8080}, 
            volumes={'/src': {'bind': '/dst', 'mode': 'rw'}}, 
            environment={'K': 'V', 'A': '1'}, 
            restart_policy={"Name": "always"}, 
            privileged=True,
            network="test-net"
        )
        
        # Verify call arguments
        # The first call is docker run, the second is docker inspect (from self.get())
        run_call = mock_run.call_args_list[0]
        args = run_call[0][0]
        self.assertIn('--name', args)
        self.assertIn('new-cont', args)
        self.assertIn('-p', args)
        self.assertIn('8080:80/tcp', args)
        self.assertIn('-v', args)
        self.assertIn('/src:/dst:rw', args)
        self.assertIn('--network', args)
        self.assertIn('test-net', args)
        self.assertIn('--restart', args)
        self.assertIn('always', args)
        self.assertIn('--privileged', args)
        self.assertIn('-e', args)
        self.assertIn('K=V', args)
        self.assertIn('A=1', args)

    @patch('core.docker_cli_wrapper.run_command')
    def test_docker_cli_wrapper_missing_cases(self, mock_run):
        from core.docker_cli_wrapper import DockerCLI, Container, Image, Volume, Network, Manager
        client = DockerCLI()
        
        # Test Container.image property
        container = Container({'Id': 'c1', 'Image': 'i1', 'Config': {'Image': 'nginx:latest'}})
        self.assertEqual(container.image.id, 'i1')
        self.assertEqual(container.image.tags, ['nginx:latest'])
        
        # Test Container.status unknown
        container_no_state = Container({'Id': 'c1'})
        self.assertEqual(container_no_state.status, 'unknown')
        
        # Test DockerCLI.info failure
        mock_run.side_effect = Exception("docker info fail")
        self.assertEqual(client.info(), {})
        mock_run.side_effect = None

        # Test Manager._exists with empty ID
        m = Manager()
        self.assertFalse(m._exists(""))

        # Test Manager._inspect_all with empty list
        self.assertEqual(m._inspect_all([], Container), [])

        # Test Container.remove without force
        mock_run.reset_mock()
        container.remove(force=False)
        mock_run.assert_called_with(['docker', 'rm', 'c1'])

        # Test Volume.remove without force
        vol = Volume({'Name': 'v1'})
        mock_run.reset_mock()
        vol.remove(force=False)
        mock_run.assert_called_with(['docker', 'volume', 'rm', 'v1'])

        # Test Network methods with ID instead of object
        net = Network({'Id': 'n1', 'Name': 'net1'})
        mock_run.reset_mock()
        net.connect('c1')
        mock_run.assert_called_with(['docker', 'network', 'connect', 'n1', 'c1'])
        
        mock_run.reset_mock()
        net.disconnect('c1')
        mock_run.assert_called_with(['docker', 'network', 'disconnect', 'n1', 'c1'])

    @patch('core.docker_cli_wrapper.run_command')
    def test_network_methods(self, mock_run):
        from core.docker_cli_wrapper import Network
        net = Network({'Id': 'net123', 'Name': 'test-net'})
        
        net.connect('cont123')
        mock_run.assert_called_with(['docker', 'network', 'connect', 'net123', 'cont123'])
        
        net.disconnect('cont123')
        mock_run.assert_called_with(['docker', 'network', 'disconnect', 'net123', 'cont123'])
        
        net.remove()
        mock_run.assert_called_with(['docker', 'network', 'rm', 'net123'])

    @patch('core.docker_cli_wrapper.run_command')
    def test_image_manager(self, mock_run):
        from core.docker_cli_wrapper import DockerCLI
        mock_run.side_effect = [b"img1", b'[{"Id": "img1", "RepoTags": ["t1"]}]', b"", b"", b""]
        client = DockerCLI()
        images = client.images.list()
        self.assertEqual(len(images), 1)
        
        client.images.pull("nginx", tag="latest")
        mock_run.assert_called_with(['docker', 'pull', 'nginx:latest'])
        
        client.images.pull("redis")
        mock_run.assert_called_with(['docker', 'pull', 'redis'])
        
        client.images.remove("img1", force=True)
        mock_run.assert_called_with(['docker', 'rmi', '-f', 'img1'])

    @patch('core.docker_cli_wrapper.run_command')
    def test_volume_manager(self, mock_run):
        from core.docker_cli_wrapper import DockerCLI
        mock_run.side_effect = [b"vol1", b'[{"Name": "vol1"}]', b"", b""]
        client = DockerCLI()
        volumes = client.volumes.list()
        self.assertEqual(len(volumes), 1)
        
        client.volumes.create("new-vol")
        mock_run.assert_called_with(['docker', 'volume', 'create', '--name', 'new-vol', '--driver', 'local'])

    @patch('core.docker_cli_wrapper.run_command')
    def test_network_manager(self, mock_run):
        from core.docker_cli_wrapper import DockerCLI
        mock_run.side_effect = [b"net1", b'[{"Id": "net1", "Name": "net1"}]', b"", b""]
        client = DockerCLI()
        networks = client.networks.list()
        self.assertEqual(len(networks), 1)
        
        client.networks.create("new-net")
        mock_run.assert_called_with(['docker', 'network', 'create', '--driver', 'bridge', 'new-net'])

class UtilsTest(TestCase):
    @patch('subprocess.check_output')
    def test_run_command_success(self, mock_sub):
        mock_run_val = b"success"
        mock_sub.return_value = mock_run_val
        result = run_command(['echo', 'test'])
        self.assertEqual(result, mock_run_val)

class TagsTest(TestCase):
    def test_tools_nav_processor(self):
        from core.context_processors import tools_nav
        request = MagicMock()
        request.user.is_authenticated = True
        context = tools_nav(request)
        self.assertIn('tools_nav', context)
        
        # Test unauthenticated
        request.user.is_authenticated = False
        context = tools_nav(request)
        self.assertEqual(context, {})

    def test_divide_filter(self):
        from core.templatetags.core_tags import divide
        self.assertEqual(divide(10, 2), 5)
        self.assertEqual(divide(10, 0), 0)
        self.assertEqual(divide("invalid", 2), 0)

    def test_split_env_filter(self):
        from core.templatetags.core_tags import split_env
        self.assertEqual(split_env("KEY=VALUE"), ["KEY", "VALUE"])
        self.assertEqual(split_env("INVALID"), ("INVALID", ""))
        self.assertEqual(split_env(None), ("", ""))
        self.assertEqual(split_env(123), ("123", ""))

    def test_to_opacity(self):
        from core.templatetags.core_tags import to_opacity
        self.assertGreater(to_opacity(100), 0.9)
        self.assertLess(to_opacity(0), 0.5)
        self.assertEqual(to_opacity("invalid"), 0.4)

    def test_split_at_colon(self):
        from core.templatetags.core_tags import split_at_colon_last, split_at_colon_first
        self.assertEqual(split_at_colon_last("a:b:c"), "c")
        self.assertEqual(split_at_colon_first("a:b:c"), "a")

    def test_call_method(self):
        from core.templatetags.core_tags import call_method
        class MockObj:
            def test(self, arg): return arg
        obj = MockObj()
        self.assertEqual(call_method(obj, "test", "hello"), "hello")
        self.assertIsNone(call_method(obj, "nonexistent"))

class AdminTest(TestCase):
    def test_tool_admin_queryset(self):
        from core.admin import ToolAdmin
        from django.contrib.admin.sites import AdminSite
        site = AdminSite()
        tool_admin = ToolAdmin(Tool, site)
        request = MagicMock()
        qs = tool_admin.get_queryset(request)
        self.assertIsNotNone(qs)

class TerminalManagerTest(TestCase):
    def test_terminal_session_base(self):
        from core.terminal_manager import TerminalSession
        session = TerminalSession()
        self.assertEqual(session.history, collections.deque(maxlen=10000))
        
        # Test consumer registration
        consumer = MagicMock()
        session.add_history(b"old history")
        session.register_consumer(consumer)
        self.assertIn(consumer, session.consumers)
        # Should have sent history
        consumer.send.assert_called_with(bytes_data=b"old history")
        
        session.add_history(b"test")
        self.assertIn(b"test", session.history)
        consumer.send.assert_called_with(bytes_data=b"test")
        
        # Test duplicate registration
        session.register_consumer(consumer)
        self.assertEqual(len(session.consumers), 1)
        
        session.unregister_consumer(consumer)
        self.assertNotIn(consumer, session.consumers)
        
        session.close()
        self.assertFalse(session.keep_running)
        
        # Test NotImplementedError
        with self.assertRaises(NotImplementedError):
            session.run()
        with self.assertRaises(NotImplementedError):
            session.send_input("test")

    @patch('core.terminal_manager.pty.openpty')
    @patch('core.terminal_manager.subprocess.Popen')
    @patch('core.terminal_manager.os.close')
    @patch('core.terminal_manager.select.select')
    @patch('core.terminal_manager.os.read')
    @patch('core.terminal_manager.manager')
    def test_system_session(self, mock_manager, mock_read, mock_select, mock_close, mock_popen, mock_pty):
        from core.terminal_manager import SystemSession
        mock_pty.return_value = (10, 11) # master, slave
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        session = SystemSession()
        self.assertEqual(session.master_fd, 10)
        
        # Test run loop once
        mock_select.return_value = ([10], [], [])
        mock_read.return_value = b"output"
        
        # We need to stop it quickly
        def select_side_effect(*args, **kwargs):
            session.keep_running = False
            return ([10], [], [])
        mock_select.side_effect = select_side_effect
        
        session.run()
        self.assertIn(b"output", session.history)
        
        # Test poll exiting
        session.keep_running = True
        mock_process.poll.return_value = 0
        mock_select.side_effect = [([10], [], [])]
        session.run()
        self.assertFalse(session.keep_running)

        # Test OSError in read
        session.keep_running = True
        mock_process.poll.return_value = None
        mock_select.side_effect = [([10], [], [])]
        mock_read.side_effect = OSError("EIO")
        session.run()
        self.assertFalse(session.keep_running)
        
        # Test generic exception in run loop
        session.keep_running = True
        mock_read.side_effect = None
        mock_select.side_effect = Exception("select error")
        session.run()
        self.assertFalse(session.keep_running)
        self.assertTrue(any(b"Error reading from PTY" in h for h in session.history))

        session.send_input("ls")
        with patch('core.terminal_manager.os.write') as mock_write:
            session.send_input("ls")
            mock_write.assert_called()
            
        session.resize(24, 80)
        with patch('core.terminal_manager.fcntl.ioctl') as mock_ioctl:
            session.resize(24, 80)
            mock_ioctl.assert_called()

        session.close()
        self.assertFalse(session.keep_running)

    def test_terminal_session_restart(self):
        from core.terminal_manager import TerminalSession
        class MockSess(TerminalSession):
            def _setup_session(self): self.setup_called = True
            def run(self): pass
            def close(self): self.keep_running = False
        
        session = MockSess()
        session.restart()
        # Restart is async, wait a bit
        import time
        time.sleep(0.5)
        self.assertTrue(session.keep_running)

    @patch('core.consumers.manager')
    def test_terminal_consumer(self, mock_manager):
        from core.consumers import TerminalConsumer
        consumer = TerminalConsumer()
        consumer.scope = {'url_route': {'kwargs': {'session_type': 'system'}}}
        consumer.send = MagicMock()
        consumer.accept = MagicMock()
        consumer.close = MagicMock()
        
        mock_session = MagicMock()
        mock_manager.get_session.return_value = mock_session
        
        consumer.connect()
        # consumer.accept() is called in connect()
        
        # Test receive
        consumer.session = mock_session # Ensure it's set
        consumer.receive(text_data=json.dumps({'input': 'ls\n'}))
        mock_session.send_input.assert_called_with('ls\n')
        
        consumer.receive(text_data=json.dumps({'resize': {'rows': 24, 'cols': 80}}))
        mock_session.resize.assert_called_with(24, 80)
        
        consumer.receive(text_data=json.dumps({'restart': True}))
        mock_manager.restart_session.assert_called()
        
        consumer.receive(text_data=json.dumps({'heartbeat': True})) # Should do nothing
        
        # Test disconnect
        consumer.disconnect(1000)
        mock_session.unregister_consumer.assert_called_with(consumer)

    def test_terminal_manager_singleton(self):
        from core.terminal_manager import manager
        # Patch SystemSession to avoid real PTY
        with patch('core.terminal_manager.SystemSession') as mock_sys:
            session = manager.get_session('test-id', 'system')
            self.assertIsNotNone(session)
            
            session2 = manager.get_session('test-id', 'system')
            self.assertEqual(session, session2)
            
            manager.restart_session('test-id')
            session.restart.assert_called_once()
            
            # Test restart nonexistent
            self.assertFalse(manager.restart_session('nonexistent'))

    def test_terminal_manager_module_session(self):
        from core.terminal_manager import manager
        # Register a mock module with session type
        class SessionModule(BaseModule):
            @property
            def module_id(self): return "sess-tool"
            @property
            def module_name(self): return "Sess Tool"
            def get_terminal_session_types(self):
                return {'custom': MagicMock}
        
        plugin_registry.register(SessionModule)
        session = manager.get_session('custom-id', 'custom', arg='val')
        self.assertIsNotNone(session)

    def test_terminal_manager_session_cleanup(self):
        from core.terminal_manager import manager
        mock_sess = MagicMock()
        mock_sess.thread.is_alive.return_value = False
        manager.sessions['dead-id'] = mock_sess
        
        # This should trigger cleanup and try to create new session
        with patch('core.terminal_manager.SystemSession') as mock_sys:
            manager.get_session('dead-id', 'system')
            # The dead session should be gone
            self.assertNotEqual(manager.sessions.get('dead-id'), mock_sess)

    def test_terminal_manager_get_session_invalid(self):
        from core.terminal_manager import manager
        res = manager.get_session('invalid', 'invalid-type')
        self.assertIsNone(res)

class RoutingTest(TestCase):
    def test_websocket_urlpatterns(self):
        from core.routing import websocket_urlpatterns
        self.assertTrue(len(websocket_urlpatterns) > 0)

class SetupDBTest(TestCase):
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('builtins.open', new_callable=mock_open, read_data="")
    @patch('os.path.exists')
    def test_setup_sqlite(self, mock_exists, mock_file, mock_print, mock_input):
        from setup_db import setup
        mock_input.side_effect = ['1', 'sudo_pass']
        mock_exists.return_value = False
        
        setup()
        
        mock_file.assert_called_with(".env", "w")
        handle = mock_file()
        written = "".join([call.args[0] for call in handle.write.call_args_list])
        self.assertIn("DATABASE_URL=sqlite:///db.sqlite3", written)
        self.assertIn("SUDO_PASSWORD=sudo_pass", written)

    @patch('builtins.input')
    @patch('builtins.print')
    @patch('builtins.open', new_callable=mock_open, read_data="EXISTING=val\nDATABASE_URL=old\nDEBUG=False\nCSRF_TRUSTED_ORIGINS=old\nSUDO_PASSWORD=old\n")
    @patch('os.path.exists')
    def test_setup_mysql(self, mock_exists, mock_file, mock_print, mock_input):
        from setup_db import setup
        # Choice 2, user, pass, host, port, dbname, sudo_pass
        mock_input.side_effect = ['2', 'user', 'pass', 'host', '3306', 'dbname', 'sudo_pass']
        mock_exists.return_value = True
        
        setup()
        
        handle = mock_file()
        written = "".join([call.args[0] for call in handle.write.call_args_list])
        self.assertIn("DATABASE_URL=mysql+mysqlconnector://user:pass@host:3306/dbname", written)
        self.assertIn("EXISTING=val", written)
        self.assertIn("DEBUG=True", written)

    @patch('builtins.input')
    @patch('builtins.print')
    @patch('builtins.open', new_callable=mock_open, read_data="")
    @patch('os.path.exists')
    def test_setup_postgres(self, mock_exists, mock_file, mock_print, mock_input):
        from setup_db import setup
        # Choice 3, user, pass, host, port, dbname, sudo_pass
        mock_input.side_effect = ['3', 'user', 'pass', 'host', '5432', 'dbname', 'sudo_pass']
        mock_exists.return_value = False
        
        setup()
        
        handle = mock_file()
        written = "".join([call.args[0] for call in handle.write.call_args_list])
        self.assertIn("DATABASE_URL=postgres://user:pass@host:5432/dbname", written)

    @patch('builtins.input')
    @patch('builtins.print')
    def test_setup_invalid(self, mock_print, mock_input):
        from setup_db import setup
        mock_input.side_effect = ['9']
        with self.assertRaises(SystemExit) as cm:
            setup()
        self.assertEqual(cm.exception.code, 1)

class DeploymentTest(TestCase):
    def test_asgi_application(self):
        from solstice_ops.asgi import application
        self.assertIsNotNone(application)

    def test_wsgi_application(self):
        from solstice_ops.wsgi import application
        self.assertIsNotNone(application)

class K8sCLIWrapperTest(TestCase):
    @patch('core.k8s_cli_wrapper.get_kubeconfig')
    @patch('core.k8s_cli_wrapper.run_command')
    def test_k8s_info(self, mock_run, mock_config):
        from core.k8s_cli_wrapper import K8sCLI
        mock_config.return_value = "/fake/config"
        mock_run.return_value = b'{"serverVersion": {"gitVersion": "v1.29.0"}}'
        
        k8s = K8sCLI()
        info = k8s.info()
        self.assertEqual(info['serverVersion']['gitVersion'], "v1.29.0")
        called_args = mock_run.call_args[0][0]
        self.assertEqual(called_args[:3], ['kubectl', 'version', '-o'])

    @patch('core.k8s_cli_wrapper.get_kubeconfig')
    @patch('core.k8s_cli_wrapper.run_command')
    def test_get_namespaces(self, mock_run, mock_config):
        from core.k8s_cli_wrapper import K8sCLI
        mock_config.return_value = "/fake/config"
        mock_run.return_value = b'{"items": [{"metadata": {"name": "default"}}, {"metadata": {"name": "kube-system"}}]}'
        
        k8s = K8sCLI()
        namespaces = k8s.get_namespaces()
        self.assertEqual(len(namespaces), 2)
        self.assertIn("default", namespaces)
        self.assertIn("kube-system", namespaces)

    @patch('core.k8s_cli_wrapper.get_kubeconfig')
    @patch('core.k8s_cli_wrapper.run_command')
    def test_pod_list(self, mock_run, mock_config):
        from core.k8s_cli_wrapper import K8sCLI
        mock_config.return_value = "/fake/config"
        mock_run.return_value = b'{"items": [{"metadata": {"name": "pod1", "namespace": "default"}, "status": {"phase": "Running"}}]}'
        
        k8s = K8sCLI()
        pods = k8s.pods.list(namespace="default")
        self.assertEqual(len(pods), 1)
        self.assertEqual(pods[0].name, "pod1")
        self.assertEqual(pods[0].status, "Running")
        self.assertEqual(pods[0].namespace, "default")

    @patch('core.k8s_cli_wrapper.get_kubeconfig')
    @patch('core.k8s_cli_wrapper.run_command')
    def test_deployment_methods(self, mock_run, mock_config):
        from core.k8s_cli_wrapper import K8sCLI
        mock_config.return_value = "/fake/config"
        mock_run.return_value = b'{"metadata": {"name": "deploy1"}, "spec": {"replicas": 2}}'
        
        k8s = K8sCLI()
        deploy = k8s.deployments.get("deploy1", namespace="default")
        self.assertEqual(deploy.name, "deploy1")
        self.assertEqual(deploy.replicas, 2)

        k8s.deployments.scale("deploy1", replicas=3, namespace="default")
        mock_run.assert_called_with(['kubectl', 'scale', 'deployment', 'deploy1', '--replicas=3', '-n', 'default'], env=ANY)
        
        k8s.deployments.restart("deploy1", namespace="default")
        mock_run.assert_called_with(['kubectl', 'rollout', 'restart', 'deployment', 'deploy1', '-n', 'default'], env=ANY)

    @patch('core.k8s_cli_wrapper.get_kubeconfig')
    @patch('core.k8s_cli_wrapper.run_command')
    def test_pod_logs(self, mock_run, mock_config):
        from core.k8s_cli_wrapper import Pod
        mock_config.return_value = "/fake/config"
        mock_run.return_value = b"some logs"
        
        pod = Pod({"metadata": {"name": "pod1", "namespace": "default"}})
        logs = pod.logs(tail=10, timestamps=True)
        self.assertEqual(logs, b"some logs")
        mock_run.assert_called_with(['kubectl', 'logs', 'pod1', '-n', 'default', '--tail', '10', '--timestamps'], env=ANY)

    @patch('core.k8s_cli_wrapper.get_kubeconfig')
    @patch('core.k8s_cli_wrapper.run_command')
    def test_k8s_get_context(self, mock_run, mock_config):
        from core.k8s_cli_wrapper import K8sCLI
        mock_config.return_value = "/fake/config"
        mock_run.return_value = b"kubernetes-admin@kubernetes"
        
        k8s = K8sCLI()
        context = k8s.get_context()
        self.assertEqual(context, "kubernetes-admin@kubernetes")

    @patch('core.k8s_cli_wrapper.get_kubeconfig')
    @patch('core.k8s_cli_wrapper.run_command')
    def test_manager_delete(self, mock_run, mock_config):
        from core.k8s_cli_wrapper import K8sCLI
        mock_config.return_value = "/fake/config"
        k8s = K8sCLI()
        k8s.pods.delete("pod1", namespace="default")
        mock_run.assert_called_with(['kubectl', 'delete', 'pod', 'pod1', '-n', 'default'], env=ANY)

    @patch('core.k8s_cli_wrapper.get_kubeconfig')
    @patch('core.k8s_cli_wrapper.run_command')
    def test_k8s_object_getattr(self, mock_run, mock_config):
        from core.k8s_cli_wrapper import K8sObject
        obj = K8sObject({"metadata": {"name": "test", "uid": "123"}, "other": "val"})
        self.assertEqual(obj.name, "test")
        self.assertEqual(obj.uid, "123")
        self.assertEqual(obj.other, "val")
        with self.assertRaises(AttributeError):
            _ = obj.nonexistent
