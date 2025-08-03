#!/usr/bin/env python3
"""
Comprehensive WebSocket testing script.
Supports both smoke testing (for CI/CD) and interactive testing (for development).
"""

import socket
import sys
import base64
import os
import asyncio
import websockets
import json
import argparse

def test_websocket_smoke():
    """Lightweight smoke test using HTTP upgrade request (no external dependencies)."""
    try:
        # Create socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        # Connect to localhost:80 (nginx proxy)
        sock.connect(('localhost', 80))
        
        # Generate WebSocket key
        key = base64.b64encode(os.urandom(16)).decode('utf-8')
        
        # Send HTTP upgrade request
        request = (
            f"GET /ws/chat/ HTTP/1.1\r\n"
            f"Host: localhost\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        
        sock.send(request.encode())
        
        # Read response
        response = sock.recv(1024).decode()
        sock.close()
        
        # Check if we got a 101 Switching Protocols response
        if "101 Switching Protocols" in response and "Upgrade: websocket" in response:
            print(f"✅ WebSocket smoke test passed. Server accepts WebSocket connections.")
            return True
        else:
            print(f"❌ WebSocket smoke test failed. Response: {response[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket smoke test failed: {e}")
        return False

async def test_websocket_interactive(url="ws://localhost/ws/chat/"):
    """Interactive WebSocket test with full connection and messaging."""
    try:
        async with websockets.connect(url) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send a test message
            message = {"message": "Hello, WebSocket!"}
            await websocket.send(json.dumps(message))
            print(f"📤 Sent: {message}")
            
            # Receive response
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📥 Received: {data}")
            
            # Wait for heartbeat
            print("⏳ Waiting for heartbeat...")
            heartbeat = await websocket.recv()
            data = json.loads(heartbeat)
            print(f"💓 Heartbeat: {data}")
            
            return True
            
    except Exception as e:
        print(f"❌ Interactive WebSocket test failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='WebSocket testing script')
    parser.add_argument('--mode', choices=['smoke', 'interactive'], default='smoke',
                       help='Test mode: smoke (lightweight) or interactive (full connection)')
    parser.add_argument('--url', default='ws://localhost/ws/chat/',
                       help='WebSocket URL for interactive mode')
    
    args = parser.parse_args()
    
    print("🧪 WebSocket Testing")
    print("=" * 40)
    
    if args.mode == 'smoke':
        success = test_websocket_smoke()
        sys.exit(0 if success else 1)
    else:
        success = asyncio.run(test_websocket_interactive(args.url))
        print("=" * 40)
        print("🎉 Interactive test completed!")
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 