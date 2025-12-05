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

## Monitoring

### Health Checks

Check if everything is running:

```bash
# Is service active?
systemctl is-active cloudflare-watcher.service

# Is cloudflared running?
pgrep -f cloudflared

# Recent logs
journalctl -u cloudflare-watcher.service -n 20
```

### Key Metrics

Monitor these patterns in logs:

```bash
# Count restarts in last 24h
journalctl -u cloudflare-watcher.service --since "24 hours ago" | grep "retrying in" | wc -l

# Count successful notifications
journalctl -u cloudflare-watcher.service --since "24 hours ago" | grep "Notification sent" | wc -l

# Check for errors
journalctl -u cloudflare-watcher.service -p err -n 50
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

## Testing

### Chaos Testing

Test resilience:

```bash
# 1. Kill cloudflared process (should auto-restart)
pkill cloudflared
journalctl -u cloudflare-watcher.service -f

# 2. Kill watcher service (systemd should restart)
sudo systemctl kill cloudflare-watcher.service
sleep 5
sudo systemctl status cloudflare-watcher.service

# 3. Simulate network failure
sudo ip link set eth0 down
sleep 10
sudo ip link set eth0 up
journalctl -u cloudflare-watcher.service -f
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
└── README.md                     # This file
```

## Security Considerations

### Credential Management

- Store `.env` file with `600` permissions
- Never commit tokens to version control
- Use systemd `EnvironmentFile` directive
- Consider running as non-root user (requires testing)

### Hardening systemd Service

Uncomment security options in [`cloudflare-watcher.service`](cloudflare-watcher.service):

```ini
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/cloudflare-watcher
```

**Note**: Test thoroughly before enabling in production.

## Performance

### Resource Usage

- **Memory**: 20-50 MB (Python process) + 30-80 MB (cloudflared)
- **CPU**: <1% idle, 2-5% during restarts
- **Disk I/O**: Minimal (log writes only)
- **Network**: <1 KB/s + SSH traffic

### Timing Characteristics

- Process spawn: 1-2s
- URL detection: 2-5s after spawn
- Telegram notification: 200-500ms
- Recovery from crash: 3-6s
- Full recovery from reboot: 10-20s

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

---

# Quick Start Guide

## Prerequisites Check

✅ Python 3 installed
✅ requests library installed (v2.31.0)
✅ Chat ID configured in `.env`
✅ Telegram token configured in `.env`

## Installation Steps

### 1. Install cloudflared (if not already installed)

```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared

# Verify installation
cloudflared --version
```

### 2. Test the Watcher Manually

```bash
# Run the watcher
python3 watcher.py

# You should see:
# [INFO] [Watcher] Service initialized
# [INFO] [Watcher] Starting Cloudflare Tunnel Watcher
# [INFO] [Watcher] Testing Telegram connection...
# [INFO] [Telegram] Connection test successful
# [INFO] [ProcessManager] Starting cloudflared process
# [INFO] [ProcessManager] Process started successfully
# [INFO] [Watcher] Monitoring process output...
# [INFO] [Parser] New URL detected: https://xxx.trycloudflare.com
# [INFO] [Telegram] Notification sent successfully

# Stop with Ctrl+C
```

### 3. Install as systemd Service

```bash
# Copy files to system directory
sudo mkdir -p /opt/cloudflare-watcher
sudo cp -r . /opt/cloudflare-watcher/
sudo chmod 600 /opt/cloudflare-watcher/.env

# Install service
sudo cp cloudflare-watcher.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cloudflare-watcher.service
sudo systemctl start cloudflare-watcher.service
```

### 4. Verify Service is Running

```bash
# Check status
sudo systemctl status cloudflare-watcher.service

# View logs
sudo journalctl -u cloudflare-watcher.service -f

# Check if URL was detected
sudo journalctl -u cloudflare-watcher.service | grep "URL detected"
```

## Common Commands

```bash
# Start service
sudo systemctl start cloudflare-watcher.service

# Stop service
sudo systemctl stop cloudflare-watcher.service

# Restart service
sudo systemctl restart cloudflare-watcher.service

# View status
sudo systemctl status cloudflare-watcher.service

# Follow logs in real-time
sudo journalctl -u cloudflare-watcher.service -f

# View last 50 lines
sudo journalctl -u cloudflare-watcher.service -n 50
```

## Success Indicators

When everything is working, you should see:

1. **In logs**: URL detected within 5-10 seconds of starting
2. **In Telegram**: Message with new tunnel URL
3. **Service status**: Active (running)
4. **Process**: cloudflared running (`ps aux | grep cloudflared`)

---

# Specification

## Objective
Create a service that:

1. Launches a Cloudflare Quick Tunnel:
   ```
   cloudflared tunnel --url ssh://localhost:22
   ```
2. Parses the process stdout and extracts the URL of the form:
   ```
   https://XXXXX.trycloudflare.com
   ```
3. Sends the new URL to Telegram every time it changes.
4. Automatically recovers after:
   - system reboot  
   - internet outage  
   - cloudflared crash  
5. Runs as a Linux systemd service with:
   - automatic restart  
   - logging to journalctl  

The solution must be minimal, stable, require no external databases, work without a domain, and remain fully free.

## Technical Constraints
- OS: Linux (Ubuntu / Debian / CentOS)
- Language: **Python 3 or Go** (Go preferred for structure and resilience)
- No Docker required (optional)
- `cloudflared` must run as an external subprocess
- Telegram API must be called directly via HTTP

## Functional Requirements

### 1. Start Cloudflare Quick Tunnel
The service must launch:
```
cloudflared tunnel --url ssh://localhost:22
```
and read stdout in real time.

### 2. Extract the URL
The Quick Tunnel URL has the form:
```
https://<random>.trycloudflare.com
```

Regular expression:
```
https?://[a-zA-Z0-9-]+\.trycloudflare\.com
```

When a new URL appears:
- store it
- send it to Telegram

### 3. Telegram Notification
Use Telegram Bot API:

```
POST https://api.telegram.org/bot<token>/sendMessage
```

Parameters:
- chat_id  
- text  

Message format:
```
New Cloudflare SSH URL:
<URL>
```

### 4. Auto-Recovery
If cloudflared exits:
- log the event  
- restart cloudflared after 3–5 seconds  

If network drops:
- cloudflared will fail → the watcher must restart it

If the watcher itself crashes:
- systemd must restart the watcher

### 5. Logging
The service must print meaningful log lines to stdout so they appear in `journalctl`.

## Non-Functional Requirements
- No external dependencies besides requests (in Python) or stdlib (in Go)
- Clean, readable code
- Error-handling with no unhandled panics
- Configuration via `.env` file:
  ```
  TELEGRAM_TOKEN=...
  CHAT_ID=...
  ```

## Project Structure (Python version)

```
cloudflare-watcher/
│
├── watcher.py
├── config.py        (optional)
├── requirements.txt
└── .env
```

## systemd Unit File

Path:
```
/etc/systemd/system/cloudflare-watcher.service
```

Content:

```
[Unit]
Description=Cloudflare Tunnel Auto-Watcher
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/cloudflare-watcher
ExecStart=/usr/bin/python3 /opt/cloudflare-watcher/watcher.py
EnvironmentFile=/opt/cloudflare-watcher/.env
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Testing Requirements

### Parser Tests:
- Feed multiple stdout lines
- Verify URL extraction
- Ensure non-URL noise does not trigger matches

### Telegram Tests:
- Use a mock HTTP server
- Verify proper POST formatting

### Stability Tests:
- Simulate cloudflared crash
- Simulate network drop
- Watcher must restart cloudflared automatically

## Notes
This project should be implemented with reliability and simplicity in mind.  
Avoid dependencies, avoid frameworks, and prioritize clarity.

---

# Architecture

## Minimal Viable Architecture with Core Reliability Patterns

### 1. Architecture Overview

#### 1.1 Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    systemd Layer                         │
│  - Auto-restart on failure                              │
│  - Journal logging                                       │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│              Watcher Service                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Main Control Loop                        │  │
│  │  - State management                              │  │
│  │  - Error recovery orchestration                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Process    │  │   Parser     │  │  Telegram    │  │
│  │  Manager    │  │   Module     │  │  Notifier    │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
└─────────────┬────────────────────────────────┬─────────┘
              │                                │
              │ manages                        │ sends to
              │                                │
┌─────────────▼────────────────┐    ┌─────────▼──────────┐
│   cloudflared subprocess     │    │  Telegram API      │
│   - Quick Tunnel             │    │  - Bot API         │
│   - SSH forwarding           │    │  - Message queue   │
└──────────────────────────────┘    └────────────────────┘
```

### 2. Reliability Patterns

#### 2.1 Process Lifecycle State Machine

**States:**
- **Initializing**: Load config, validate environment
- **Starting**: Spawn cloudflared subprocess
- **Running**: Process alive, waiting for URL
- **Monitoring**: URL captured, watching for changes
- **Notifying**: Sending Telegram message
- **Retrying**: Backoff before restart attempt
- **Failed**: Terminal state (systemd will restart watcher)

#### 2.2 Error Recovery Strategy

**Hierarchical Recovery Levels**

| Level | Component | Mechanism | Timeout |
|-------|-----------|-----------|---------|
| 1 | cloudflared process | Watcher restarts | 3-5s exponential backoff |
| 2 | Telegram notification | Retry with backoff | 3 attempts, 2s/4s/8s |
| 3 | Watcher service | systemd restart | 3s (RestartSec) |
| 4 | System reboot | systemd on boot | After network-online.target |

**Exponential Backoff Algorithm**

```
attempt = 0
base_delay = 3s
max_delay = 60s
max_attempts = 10

delay = min(base_delay * (2 ^ attempt), max_delay)
```

**Implementation:**
- First retry: 3s
- Second retry: 6s
- Third retry: 12s
- Fourth retry: 24s
- Fifth retry: 48s
- Sixth+ retry: 60s (capped)
- After 10 attempts: Give up, let systemd restart watcher

### 3. Error Handling Patterns

#### 3.1 Failure Scenarios & Recovery

| Failure Type | Detection | Recovery Action | Notification |
|--------------|-----------|-----------------|--------------|
| **cloudflared not found** | Spawn error | Log error, exit (systemd restarts) | No |
| **cloudflared crashes immediately** | Exit code != 0 | Exponential backoff retry | After 3 failures |
| **Network down** | Spawn succeeds, no URL | Keep retrying, URL will appear when net up | On first success |
| **Stdout parsing error** | Regex fails | Log warning, continue monitoring | No |
| **URL extraction timeout** | No URL for 60s | Log warning, keep waiting | No |
| **Telegram API unreachable** | HTTP error 5xx | Retry 3x with backoff, then log & continue | No |
| **Invalid Telegram token** | HTTP error 401/403 | Log error, continue monitoring (don't exit) | No |
| **Process becomes zombie** | Read timeout on stdout | Kill process, restart | No |

#### 3.2 Graceful Shutdown Handling

**On SIGTERM/SIGINT:**
1. Set shutdown flag
2. Send SIGTERM to cloudflared subprocess
3. Wait up to 5s for clean exit
4. If still alive, send SIGKILL
5. Flush logs
6. Exit with code 0

### 4. Detailed Component Design

#### 4.1 Process Manager

**Responsibilities:**
- Spawn cloudflared subprocess
- Monitor process health
- Handle stdout/stderr streams
- Implement restart logic with backoff

**Key Functions:**
```
start_process()
  → spawn cloudflared with args
  → set up stdout pipe (non-blocking)
  → set up stderr pipe (for error logging)
  → return process handle

is_alive()
  → check process.poll() is None
  → verify stdout is readable

kill_process()
  → send SIGTERM
  → wait 5s
  → if still alive: SIGKILL

restart_with_backoff()
  → increment retry counter
  → calculate delay
  → sleep(delay)
  → start_process()
```

**Process Arguments:**
```bash
cloudflared tunnel --url ssh://localhost:22 --no-autoupdate
```

**Why `--no-autoupdate`:** Prevents cloudflared from auto-updating during operation, which could cause unexpected restarts.

#### 4.2 Parser Module

**Responsibilities:**
- Read stdout line-by-line
- Extract URL with regex
- Detect URL changes
- Handle malformed output

**URL Extraction Logic:**
```python
import re

URL_PATTERN = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')

def extract_url(line: str) -> str | None:
    match = URL_PATTERN.search(line)
    return match.group(0) if match else None

# Usage in read loop
current_url = None
for line in process.stdout:
    new_url = extract_url(line)
    if new_url and new_url != current_url:
        current_url = new_url
        notify_telegram(new_url)
```

**Edge Cases:**
- Multiple URLs in one line: Take first match
- Malformed URLs: Skip and log
- Empty lines: Ignore
- Non-UTF8 characters: Decode with errors='replace'

#### 4.3 Telegram Notifier

**Responsibilities:**
- Send messages via Telegram Bot API
- Implement retry logic
- Queue messages if needed
- Handle rate limits

**Message Format:**
```
🔗 New Cloudflare SSH Tunnel

URL: https://xxxxx.trycloudflare.com

Status: Active
Time: 2025-12-05 04:30:15 UTC
```

**Retry Logic:**
```python
def send_message(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            if response.status_code in [401, 403, 404]:
                # Auth error - don't retry
                log_error(f"Telegram auth error: {response.status_code}")
                return False
            # Server error - retry
            time.sleep(2 ** attempt)
        except requests.RequestException as e:
            log_error(f"Telegram request failed: {e}")
            time.sleep(2 ** attempt)
    
    return False
```

### 5. Configuration Management

#### 5.1 Environment Variables

**Required:**
```bash
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
CHAT_ID=-1001234567890
```

**Optional:**
```bash
CLOUDFLARED_PATH=/usr/local/bin/cloudflared
SSH_PORT=22
LOG_LEVEL=INFO
MAX_RETRIES=10
BASE_RETRY_DELAY=3
MAX_RETRY_DELAY=60
```

#### 5.2 Config Validation

**On startup, validate:**
1. `TELEGRAM_TOKEN` format: `\d+:[A-Za-z0-9_-]+`
2. `CHAT_ID` format: `-?\d+`
3. `cloudflared` binary exists and is executable
4. Port 22 is listening (optional warning)

**Validation failures:**
- Invalid token/chat_id: Exit with error code 1
- cloudflared not found: Exit with error code 2
- Port not listening: Log warning, continue

### 6. Logging Architecture

#### 6.1 Log Levels

| Level | Use Case | Example |
|-------|----------|---------|
| **ERROR** | Unrecoverable errors | "Failed to start cloudflared after 10 attempts" |
| **WARN** | Recoverable issues | "Telegram notification failed, retrying..." |
| **INFO** | Important events | "New URL detected: https://..." |
| **DEBUG** | Detailed diagnostics | "Parsing stdout line: ..." |

#### 6.2 Structured Logging Format

**Format:**
```
[TIMESTAMP] [LEVEL] [COMPONENT] message
```

**Examples:**
```
[2025-12-05T04:30:15Z] [INFO] [ProcessManager] Starting cloudflared process
[2025-12-05T04:30:16Z] [INFO] [Parser] URL detected: https://abc123.trycloudflare.com
[2025-12-05T04:30:17Z] [INFO] [Telegram] Notification sent successfully
[2025-12-05T04:32:10Z] [WARN] [ProcessManager] Process exited with code 1, retrying in 3s
[2025-12-05T04:35:00Z] [ERROR] [ProcessManager] Max retries exceeded, giving up
```

#### 6.3 Log Rotation

**systemd journal handles rotation automatically:**
- Default retention: 10% of filesystem or 4GB
- Access logs: `journalctl -u cloudflare-watcher.service`
- Follow logs: `journalctl -u cloudflare-watcher.service -f`
- Last 100 lines: `journalctl -u cloudflare-watcher.service -n 100`

### 7. Testing Strategy

#### 7.1 Unit Tests

**Parser Module:**
```python
def test_url_extraction():
    line = "2025-12-05T04:30:15Z INF | https://abc123.trycloudflare.com |"
    assert extract_url(line) == "https://abc123.trycloudflare.com"

def test_no_url_in_line():
    line = "Some random output"
    assert extract_url(line) is None

def test_multiple_urls():
    line = "https://first.trycloudflare.com and https://second.trycloudflare.com"
    assert extract_url(line) == "https://first.trycloudflare.com"
```

**Telegram Module:**
```python
def test_message_formatting():
    msg = format_message("https://test.trycloudflare.com")
    assert "test.trycloudflare.com" in msg
    assert "New Cloudflare SSH Tunnel" in msg

@patch('requests.post')
def test_telegram_retry(mock_post):
    mock_post.side_effect = [
        Mock(status_code=500),  # First attempt fails
        Mock(status_code=200)   # Second attempt succeeds
    ]
    assert send_message("token", "123", "test") == True
    assert mock_post.call_count == 2
```

#### 7.2 Chaos Testing

**Manual tests to verify resilience:**

1. **Network Disconnect Test:**
   ```bash
   # Disable network
   sudo ip link set eth0 down
   # Wait 30s
   # Re-enable network
   sudo ip link set eth0 up
   # Verify: URL should be sent when tunnel reconnects
   ```

2. **Process Kill Test:**
   ```bash
   # Find cloudflared PID
   ps aux | grep cloudflared
   # Kill it
   sudo kill -9 <PID>
   # Verify: Should restart within 3-5s
   ```

3. **Watcher Kill Test:**
   ```bash
   sudo systemctl kill cloudflare-watcher.service
   # Verify: systemd restarts it within 3s
   ```

### 8. Security Considerations

#### 8.1 Credential Management

**DO:**
- Store tokens in `.env` file with 600 permissions
- Never log tokens (mask in logs: `1234567890:ABC***`)
- Use systemd `EnvironmentFile` directive
- Run as dedicated user (not root if possible)

**DON'T:**
- Hardcode tokens in source code
- Store tokens in version control
- Pass tokens as command-line arguments (visible in `ps`)

#### 8.2 Process Isolation

**Recommended systemd hardening:**
```ini
[Service]
# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/cloudflare-watcher

# Resource limits
MemoryMax=500M
CPUQuota=50%
TasksMax=10
```

**Note:** Some options may conflict with cloudflared requirements. Test before production.

### 9. Monitoring & Observability

#### 9.1 Health Checks

**Internal health indicators:**
- Process alive: `process.poll() is None`
- Last URL update: `time.time() - last_url_time < 300s`
- Telegram connectivity: Last successful send within 24h

#### 9.2 Key Metrics to Track

| Metric | Collection | Threshold |
|--------|------------|-----------|
| Watcher uptime | systemd | > 99% |
| cloudflared restart count | Counter in logs | < 10/day |
| URL change frequency | Counter in logs | Varies |
| Telegram send failures | Counter in logs | < 5% |
| Average recovery time | Time between crash and URL | < 30s |

**Log-based metrics extraction:**
```bash
# Count restarts in last 24h
journalctl -u cloudflare-watcher.service --since "24 hours ago" | grep "retrying in" | wc -l

# Count successful notifications
journalctl -u cloudflare-watcher.service --since "24 hours ago" | grep "Notification sent" | wc -l
```

### 10. Performance Characteristics

#### 10.1 Resource Usage

**Expected:**
- Memory: 20-50 MB (Python), 10-20 MB (Go)
- CPU: < 1% (idle), 2-5% (during restart)
- Disk I/O: Minimal (log writes only)
- Network: < 1 KB/s (stdout parsing), spikes during Telegram sends

**cloudflared overhead:**
- Memory: 30-80 MB
- CPU: 1-3%
- Network: Depends on SSH traffic

#### 10.2 Timing Characteristics

| Event | Typical Duration | Max Acceptable |
|-------|------------------|----------------|
| Process spawn | 1-2s | 5s |
| URL detection | 2-5s after spawn | 30s |
| Telegram send | 200-500ms | 3s |
| Restart after crash | 3-6s | 15s |
| Full recovery from reboot | 10-20s | 60s |

### 11. Production Readiness Checklist

#### 11.1 Pre-Deployment

- [ ] Config validation passes
- [ ] cloudflared binary installed and executable
- [ ] Telegram bot token is valid
- [ ] Chat ID is correct
- [ ] .env file has 600 permissions
- [ ] systemd service file is correct
- [ ] All dependencies installed
- [ ] Unit tests pass
- [ ] Manual end-to-end test successful

#### 11.2 Post-Deployment

- [ ] Service starts successfully
- [ ] URL is detected within 30s
- [ ] Telegram notification received
- [ ] Logs are being written to journal
- [ ] Process survives manual kill test
- [ ] Service survives watcher kill test
- [ ] Health check script works
- [ ] Documentation is complete

### 12. Summary

This architecture provides a **minimal, reliable foundation** for the Cloudflare Tunnel Watcher:

**Key Reliability Patterns:**
1. **Layered recovery**: Process → Watcher → systemd
2. **Exponential backoff**: Prevents tight restart loops
3. **State machine**: Clear process lifecycle
4. **Fail-fast validation**: Catch config errors early
5. **Graceful degradation**: Continue on Telegram failures

**Implementation Priorities:**
1. Core loop with state machine
2. Process management with backoff
3. URL parsing and deduplication
4. Telegram client with retry
5. Logging and error handling
6. systemd integration
7. Testing and validation

This design favors **simplicity and robustness** over features, ensuring the service "just works" across network failures, crashes, and reboots.