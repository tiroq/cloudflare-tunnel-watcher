#!/usr/bin/env python3
"""
Cloudflare Tunnel Watcher - Main entry point
Monitors cloudflared Quick Tunnel and sends URL changes to Telegram
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import load_env_file, load_config
from src.watcher import CloudflareWatcher, setup_logging


def main():
    """Main entry point for the watcher service."""
    try:
        # Load environment variables from .env file if it exists
        load_env_file()
        
        # Load and validate configuration
        config = load_config()
        
        # Set up logging
        setup_logging(config.log_level)
        
        # Create and start watcher
        watcher = CloudflareWatcher(config)
        watcher.start()
        
        # Exit with success code
        sys.exit(0)
        
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()