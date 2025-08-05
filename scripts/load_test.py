#!/usr/bin/env python3
"""
Load testing script for Django WebSocket service.
Tests concurrent WebSocket connections and message throughput.
"""

import asyncio
import json
import time
import uuid
import websockets
import argparse
import statistics
from datetime import datetime
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSocketLoadTester:
    def __init__(self, url: str, num_connections: int, messages_per_connection: int, 
                 message_interval: float, test_duration: int, debug: bool = False):
        self.url = url
        self.num_connections = num_connections
        self.messages_per_connection = messages_per_connection
        self.message_interval = message_interval
        self.test_duration = test_duration
        self.connections: List[websockets.WebSocketServerProtocol] = []
        self.results: List[Dict[str, Any]] = []
        self.start_time = None
        self.end_time = None
        self.debug = debug
        
    async def create_connection(self, connection_id: int) -> websockets.WebSocketServerProtocol:
        """Create a single WebSocket connection."""
        try:
            session_uuid = str(uuid.uuid4())
            ws_url = f"{self.url}?session_uuid={session_uuid}"
            websocket = await websockets.connect(ws_url)
            
            logger.info(f"Connection {connection_id} established")
            return websocket
        except Exception as e:
            logger.error(f"Failed to create connection {connection_id}: {e}")
            return None
    
    async def send_messages(self, websocket: websockets.WebSocketServerProtocol, 
                          connection_id: int) -> Dict[str, Any]:
        """Send messages on a single connection and collect metrics."""
        results = {
            'connection_id': connection_id,
            'messages_sent': 0,
            'messages_received': 0,
            'messages_with_count': 0,
            'errors': 0,
            'latencies': [],
            'start_time': time.time()
        }
        
        try:
            for i in range(self.messages_per_connection):
                if not websocket.open:
                    break
                    
                # Send message
                message = {
                    'message': f'Test message {i} from connection {connection_id}'
                }
                
                send_time = time.time()
                msg_str = json.dumps(message)
                await websocket.send(msg_str)
                if self.debug:
                    logger.debug(f"[Conn {connection_id}] Sent (dict): {message}")
                
                # Read all available messages after sending
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=1)
                        data = json.loads(response)
                        if self.debug:
                            logger.debug(f"[Conn {connection_id}] Received (dict): {data}")
                        receive_time = time.time()
                        if 'count' in data:
                            results['messages_received'] += 1
                            results['messages_with_count'] += 1
                            results['latencies'].append(receive_time - send_time)
                        elif 'session_uuid' in data:
                            results['messages_received'] += 1
                            results['latencies'].append(receive_time - send_time)
                        elif 'ts' in data:
                            # Heartbeat message
                            continue
                        else:
                            results['errors'] += 1
                    except asyncio.TimeoutError:
                        break
                    except Exception as e:
                        import traceback
                        results['errors'] += 1
                        logger.error(f"Error on connection {connection_id} during message send/receive: {e}\n{traceback.format_exc()}")
                        break
                
                results['messages_sent'] += 1
                
                # Wait before next message
                if self.message_interval > 0:
                    await asyncio.sleep(self.message_interval)
                    
        except Exception as e:
            import traceback
            logger.error(f"Error in connection {connection_id}: {e}\n{traceback.format_exc()}")
            results['errors'] += 1
            
        results['end_time'] = time.time()

        return results
    
    async def run_test(self):
        """Run the complete load test."""
        logger.info(f"Starting load test with {self.num_connections} connections")
        self.start_time = time.time()
        
        # Create connections gradually to avoid overwhelming the server
        logger.info("Creating connections gradually...")
        connection_tasks = []
        batch_size = 50  # Smaller batches for higher success rate with 5000+ connections
        
        for i in range(0, self.num_connections, batch_size):
            batch_end = min(i + batch_size, self.num_connections)
            logger.info(f"Creating connections {i} to {batch_end-1}...")
            
            # Create batch of connections
            batch_tasks = []
            for j in range(i, batch_end):
                task = asyncio.create_task(self.create_connection(j))
                batch_tasks.append(task)
                # Slightly longer delay between connections for stability
                await asyncio.sleep(0.002)
            
            # Wait for this batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            connection_tasks.extend(batch_results)
            
            # Longer delay between batches for server recovery
            await asyncio.sleep(0.1)
        
        # Filter successful connections
        self.connections = [ws for ws in connection_tasks if ws is not None and not isinstance(ws, Exception)]
        
        logger.info(f"Successfully created {len(self.connections)} connections")
        
        # Send messages on all connections
        logger.info("Sending messages...")
        message_tasks = []
        for i, websocket in enumerate(self.connections):
            task = asyncio.create_task(self.send_messages(websocket, i))
            message_tasks.append(task)
        
        # Wait for all message tasks to complete or timeout
        try:
            self.results = await asyncio.wait_for(
                asyncio.gather(*message_tasks, return_exceptions=True),
                timeout=self.test_duration
            )
        except asyncio.TimeoutError:
            logger.warning("Test duration exceeded, stopping...")
        
        self.end_time = time.time()
        
        # Close all connections
        logger.info("Closing connections...")
        close_tasks = []
        for websocket in self.connections:
            if websocket.open:
                close_tasks.append(websocket.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        logger.info("Load test completed")
    
    def print_results(self):
        """Print test results and statistics."""
        if not self.results:
            logger.warning("No results to display")
            return
        
        # Filter out exceptions
        valid_results = [r for r in self.results if isinstance(r, dict)]
        
        if not valid_results:
            logger.warning("No valid results to display")
            return
        
        total_duration = self.end_time - self.start_time
        total_messages_sent = sum(r['messages_sent'] for r in valid_results)
        total_messages_received = sum(r['messages_received'] for r in valid_results)
        total_messages_with_count = sum(r.get('messages_with_count', 0) for r in valid_results)
        total_errors = sum(r['errors'] for r in valid_results)
        
        # Calculate latencies
        all_latencies = []
        for r in valid_results:
            all_latencies.extend(r['latencies'])
        
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)
        print(f"Test Duration: {total_duration:.2f} seconds")
        print(f"Connections Created: {len(self.connections)}")
        print(f"Connections Successful: {len(valid_results)}")
        print(f"Total Messages Sent: {total_messages_sent}")
        print(f"Total Messages Received: {total_messages_received}")
        print(f"Total Messages With 'count': {total_messages_with_count}")
        print(f"Total Errors: {total_errors}")
        print(f"Success Rate: {(total_messages_received/total_messages_sent*100):.2f}%" if total_messages_sent > 0 else "N/A")
        
        if all_latencies:
            print(f"Average Latency: {statistics.mean(all_latencies)*1000:.2f} ms")
            print(f"Median Latency: {statistics.median(all_latencies)*1000:.2f} ms")
            print(f"Min Latency: {min(all_latencies)*1000:.2f} ms")
            print(f"Max Latency: {max(all_latencies)*1000:.2f} ms")
            print(f"95th Percentile: {statistics.quantiles(all_latencies, n=20)[18]*1000:.2f} ms")
        
        print(f"Messages per Second: {total_messages_sent/total_duration:.2f}")
        print(f"Connections per Second: {len(self.connections)/total_duration:.2f}")
        print("="*60)

async def main():
    parser = argparse.ArgumentParser(description='Load test Django WebSocket service')
    parser.add_argument('--url', default='ws://localhost/ws/chat/', 
                       help='WebSocket URL (default: ws://localhost/ws/chat/)')
    parser.add_argument('--connections', type=int, default=10,
                       help='Number of concurrent connections (default: 100)')
    parser.add_argument('--messages', type=int, default=10,
                       help='Messages per connection (default: 10)')
    parser.add_argument('--interval', type=float, default=0.1,
                       help='Interval between messages in seconds (default: 0.1)')
    parser.add_argument('--duration', type=int, default=60,
                       help='Test duration in seconds (default: 60)')
    parser.add_argument('--target', type=int, default=10,
                       help='Target concurrent connections (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging of all messages')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # If target is specified, use it instead of connections
    if args.target > args.connections:
        args.connections = args.target
    
    logger.info(f"Load test configuration:")
    logger.info(f"  URL: {args.url}")
    logger.info(f"  Connections: {args.connections}")
    logger.info(f"  Messages per connection: {args.messages}")
    logger.info(f"  Message interval: {args.interval}s")
    logger.info(f"  Test duration: {args.duration}s")
    
    # Run the test
    tester = WebSocketLoadTester(
        url=args.url,
        num_connections=args.connections,
        messages_per_connection=args.messages,
        message_interval=args.interval,
        test_duration=args.duration,
        debug=args.debug
    )
    
    try:
        await tester.run_test()
        tester.print_results()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == '__main__':
    asyncio.run(main()) 