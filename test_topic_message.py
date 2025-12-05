#!/usr/bin/env python3
"""Test script to send a message to a Telegram topic."""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import load_env_file, load_config
from telegram_notifier import TelegramNotifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Send a test message to the configured Telegram topic."""
    try:
        # Load environment variables
        load_env_file()
        
        # Load configuration
        config = load_config()
        
        print(f"\n{'='*60}")
        print("Telegram Topic Test")
        print(f"{'='*60}")
        print(f"Chat ID: {config.chat_id}")
        print(f"Token: {config.telegram_token[:20]}...")
        print(f"{'='*60}\n")
        
        # Initialize notifier
        notifier = TelegramNotifier(config.telegram_token, config.chat_id)
        
        print(f"Parsed Configuration:")
        print(f"  Base Chat ID: {notifier.base_chat_id}")
        print(f"  Message Thread ID: {notifier.message_thread_id}")
        print()
        
        # Test connection
        print("Testing connection...")
        if not notifier.test_connection():
            print("❌ Connection test failed!")
            return 1
        print("✅ Connection test passed!\n")
        
        # Send test notification
        print("Sending test message to topic...")
        test_url = "https://example-tunnel.trycloudflare.com"
        
        if notifier.send_notification(test_url):
            print("✅ Test message sent successfully!")
            print(f"\nCheck your Telegram topic (thread {notifier.message_thread_id}) for the message.")
            return 0
        else:
            print("❌ Failed to send test message!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())