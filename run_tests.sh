#!/bin/bash
# Run all tests for Cloudflare Tunnel Watcher

set -e

echo "Running Cloudflare Tunnel Watcher Tests"
echo "========================================"
echo ""

# Set Python path to include src directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run tests with unittest
echo "Running unit tests..."
python3 -m unittest discover -s tests -p "test_*.py" -v

echo ""
echo "========================================"
echo "All tests completed!"