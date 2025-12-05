"""Telegram notification module with retry logic."""

import logging
import time
from typing import Optional
from datetime import datetime
import requests


logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram Bot API client with retry logic."""
    
    API_BASE_URL = "https://api.telegram.org/bot{token}/{method}"
    MAX_RETRIES = 3
    RETRY_DELAYS = [2, 4, 8]  # Exponential backoff in seconds
    REQUEST_TIMEOUT = 10  # seconds
    
    def __init__(self, token: str, chat_id: str):
        """
        Initialize the Telegram notifier.
        
        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID to send messages to (format: chat_id or chat_id_topic_id)
        """
        self.token = token
        self.chat_id = chat_id
        self.base_chat_id, self.message_thread_id = self._parse_chat_id(chat_id)
        self._validate_config()
    
    def _parse_chat_id(self, chat_id: str) -> tuple[str, Optional[int]]:
        """
        Parse chat_id to extract base chat ID and optional message_thread_id.
        
        Format: -1001234567890_123 where _123 is the topic/thread ID
        
        Args:
            chat_id: The chat ID string (may include topic ID)
            
        Returns:
            Tuple of (base_chat_id, message_thread_id)
        """
        if '_' in chat_id:
            parts = chat_id.split('_', 1)
            base_id = parts[0]
            thread_id = int(parts[1])
            logger.info(f"[Telegram] Parsed topic: chat_id={base_id}, thread_id={thread_id}")
            return base_id, thread_id
        return chat_id, None
    
    def _validate_config(self):
        """Validate Telegram configuration."""
        if not self.token or not self.chat_id:
            raise ValueError("TELEGRAM_TOKEN and CHAT_ID must be set")
        
        # Basic token format validation
        if ':' not in self.token:
            logger.warning("Telegram token format may be invalid")
    
    def _format_message(self, url: str) -> str:
        """
        Format the notification message.
        
        Args:
            url: The Cloudflare tunnel URL
            
        Returns:
            Formatted message text
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        return (
            "🔗 New Cloudflare SSH Tunnel\n\n"
            f"URL: {url}\n\n"
            f"Status: Active\n"
            f"Time: {timestamp}"
        )
    
    def send_notification(self, url: str) -> bool:
        """
        Send a notification to Telegram with retry logic.
        
        Args:
            url: The Cloudflare tunnel URL to notify about
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        message = self._format_message(url)
        logger.info(f"[Telegram] Preparing to send notification for URL: {url}")
        
        for attempt in range(self.MAX_RETRIES):
            try:
                success = self._send_message(message)
                if success:
                    logger.info(f"[Telegram] ✓ Notification sent successfully for: {url}")
                    return True
                
                # If we got a client error (4xx), don't retry
                if attempt == 0:
                    logger.error(f"[Telegram] Client error, won't retry")
                    return False
                    
            except requests.RequestException as e:
                logger.warning(f"[Telegram] Request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                
                # Don't sleep after the last attempt
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAYS[attempt]
                    logger.info(f"[Telegram] Retrying in {delay}s...")
                    time.sleep(delay)
        
        logger.error(f"[Telegram] Failed to send notification after {self.MAX_RETRIES} attempts")
        return False
    
    def _send_message(self, text: str) -> bool:
        """
        Send a message via Telegram Bot API.
        
        Args:
            text: The message text to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        url = self.API_BASE_URL.format(token=self.token, method="sendMessage")
        payload = {
            "chat_id": self.base_chat_id,
            "text": text
        }
        
        # Add message_thread_id for topic support
        if self.message_thread_id is not None:
            payload["message_thread_id"] = self.message_thread_id
        
        logger.debug(f"[Telegram] Sending to chat_id: {self.base_chat_id}" +
                     (f", thread_id: {self.message_thread_id}" if self.message_thread_id else ""))
        
        response = requests.post(url, json=payload, timeout=self.REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            logger.info(f"[Telegram] Message delivered (HTTP 200)")
            return True
        
        # Handle different error codes
        if response.status_code in [401, 403, 404]:
            logger.error(f"[Telegram] ✗ Authentication/authorization error: {response.status_code}")
            return False
        
        # Server errors (5xx) should be retried
        if response.status_code >= 500:
            logger.warning(f"[Telegram] ✗ Server error: {response.status_code}")
            raise requests.RequestException(f"Server error: {response.status_code}")
        
        logger.error(f"[Telegram] ✗ Unexpected error: {response.status_code}")
        return False
    
    def test_connection(self) -> bool:
        """
        Test the Telegram connection by calling getMe.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            url = self.API_BASE_URL.format(token=self.token, method="getMe")
            response = requests.get(url, timeout=self.REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                logger.info("[Telegram] Connection test successful")
                return True
            else:
                logger.error(f"[Telegram] Connection test failed: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"[Telegram] Connection test error: {e}")
            return False