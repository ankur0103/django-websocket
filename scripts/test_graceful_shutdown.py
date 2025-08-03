#!/usr/bin/env python3
"""
Test script to verify graceful shutdown behavior.
Tests that the server sends goodbye messages and closes connections gracefully on SIGTERM.
"""

import asyncio
import websockets
import json
import time
import signal
import sys

async def test_graceful_shutdown(url="ws://localhost/ws/chat/"):
    """Test graceful shutdown by connecting and then sending SIGTERM."""
    uri = url
    
    try:
        print("🔌 Connecting to WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send a test message
            message = {"message": "Hello, graceful shutdown test!"}
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
            
            print("🛑 Now sending SIGTERM to test graceful shutdown...")
            
            # Send SIGTERM to the server
            import subprocess
            try:
                result = subprocess.run(['lsof', '-ti:8000'], capture_output=True, text=True)
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            print(f"📤 Sending SIGTERM to PID {pid}")
                            subprocess.run(['kill', '-TERM', pid])
                else:
                    print("⚠️  No process found on port 8000")
            except FileNotFoundError:
                print("⚠️  'lsof' command not found. Please install it or manually send SIGTERM.")
                print("   You can manually send SIGTERM using: lsof -ti:8000 | xargs kill -TERM")
            
            # Wait for goodbye message or connection close
            print("⏳ Waiting for goodbye message or connection close...")
            try:
                # Wait for goodbye message
                goodbye = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(goodbye)
                print(f"👋 Goodbye message: {data}")
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for goodbye message")
            
            # Wait for connection to close
            try:
                await websocket.wait_closed()
                print("🔌 Connection closed")
            except Exception as e:
                print(f"❌ Error waiting for close: {e}")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"🔌 Connection closed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test graceful shutdown behavior')
    parser.add_argument('--url', default='ws://localhost/ws/chat/',
                       help='WebSocket URL to test')
    
    args = parser.parse_args()
    
    print("🧪 Testing Graceful Shutdown")
    print("=" * 50)
    asyncio.run(test_graceful_shutdown(args.url))
    print("=" * 50)
    print("🎉 Test completed!")

if __name__ == "__main__":
    main() 