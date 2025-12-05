"""Tests for the configuration module."""

import unittest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import Config, ConfigValidator, load_config


class TestConfigValidator(unittest.TestCase):
    """Test cases for ConfigValidator class."""
    
    def test_validate_telegram_token_valid(self):
        """Test valid token formats."""
        valid_tokens = [
            "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
            "123:ABC",
            "9876543210:XYZ123-_abc"
        ]
        for token in valid_tokens:
            self.assertTrue(
                ConfigValidator.validate_telegram_token(token),
                f"Token should be valid: {token}"
            )
    
    def test_validate_telegram_token_invalid(self):
        """Test invalid token formats."""
        invalid_tokens = [
            "",
            "no_colon_here",
            "ABC:123",  # digits should be first
            "123:",  # missing second part
            ":ABC",  # missing first part
        ]
        for token in invalid_tokens:
            self.assertFalse(
                ConfigValidator.validate_telegram_token(token),
                f"Token should be invalid: {token}"
            )
    
    def test_validate_chat_id_valid(self):
        """Test valid chat ID formats."""
        valid_chat_ids = [
            "123456789",
            "-1001234567890",
            "0",
            "-1",
            "-1001905962453_633"  # Topic/thread ID format
        ]
        for chat_id in valid_chat_ids:
            self.assertTrue(
                ConfigValidator.validate_chat_id(chat_id),
                f"Chat ID should be valid: {chat_id}"
            )
    
    def test_validate_chat_id_invalid(self):
        """Test invalid chat ID formats."""
        invalid_chat_ids = [
            "",
            "abc",
            "123abc",
            "--123",
            "12.34"
        ]
        for chat_id in invalid_chat_ids:
            self.assertFalse(
                ConfigValidator.validate_chat_id(chat_id),
                f"Chat ID should be invalid: {chat_id}"
            )
    
    def test_validate_config_valid(self):
        """Test valid configuration."""
        config = Config(
            telegram_token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
            chat_id="-1001234567890",
            ssh_port=22,
            max_retries=10,
            base_retry_delay=3,
            max_retry_delay=60
        )
        is_valid, error = ConfigValidator.validate_config(config)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_config_invalid_token(self):
        """Test configuration with invalid token."""
        config = Config(
            telegram_token="invalid_token",
            chat_id="-1001234567890"
        )
        is_valid, error = ConfigValidator.validate_config(config)
        self.assertFalse(is_valid)
        self.assertIn("Invalid Telegram token", error)
    
    def test_validate_config_invalid_port(self):
        """Test configuration with invalid port."""
        config = Config(
            telegram_token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
            chat_id="-1001234567890",
            ssh_port=99999  # Invalid port
        )
        is_valid, error = ConfigValidator.validate_config(config)
        self.assertFalse(is_valid)
        self.assertIn("Invalid SSH port", error)


class TestLoadConfig(unittest.TestCase):
    """Test cases for load_config function."""
    
    def setUp(self):
        """Save original environment."""
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_load_config_with_required_vars(self):
        """Test loading config with only required variables."""
        os.environ["TELEGRAM_TOKEN"] = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
        os.environ["CHAT_ID"] = "-1001234567890"
        
        config = load_config()
        
        self.assertEqual(config.telegram_token, "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.assertEqual(config.chat_id, "-1001234567890")
        self.assertEqual(config.ssh_port, 22)  # Default
        self.assertEqual(config.log_level, "INFO")  # Default
    
    def test_load_config_with_optional_vars(self):
        """Test loading config with optional variables."""
        os.environ["TELEGRAM_TOKEN"] = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
        os.environ["CHAT_ID"] = "-1001234567890"
        os.environ["SSH_PORT"] = "2222"
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["MAX_RETRIES"] = "5"
        
        config = load_config()
        
        self.assertEqual(config.ssh_port, 2222)
        self.assertEqual(config.log_level, "DEBUG")
        self.assertEqual(config.max_retries, 5)
    
    def test_load_config_missing_token(self):
        """Test that missing token raises ValueError."""
        os.environ["CHAT_ID"] = "-1001234567890"
        
        with self.assertRaises(ValueError) as context:
            load_config()
        
        self.assertIn("TELEGRAM_TOKEN", str(context.exception))
    
    def test_load_config_missing_chat_id(self):
        """Test that missing chat_id raises ValueError."""
        os.environ["TELEGRAM_TOKEN"] = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
        
        with self.assertRaises(ValueError) as context:
            load_config()
        
        self.assertIn("CHAT_ID", str(context.exception))
    
    def test_load_config_invalid_validation(self):
        """Test that invalid config raises ValueError."""
        os.environ["TELEGRAM_TOKEN"] = "invalid"
        os.environ["CHAT_ID"] = "invalid"
        
        with self.assertRaises(ValueError) as context:
            load_config()
        
        self.assertIn("validation failed", str(context.exception))


if __name__ == '__main__':
    unittest.main()