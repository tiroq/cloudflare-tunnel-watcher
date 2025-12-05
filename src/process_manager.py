"""Process manager for cloudflared with exponential backoff retry."""

import logging
import subprocess
import time
import signal
from typing import Optional
from enum import Enum


logger = logging.getLogger(__name__)


class ProcessState(Enum):
    """Process lifecycle states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"


class ProcessManager:
    """Manager for cloudflared subprocess with restart logic."""
    
    DEFAULT_CLOUDFLARED_PATH = "cloudflared"
    BASE_RETRY_DELAY = 3  # seconds
    MAX_RETRY_DELAY = 60  # seconds
    MAX_RETRIES = 10
    SHUTDOWN_TIMEOUT = 5  # seconds
    
    def __init__(
        self,
        cloudflared_path: Optional[str] = None,
        ssh_port: int = 22
    ):
        """
        Initialize the process manager.
        
        Args:
            cloudflared_path: Path to cloudflared binary (default: use PATH)
            ssh_port: SSH port to forward (default: 22)
        """
        self.cloudflared_path = cloudflared_path or self.DEFAULT_CLOUDFLARED_PATH
        self.ssh_port = ssh_port
        self.process: Optional[subprocess.Popen] = None
        self.state = ProcessState.STOPPED
        self.retry_count = 0
    
    def start_process(self) -> bool:
        """
        Start the cloudflared process.
        
        Returns:
            True if process started successfully, False otherwise
        """
        if self.state == ProcessState.RUNNING and self.is_alive():
            logger.warning("[ProcessManager] Process already running")
            return True
        
        self.state = ProcessState.STARTING
        logger.info("[ProcessManager] Starting cloudflared process")
        
        try:
            # Build command
            cmd = [
                self.cloudflared_path,
                "tunnel",
                "--url", f"ssh://localhost:{self.ssh_port}",
                "--no-autoupdate"
            ]
            
            # Start process with stdout/stderr pipes
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            # Give it a moment to potentially fail immediately
            time.sleep(0.5)
            
            if self.process.poll() is not None:
                # Process exited immediately
                exit_code = self.process.returncode
                logger.error(f"[ProcessManager] Process exited immediately with code {exit_code}")
                self.state = ProcessState.FAILED
                return False
            
            self.state = ProcessState.RUNNING
            self.retry_count = 0  # Reset retry counter on success
            logger.info("[ProcessManager] Process started successfully")
            return True
            
        except FileNotFoundError:
            logger.error(f"[ProcessManager] cloudflared not found at: {self.cloudflared_path}")
            self.state = ProcessState.FAILED
            return False
            
        except Exception as e:
            logger.error(f"[ProcessManager] Failed to start process: {e}")
            self.state = ProcessState.FAILED
            return False
    
    def is_alive(self) -> bool:
        """
        Check if the process is alive.
        
        Returns:
            True if process is running, False otherwise
        """
        if self.process is None:
            return False
        
        return self.process.poll() is None
    
    def kill_process(self, force: bool = False):
        """
        Kill the cloudflared process.
        
        Args:
            force: If True, use SIGKILL immediately, otherwise try SIGTERM first
        """
        if self.process is None:
            return
        
        if not self.is_alive():
            logger.info("[ProcessManager] Process already dead")
            self.state = ProcessState.STOPPED
            return
        
        if force:
            logger.info("[ProcessManager] Sending SIGKILL to process")
            self.process.kill()
        else:
            logger.info("[ProcessManager] Sending SIGTERM to process")
            self.process.terminate()
            
            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=self.SHUTDOWN_TIMEOUT)
                logger.info("[ProcessManager] Process terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("[ProcessManager] Process didn't terminate, sending SIGKILL")
                self.process.kill()
                self.process.wait()
        
        self.state = ProcessState.STOPPED
        self.process = None
    
    def restart_with_backoff(self) -> bool:
        """
        Restart the process with exponential backoff.
        
        Returns:
            True if restart succeeded, False if max retries exceeded
        """
        self.retry_count += 1
        
        if self.retry_count > self.MAX_RETRIES:
            logger.error(f"[ProcessManager] Max retries ({self.MAX_RETRIES}) exceeded, giving up")
            self.state = ProcessState.FAILED
            return False
        
        # Calculate delay with exponential backoff
        delay = min(
            self.BASE_RETRY_DELAY * (2 ** (self.retry_count - 1)),
            self.MAX_RETRY_DELAY
        )
        
        logger.info(f"[ProcessManager] Retry {self.retry_count}/{self.MAX_RETRIES}, waiting {delay}s...")
        time.sleep(delay)
        
        # Kill old process if still running
        if self.is_alive():
            self.kill_process(force=True)
        
        return self.start_process()
    
    def read_stdout_line(self) -> Optional[str]:
        """
        Read a line from stderr (cloudflared outputs to stderr).
        
        Returns:
            A line of output, or None if no data available or process dead
        """
        if self.process is None or self.process.stderr is None:
            return None
        
        try:
            # Check if process is still alive
            if not self.is_alive():
                return None
            
            # Read line from stderr (cloudflared outputs tunnel info here)
            line = self.process.stderr.readline()
            
            if line:
                return line.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"[ProcessManager] Error reading stderr: {e}")
            return None
    
    def get_exit_code(self) -> Optional[int]:
        """
        Get the exit code of the process.
        
        Returns:
            Exit code if process has exited, None if still running
        """
        if self.process is None:
            return None
        
        return self.process.poll()