import threading
import collections
import os
import logging
import pty
import subprocess
import select
import fcntl
import termios
import struct
from .plugin_system import plugin_registry

logger = logging.getLogger(__name__)

class TerminalSession:
    def __init__(self, max_history=10000):
        self.history = collections.deque(maxlen=max_history)
        self.consumers = set()
        self.lock = threading.Lock()
        self.keep_running = True
        self.thread = None

    def add_history(self, data):
        with self.lock:
            self.history.append(data)
            for consumer in self.consumers:
                try:
                    consumer.send(bytes_data=data)
                except:
                    pass

    def register_consumer(self, consumer):
        with self.lock:
            if consumer in self.consumers:
                return
            
            # Check if we already have consumers to decide whether to send history
            # If this is a re-connection of the same session, we might want to be careful
            is_new_session = len(self.consumers) == 0
            
            self.consumers.add(consumer)
            
            if is_new_session:
                for data in self.history:
                    try:
                        consumer.send(bytes_data=data)
                    except:
                        pass

    def unregister_consumer(self, consumer):
        with self.lock:
            if consumer in self.consumers:
                self.consumers.remove(consumer)

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        raise NotImplementedError()

    def send_input(self, data):
        raise NotImplementedError()

    def resize(self, rows, cols):
        pass

    def close(self):
        self.keep_running = False

    def restart(self):
        def _do_restart():
            logger.info("Executing background restart")
            with self.lock:
                self.close()
                self.history.clear()
                
            if self.thread and self.thread.is_alive() and threading.current_thread() != self.thread:
                self.thread.join(timeout=1)
                
            self.keep_running = True
            try:
                self._setup_session()
                # We need to replace the thread reference
                self.thread = threading.Thread(target=self.run, daemon=True)
                self.thread.start()
                self.add_history(b'\r\n\x1b[2J\x1b[H\x1b[32m--- Session Restarted ---\x1b[0m\r\n')
                logger.info("Background restart successful")
            except Exception as e:
                logger.error(f"Background restart failed: {e}")
                self.add_history(f"\r\n\x1b[31mFailed to restart session: {str(e)}\x1b[0m\r\n".encode())

        # Run restart in a separate thread to avoid deadlocking the consumer or the run loop itself
        threading.Thread(target=_do_restart, daemon=True).start()

class SystemSession(TerminalSession):
    def __init__(self):
        super().__init__()
        self._init_args = {}
        self._setup_session()

    def _setup_session(self):
        self.master_fd, self.slave_fd = pty.openpty()
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        env['COLORTERM'] = 'truecolor'
        self.process = subprocess.Popen(
            ['/bin/bash', '--login'], preexec_fn=os.setsid, stdin=self.slave_fd, stdout=self.slave_fd, stderr=self.slave_fd,
            universal_newlines=False, env=env
        )
        # Close slave_fd in parent process to avoid hanging on read
        os.close(self.slave_fd)

    def run(self):
        logger.info("Starting SystemSession run loop")
        try:
            while self.keep_running:
                try:
                    # Check if process is still alive
                    if self.process.poll() is not None:
                        logger.warning(f"System process exited with code {self.process.returncode}")
                        break

                    r, w, e = select.select([self.master_fd], [], [], 0.5)
                    if self.master_fd in r:
                        try:
                            data = os.read(self.master_fd, 4096)
                            if data:
                                self.add_history(data)
                            else:
                                logger.info("PTY EOF reached")
                                break
                        except OSError as e:
                            # EIO is common when the process exits
                            logger.warning(f"PTY read OSError: {e}")
                            break
                except (TimeoutError, BlockingIOError):
                    continue
                except Exception as e:
                    logger.error(f"SystemSession read error: {e}")
                    self.add_history(f"\r\n\x1b[31mError reading from PTY: {str(e)}\x1b[0m\r\n".encode())
                    break
        finally:
            logger.info("SystemSession run loop finished")
            try:
                os.close(self.master_fd)
            except:
                pass
            try:
                if self.process.poll() is None:
                    self.process.terminate()
                    self.process.wait(timeout=1)
            except:
                pass
        # Clean up session from manager
        from .terminal_manager import manager
        with manager._lock:
            for sid, sess in list(manager.sessions.items()):
                if sess == self:
                    del manager.sessions[sid]

    def send_input(self, data):
        try:
            os.write(self.master_fd, data.encode())
        except:
            pass

    def resize(self, rows, cols):
        try:
            s = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, s)
        except:
            pass

class TerminalManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TerminalManager, cls).__new__(cls)
                cls._instance.sessions = {}
        return cls._instance

    def restart_session(self, session_id):
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.restart()
                return True
        return False

    def get_session(self, session_id, session_type, **kwargs):
        with self._lock:
            session = self.sessions.get(session_id)
            if session and (not session.thread or not session.thread.is_alive()):
                del self.sessions[session_id]

            if session_id not in self.sessions:
                if session_type == 'system':
                    session = SystemSession()
                else:
                    # Check registered modules for session types
                    session_class = None
                    for module in plugin_registry.get_all_modules():
                        session_types = module.get_terminal_session_types()
                        if session_type in session_types:
                            session_class = session_types[session_type]
                            break
                    
                    if session_class:
                        session = session_class(**kwargs)
                    else:
                        return None
                
                session.start()
                self.sessions[session_id] = session
            return self.sessions.get(session_id)

manager = TerminalManager()
