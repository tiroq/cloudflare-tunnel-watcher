"""Configuration management for the watcher service."""

import os
import logging
import re
from typing import Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration for the Cloudflare Tunnel Watcher."""
    
    telegram_token: str
    chat_id: str
    ssh_username: str = "username"
    cloudflared_path: str = "cloudflared"
    ssh_port: int = 22
    log_level: str = "INFO"
    max_retries: int = 10
    base_retry_delay: int = 3
    max_retry_delay: int = 60


class ConfigValidator:
    """Validator for configuration values."""
    
    # Telegram token format: digits:alphanumeric_with_dashes
    TOKEN_PATTERN = re.compile(r'^\d+:[A-Za-z0-9_-]+$')
    
    # Chat ID format: optional minus sign followed by digits, optionally with _digits suffix for topics
    CHAT_ID_PATTERN = re.compile(r'^-?\d+(_\d+)?$')
    
    @classmethod
    def validate_telegram_token(cls, token: str) -> bool:
        """
        Validate Telegram bot token format.
        
        Args:
            token: The token to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not token:
            return False
        return bool(cls.TOKEN_PATTERN.match(token))
    
    @classmethod
    def validate_chat_id(cls, chat_id: str) -> bool:
        """
        Validate Telegram chat ID format.
        
        Args:
            chat_id: The chat ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not chat_id:
            return False
        return bool(cls.CHAT_ID_PATTERN.match(chat_id))
    
    @classmethod
    def validate_config(cls, config: Config) -> tuple[bool, Optional[str]]:
        """
        Validate the entire configuration.
        
        Args:
            config: The configuration to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate Telegram token
        if not cls.validate_telegram_token(config.telegram_token):
            return False, f"Invalid Telegram token format: {config.telegram_token[:20]}..."
        
        # Validate chat ID
        if not cls.validate_chat_id(config.chat_id):
            return False, f"Invalid chat ID format: {config.chat_id}"
        
        # Validate numeric values
        if config.ssh_port < 1 or config.ssh_port > 65535:
            return False, f"Invalid SSH port: {config.ssh_port}"
        
        if config.max_retries < 1:
            return False, f"Invalid max_retries: {config.max_retries}"
        
        if config.base_retry_delay < 1:
            return False, f"Invalid base_retry_delay: {config.base_retry_delay}"
        
        if config.max_retry_delay < config.base_retry_delay:
            return False, f"max_retry_delay must be >= base_retry_delay"
        
        return True, None


def load_config() -> Config:
    """
    Load configuration from environment variables.
    
    Returns:
        Config object with loaded values
        
    Raises:
        ValueError: If required environment variables are missing
    """
    # Load required variables
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    
    if not telegram_token:
        raise ValueError("TELEGRAM_TOKEN environment variable is required")
    
    if not chat_id:
        raise ValueError("CHAT_ID environment variable is required")
    
    # Load optional variables with defaults
    config = Config(
        telegram_token=telegram_token,
        chat_id=chat_id,
        ssh_username=os.getenv("SSH_USERNAME", "username"),
        cloudflared_path=os.getenv("CLOUDFLARED_PATH", "cloudflared"),
        ssh_port=int(os.getenv("SSH_PORT", "22")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        max_retries=int(os.getenv("MAX_RETRIES", "10")),
        base_retry_delay=int(os.getenv("BASE_RETRY_DELAY", "3")),
        max_retry_delay=int(os.getenv("MAX_RETRY_DELAY", "60"))
    )
    
    # Validate configuration
    is_valid, error_msg = ConfigValidator.validate_config(config)
    if not is_valid:
        raise ValueError(f"Configuration validation failed: {error_msg}")
    
    logger.info("[Config] Configuration loaded successfully")
    logger.debug(f"[Config] SSH Port: {config.ssh_port}")
    logger.debug(f"[Config] Log Level: {config.log_level}")
    logger.debug(f"[Config] Max Retries: {config.max_retries}")
    
    return config


def load_env_file(env_file: str = ".env"):
    """
    Load environment variables from a .env file.
    
    Args:
        env_file: Path to the .env file
    """
    if not os.path.exists(env_file):
        logger.warning(f"[Config] .env file not found: {env_file}")
        return
    
    logger.info(f"[Config] Loading environment from {env_file}")
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value