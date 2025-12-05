"""Main watcher service with state machine."""

import logging
import signal
import sys
import time
from enum import Enum
from typing import Optional

from .config import Config
from .parser import URLParser
from .process_manager import ProcessManager, ProcessState
from .telegram_notifier import TelegramNotifier


logger = logging.getLogger(__name__)


class WatcherState(Enum):
    """Watcher service states."""
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    MONITORING = "monitoring"
    NOTIFYING = "notifying"
    RETRYING = "retrying"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class CloudflareWatcher:
    """Main watcher service that orchestrates all components."""
    
    URL_DETECTION_TIMEOUT = 60  # seconds to wait for URL before warning
    
    def __init__(self, config: Config):
        """
        Initialize the watcher service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.state = WatcherState.INITIALIZING
        self.shutdown_requested = False
        
        # Initialize components
        self.parser = URLParser()
        self.process_manager = ProcessManager(
            cloudflared_path=config.cloudflared_path,
            ssh_port=config.ssh_port
        )
        self.telegram = TelegramNotifier(
            token=config.telegram_token,
            chat_id=config.chat_id,
            ssh_username=config.ssh_username
        )
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info("[Watcher] Service initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info(f"[Watcher] Received {signal_name}, initiating shutdown...")
        self.shutdown_requested = True
    
    def start(self):
        """Start the watcher service."""
        logger.info("[Watcher] Starting Cloudflare Tunnel Watcher")
        
        try:
            # Test Telegram connection
            logger.info("[Watcher] Testing Telegram connection...")
            if not self.telegram.test_connection():
                logger.warning("[Watcher] Telegram connection test failed, but continuing...")
            
            # Main service loop
            self._run_main_loop()
            
        except Exception as e:
            logger.error(f"[Watcher] Fatal error: {e}", exc_info=True)
            self.state = WatcherState.FAILED
            raise
        finally:
            self._shutdown()
    
    def _run_main_loop(self):
        """Run the main service loop."""
        while not self.shutdown_requested:
            try:
                # Start cloudflared process
                self.state = WatcherState.STARTING
                if not self.process_manager.start_process():
                    logger.error("[Watcher] Failed to start process, retrying...")
                    self.state = WatcherState.RETRYING
                    if not self.process_manager.restart_with_backoff():
                        logger.error("[Watcher] Max retries exceeded, giving up")
                        self.state = WatcherState.FAILED
                        break
                    continue
                
                # Monitor process and parse output
                self.state = WatcherState.RUNNING
                self._monitor_process()
                
                # If we get here, process died
                if not self.shutdown_requested:
                    exit_code = self.process_manager.get_exit_code()
                    logger.warning(f"[Watcher] Process exited with code {exit_code}, restarting...")
                    self.state = WatcherState.RETRYING
                    
                    if not self.process_manager.restart_with_backoff():
                        logger.error("[Watcher] Max retries exceeded, giving up")
                        self.state = WatcherState.FAILED
                        break
                
            except KeyboardInterrupt:
                logger.info("[Watcher] Keyboard interrupt received")
                self.shutdown_requested = True
                break
            except Exception as e:
                logger.error(f"[Watcher] Error in main loop: {e}", exc_info=True)
                time.sleep(5)
    
    def _monitor_process(self):
        """Monitor the cloudflared process and parse output."""
        logger.info("[Watcher] Monitoring process output...")
        url_detect_start = time.time()
        url_detected = False
        
        while not self.shutdown_requested:
            # Check if process is still alive
            if not self.process_manager.is_alive():
                logger.warning("[Watcher] Process died during monitoring")
                break
            
            # Read stdout line
            line = self.process_manager.read_stdout_line()
            
            if line is None:
                # No data available, check for timeout
                if not url_detected:
                    elapsed = time.time() - url_detect_start
                    if elapsed > self.URL_DETECTION_TIMEOUT:
                        logger.warning(f"[Watcher] No URL detected after {self.URL_DETECTION_TIMEOUT}s, still waiting...")
                        url_detect_start = time.time()  # Reset timer
                
                time.sleep(0.1)  # Small sleep to prevent busy loop
                continue
            
            # Log the line at debug level
            logger.debug(f"[Parser] {line}")
            
            # Try to extract URL
            url = self.parser.extract_url(line)
            
            if url:
                url_detected = True
                
                # Check if this is a new URL
                if self.parser.is_new_url(url):
                    logger.info(f"[Parser] ✓ New URL detected: {url}")
                    logger.info(f"[Watcher] Tunnel URL: {url}")
                    self.state = WatcherState.MONITORING
                    
                    # Send notification
                    self._send_notification(url)
    
    def _send_notification(self, url: str):
        """
        Send a Telegram notification for the new URL.
        
        Args:
            url: The URL to notify about
        """
        self.state = WatcherState.NOTIFYING
        logger.info(f"[Watcher] Sending notification for URL: {url}")
        
        success = self.telegram.send_notification(url)
        
        if success:
            logger.info("[Watcher] ✓ Message sent successfully to Telegram")
            logger.info(f"[Watcher] Notification delivered for: {url}")
        else:
            logger.error("[Watcher] ✗ Failed to send message to Telegram")
            logger.warning("[Watcher] Notification failed, but continuing to monitor")
        
        self.state = WatcherState.MONITORING
    
    def _shutdown(self):
        """Perform graceful shutdown."""
        logger.info("[Watcher] Shutting down...")
        self.state = WatcherState.SHUTDOWN
        
        # Kill cloudflared process
        if self.process_manager.is_alive():
            logger.info("[Watcher] Stopping cloudflared process...")
            self.process_manager.kill_process()
        
        logger.info("[Watcher] Shutdown complete")
        sys.stdout.flush()
        sys.stderr.flush()


def setup_logging(log_level: str):
    """
    Set up logging configuration.
    
    Args:
        log_level: The log level (DEBUG, INFO, WARNING, ERROR)
    """
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set time to UTC
    logging.Formatter.converter = time.gmtime