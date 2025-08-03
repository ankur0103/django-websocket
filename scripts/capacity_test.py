#!/usr/bin/env python3
"""
Capacity testing script to determine actual connection limits per worker.
This script helps validate the 1250 connections per worker assumption.
"""

import asyncio
import websockets
import json
import time
import statistics
import argparse
from typing import List, Dict
import sys

class CapacityTester:
    def __init__(self, target_url: str, max_connections: int = 2000, step_size: int = 100):
        self.target_url = target_url
        self.max_connections = max_connections
        self.step_size = step_size
        self.connections: List[websockets.WebSocketServerProtocol] = []
        self.results: Dict[int, Dict] = {}
        
    async def test_connection_capacity(self):
        """Test connection capacity in steps."""
        print(f"Testing connection capacity for: {self.target_url}")
        print(f"Max connections: {self.max_connections}, Step size: {self.step_size}")
        print("-" * 60)
        
        for connection_count in range(self.step_size, self.max_connections + 1, self.step_size):
            print(f"\nTesting {connection_count} connections...")
            
            # Create connections
            start_time = time.time()
            success_count = await self.create_connections(connection_count)
            connect_time = time.time() - start_time
            
            if success_count < connection_count:
                print(f"❌ Failed to create {connection_count} connections. Only {success_count} succeeded.")
                print(f"   Connection limit reached at {success_count} connections.")
                break
            
            # Test message sending
            start_time = time.time()
            message_success = await self.test_message_sending()
            message_time = time.time() - start_time
            
            # Calculate metrics
            memory_usage = await self.get_memory_usage()
            
            self.results[connection_count] = {
                'connections_created': success_count,
                'connect_time': connect_time,
                'message_success': message_success,
                'message_time': message_time,
                'memory_mb': memory_usage,
                'connections_per_second': success_count / connect_time if connect_time > 0 else 0
            }
            
            print(f"✅ {success_count} connections created in {connect_time:.2f}s")
            print(f"   Memory usage: {memory_usage:.1f}MB")
            print(f"   Message test: {'✅' if message_success else '❌'}")
            
            # Check for performance degradation
            if connect_time > 10.0:  # More than 10 seconds to connect
                print(f"⚠️  Performance degradation detected at {connection_count} connections")
                break
                
            if memory_usage > 1024:  # More than 1GB memory
                print(f"⚠️  Memory limit reached at {connection_count} connections")
                break
    
    async def create_connections(self, count: int) -> int:
        """Create the specified number of WebSocket connections."""
        tasks = []
        for i in range(count):
            task = self.create_single_connection(i)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_connections = [r for r in results if isinstance(r, websockets.WebSocketServerProtocol)]
        
        # Store successful connections
        self.connections.extend(successful_connections)
        
        return len(successful_connections)
    
    async def create_single_connection(self, index: int) -> websockets.WebSocketServerProtocol:
        """Create a single WebSocket connection."""
        try:
            uri = f"{self.target_url}/ws/chat/"
            websocket = await websockets.connect(uri)
            
            # Wait for initial message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                if 'session_uuid' in data:
                    return websocket
            except (asyncio.TimeoutError, json.JSONDecodeError):
                pass
                
            return websocket
        except Exception as e:
            print(f"Connection {index} failed: {e}")
            raise
    
    async def test_message_sending(self) -> bool:
        """Test sending messages to all connections."""
        if not self.connections:
            return False
            
        # Send a test message to a sample of connections
        sample_size = min(10, len(self.connections))
        sample_connections = self.connections[:sample_size]
        
        tasks = []
        for i, websocket in enumerate(sample_connections):
            task = self.send_test_message(websocket, f"test_message_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_sends = sum(1 for r in results if r is True)
        
        return successful_sends >= sample_size * 0.8  # 80% success rate
    
    async def send_test_message(self, websocket, message: str) -> bool:
        """Send a test message to a single connection."""
        try:
            await websocket.send(json.dumps({"message": message}))
            return True
        except Exception:
            return False
    
    async def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0
    
    async def cleanup(self):
        """Close all connections."""
        if self.connections:
            print(f"\nCleaning up {len(self.connections)} connections...")
            tasks = [websocket.close() for websocket in self.connections]
            await asyncio.gather(*tasks, return_exceptions=True)
            self.connections.clear()
    
    def print_summary(self):
        """Print test summary and recommendations."""
        if not self.results:
            print("No test results available.")
            return
        
        print("\n" + "=" * 60)
        print("CAPACITY TEST SUMMARY")
        print("=" * 60)
        
        # Find the maximum successful connections
        max_connections = max(self.results.keys())
        max_result = self.results[max_connections]
        
        print(f"Maximum connections tested: {max_connections}")
        print(f"Memory usage at max: {max_result['memory_mb']:.1f}MB")
        print(f"Connection rate: {max_result['connections_per_second']:.1f} connections/second")
        
        # Calculate recommendations
        memory_per_connection = max_result['memory_mb'] / max_connections if max_connections > 0 else 0
        
        print(f"\nRECOMMENDATIONS:")
        print(f"- Memory per connection: {memory_per_connection:.2f}MB")
        
        # Calculate safe limits based on 1GB memory
        safe_connections_1gb = int(1024 / memory_per_connection) if memory_per_connection > 0 else 1000
        print(f"- Safe limit (1GB memory): ~{safe_connections_1gb} connections")
        
        # Calculate safe limits based on 2GB memory
        safe_connections_2gb = int(2048 / memory_per_connection) if memory_per_connection > 0 else 2000
        print(f"- Safe limit (2GB memory): ~{safe_connections_2gb} connections")
        
        # Worker recommendations
        workers_4 = safe_connections_1gb // 4
        workers_8 = safe_connections_1gb // 8
        
        print(f"\nWORKER RECOMMENDATIONS:")
        print(f"- 4 workers: ~{workers_4} connections per worker")
        print(f"- 8 workers: ~{workers_8} connections per worker")
        
        print(f"\nPERFORMANCE METRICS:")
        for connections, result in self.results.items():
            print(f"  {connections:4d} connections: {result['connect_time']:5.2f}s, {result['memory_mb']:6.1f}MB")

async def main():
    parser = argparse.ArgumentParser(description='Test WebSocket connection capacity')
    parser.add_argument('--url', default='ws://localhost', help='WebSocket URL')
    parser.add_argument('--max', type=int, default=2000, help='Maximum connections to test')
    parser.add_argument('--step', type=int, default=100, help='Step size for testing')
    
    args = parser.parse_args()
    
    tester = CapacityTester(args.url, args.max, args.step)
    
    try:
        await tester.test_connection_capacity()
        tester.print_summary()
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 