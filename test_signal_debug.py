#!/usr/bin/env python3
"""
Test script to debug signal handling issues.
"""

import signal
import time
import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_signal_handler(signum, frame):
    """Test signal handler."""
    signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    print(f"🚨 TEST: Received {signal_name} signal!")
    sys.exit(0)

def main():
    print("🧪 Testing signal handling...")
    
    # Check current signal handlers
    print(f"📋 Current SIGTERM handler: {signal.getsignal(signal.SIGTERM)}")
    print(f"📋 Current SIGINT handler: {signal.getsignal(signal.SIGINT)}")
    
    # Set our test handler
    signal.signal(signal.SIGTERM, test_signal_handler)
    signal.signal(signal.SIGINT, test_signal_handler)
    
    # Verify handlers were set
    print(f"✅ New SIGTERM handler: {signal.getsignal(signal.SIGTERM)}")
    print(f"✅ New SIGINT handler: {signal.getsignal(signal.SIGINT)}")
    
    print("⏳ Waiting for signals... (Press Ctrl+C or send SIGTERM)")
    print(f"📝 Process ID: {os.getpid()}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🔄 KeyboardInterrupt received")

if __name__ == "__main__":
    main() 