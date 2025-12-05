"""Tests for the Telegram notifier module."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from telegram_notifier import TelegramNotifier


class TestTelegramNotifier(unittest.TestCase):
    """Test cases for TelegramNotifier class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.token = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
        self.chat_id = "-1001234567890"
        self.notifier = TelegramNotifier(self.token, self.chat_id)
    
    def test_initialization(self):
        """Test notifier initialization."""
        self.assertEqual(self.notifier.token, self.token)
        self.assertEqual(self.notifier.chat_id, self.chat_id)
    
    def test_invalid_token_raises_error(self):
        """Test that missing token raises ValueError."""
        with self.assertRaises(ValueError):
            TelegramNotifier("", self.chat_id)
    
    def test_invalid_chat_id_raises_error(self):
        """Test that missing chat_id raises ValueError."""
        with self.assertRaises(ValueError):
            TelegramNotifier(self.token, "")
    
    def test_format_message(self):
        """Test message formatting."""
        url = "https://test.trycloudflare.com"
        message = self.notifier._format_message(url)
        
        self.assertIn("New Cloudflare SSH Tunnel", message)
        self.assertIn(url, message)
        self.assertIn("Status: Active", message)
        self.assertIn("Time:", message)
    
    @patch('telegram_notifier.requests.post')
    def test_send_notification_success(self, mock_post):
        """Test successful notification send."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        url = "https://test.trycloudflare.com"
        result = self.notifier.send_notification(url)
        
        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 1)
    
    @patch('telegram_notifier.requests.post')
    def test_send_notification_retry_on_500(self, mock_post):
        """Test retry on server error."""
        # First two attempts fail with 500, third succeeds
        mock_post.side_effect = [
            Mock(status_code=500),
            Mock(status_code=500),
            Mock(status_code=200)
        ]
        
        url = "https://test.trycloudflare.com"
        result = self.notifier.send_notification(url)
        
        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 3)
    
    @patch('telegram_notifier.requests.post')
    def test_send_notification_fails_after_retries(self, mock_post):
        """Test failure after max retries."""
        mock_post.side_effect = [
            Mock(status_code=500),
            Mock(status_code=500),
            Mock(status_code=500)
        ]
        
        url = "https://test.trycloudflare.com"
        result = self.notifier.send_notification(url)
        
        self.assertFalse(result)
        self.assertEqual(mock_post.call_count, 3)
    
    @patch('telegram_notifier.requests.post')
    def test_send_notification_auth_error_no_retry(self, mock_post):
        """Test that auth errors don't retry."""
        mock_post.return_value = Mock(status_code=401)
        
        url = "https://test.trycloudflare.com"
        result = self.notifier.send_notification(url)
        
        self.assertFalse(result)
        # Should only try once for auth errors
        self.assertEqual(mock_post.call_count, 1)
    
    @patch('telegram_notifier.requests.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection test."""
        mock_get.return_value = Mock(status_code=200)
        
        result = self.notifier.test_connection()
        
        self.assertTrue(result)
    
    @patch('telegram_notifier.requests.get')
    def test_test_connection_failure(self, mock_get):
        """Test failed connection test."""
        mock_get.return_value = Mock(status_code=401)
        
        result = self.notifier.test_connection()
        
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()