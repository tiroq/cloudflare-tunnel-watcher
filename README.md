# Cloudflare Tunnel Watcher

A reliable service that automatically monitors Cloudflare Quick Tunnels and sends URL notifications to Telegram when they change.

## Features

- 🔄 **Auto-Recovery**: Survives system reboots, network outages, and process crashes
- 📱 **Telegram Notifications**: Instant alerts when tunnel URLs change
- 🛡️ **Reliability Patterns**: Exponential backoff, state machine, layered recovery
- 📊 **Structured Logging**: All events logged to systemd journal
- ⚙️ **Minimal Dependencies**: Just Python 3 and requests library
- 🔒 **Security Hardening**: Optional systemd security features

## Architecture

The service implements a robust state machine with multiple recovery layers:

1. **Process Manager**: Manages cloudflared subprocess with exponential backoff retry
2. **URL Parser**: Extracts and tracks tunnel URLs from stdout
3. **Telegram Notifier**: Sends notifications with automatic retry logic
4. **Main Watcher**: Orchestrates all components with graceful error handling

## Requirements

- Linux (Ubuntu/Debian/CentOS/etc.)
- Python 3.8+
- cloudflared binary
- Telegram Bot API token

## Quick Start

### 1. Install cloudflared

```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared
```

#### MacOS

```bash
brew install cloudflare/cloudflare/cloudflared
```

### 2. Create Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow instructions
3. Save the bot token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Get your chat ID:
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find the `chat.id` value

### 3. Install the Service

```bash
# Create service directory
sudo mkdir -p /opt/cloudflare-watcher
sudo chown $USER:$USER /opt/cloudflare-watcher

# Clone or copy files
cd /opt/cloudflare-watcher
# Copy all project files here

# Install Python dependencies
pip3 install -r requirements.txt
# Or use a virtual environment:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Create .env file
cat > /opt/cloudflare-watcher/.env << 'EOF'
TELEGRAM_TOKEN=your_bot_token_here
CHAT_ID=your_chat_id_here
SSH_USERNAME=username
EOF

# Secure the file
chmod 600 /opt/cloudflare-watcher/.env
```

### 5. Install systemd Service

```bash
# Copy service file
sudo cp cloudflare-watcher.service /etc/systemd/system/

# If using virtual environment, update ExecStart in service file:
# ExecStart=/opt/cloudflare-watcher/venv/bin/python /opt/cloudflare-watcher/watcher.py

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable cloudflare-watcher.service
sudo systemctl start cloudflare-watcher.service
```

### 6. Verify Installation

```bash
# Check service status
sudo systemctl status cloudflare-watcher.service

# View logs
sudo journalctl -u cloudflare-watcher.service -f

# You should see:
# - Service starting
# - Telegram connection test
# - cloudflared process starting
# - URL detected and notification sent
```

## Configuration

All configuration is done via environment variables in the `.env` file:

### Required Variables

```bash
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
CHAT_ID=-1001234567890
```

### Optional Variables

```bash
# SSH username for tunnel connections (default: username)
SSH_USERNAME=username

# Path to cloudflared binary (default: uses PATH)
CLOUDFLARED_PATH=/usr/local/bin/cloudflared

# SSH port to forward (default: 22)
SSH_PORT=22

# Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
LOG_LEVEL=INFO

# Maximum retry attempts before giving up (default: 10)
MAX_RETRIES=10

# Base retry delay in seconds (default: 3)
BASE_RETRY_DELAY=3

# Maximum retry delay in seconds (default: 60)
MAX_RETRY_DELAY=60
```

## Usage

### Manual Testing

Test the watcher without systemd:

```bash
cd /opt/cloudflare-watcher
python3 watcher.py
```

### Service Management

```bash
# Start service
sudo systemctl start cloudflare-watcher.service

# Stop service
sudo systemctl stop cloudflare-watcher.service

# Restart service
sudo systemctl restart cloudflare-watcher.service

# View status
sudo systemctl status cloudflare-watcher.service

# View logs (follow mode)
sudo journalctl -u cloudflare-watcher.service -f

# View last 100 lines
sudo journalctl -u cloudflare-watcher.service -n 100

# View logs since yesterday
sudo journalctl -u cloudflare-watcher.service --since yesterday
```

## Troubleshooting

### Service Won't Start

```bash
# Check status
sudo systemctl status cloudflare-watcher.service

# View detailed logs
sudo journalctl -u cloudflare-watcher.service -n 100

# Common issues:
# 1. Missing .env file
# 2. Invalid token/chat_id format
# 3. cloudflared not in PATH
# 4. Python dependencies not installed
```

### URL Not Detected

```bash
# Test cloudflared manually
cloudflared tunnel --url ssh://localhost:22

# Check if SSH is running
sudo systemctl status ssh

# View parser debug logs
echo "LOG_LEVEL=DEBUG" >> /opt/cloudflare-watcher/.env
sudo systemctl restart cloudflare-watcher.service
sudo journalctl -u cloudflare-watcher.service -f
```

### Telegram Notifications Not Sent

```bash
# Test token manually
curl "https://api.telegram.org/bot<TOKEN>/getMe"

# Test sending message
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<CHAT_ID>&text=Test"

# Check logs for Telegram errors
journalctl -u cloudflare-watcher.service | grep -i telegram
```

### Process Keeps Restarting

```bash
# View exit codes
journalctl -u cloudflare-watcher.service | grep "exited with code"

# Check system resources
free -h
df -h

# Verify cloudflared works
cloudflared tunnel --url ssh://localhost:22
```

## Project Structure

```
cloudflare-watcher/
├── watcher.py                    # Main entry point
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration management
│   ├── parser.py                 # URL extraction from stdout
│   ├── process_manager.py        # cloudflared subprocess manager
│   ├── telegram_notifier.py      # Telegram API client
│   └── watcher.py                # Main service orchestrator
├── cloudflare-watcher.service    # systemd unit file
├── requirements.txt              # Python dependencies
├── .env                          # Configuration (not in git)
├── .env.example                  # Example configuration file
└── README.md                     # This file
```

## Security Considerations

### Credential Management

- Store `.env` file with `600` permissions
- Never commit tokens to version control
- Use systemd `EnvironmentFile` directive
- Consider running as non-root user (requires testing)

### Hardening systemd Service

Uncomment security options in `cloudflare-watcher.service`:

```ini
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/cloudflare-watcher
```

**Note**: Test thoroughly before enabling in production.

## Contributing

This is a minimal, production-ready implementation. Before adding features:

1. Consider if it increases complexity unnecessarily
2. Ensure it doesn't add external dependencies
3. Maintain backward compatibility
4. Add appropriate tests

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions:

1. Review troubleshooting section above
2. Check logs with `journalctl`
3. Test components individually

## Related Documentation

- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Telegram Bot API](https://core.telegram.org/bots/api)