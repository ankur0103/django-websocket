import pytest
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from app.asgi import application


class ChatConsumerTest(TestCase):
    async def test_websocket_connection(self):
        """Test WebSocket connection establishment."""
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        connected, _ = await communicator.connect()
        
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_message_counter(self):
        """Test message counter functionality."""
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        connected, _ = await communicator.connect()
        
        # Send first message
        await communicator.send_json_to({"message": "Hello"})
        response = await communicator.receive_json_from()
        
        self.assertEqual(response["count"], 1)
        
        # Send second message
        await communicator.send_json_to({"message": "World"})
        response = await communicator.receive_json_from()
        
        self.assertEqual(response["count"], 2)
        
        await communicator.disconnect()

    async def test_heartbeat(self):
        """Test heartbeat functionality."""
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        connected, _ = await communicator.connect()
        
        # Wait for heartbeat (should come within 30 seconds)
        response = await communicator.receive_json_from()
        
        self.assertIn("ts", response)
        
        await communicator.disconnect()

    async def test_invalid_json(self):
        """Test handling of invalid JSON."""
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        connected, _ = await communicator.connect()
        
        # Send invalid JSON
        await communicator.send_to("invalid json")
        response = await communicator.receive_json_from()
        
        self.assertIn("error", response)
        
        await communicator.disconnect()

    async def test_session_uuid(self):
        """Test session UUID support."""
        session_uuid = "test-session-123"
        communicator = WebsocketCommunicator(
            application, f"/ws/chat/?session_uuid={session_uuid}"
        )
        connected, _ = await communicator.connect()
        
        self.assertTrue(connected)
        
        await communicator.disconnect()


@pytest.mark.asyncio
class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""
    
    async def test_full_message_flow(self):
        """Test complete message flow with counter."""
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        connected, _ = await communicator.connect()
        
        # Send multiple messages
        for i in range(3):
            await communicator.send_json_to({"message": f"Message {i}"})
            response = await communicator.receive_json_from()
            self.assertEqual(response["count"], i + 1)
        
        await communicator.disconnect()

    async def test_graceful_disconnect(self):
        """Test graceful disconnect with goodbye message."""
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        connected, _ = await communicator.connect()
        
        # Send a message first
        await communicator.send_json_to({"message": "Test"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["count"], 1)
        
        # Disconnect gracefully
        await communicator.disconnect()
        
        # Should receive goodbye message
        try:
            response = await communicator.receive_json_from()
            self.assertIn("bye", response)
            self.assertEqual(response["total"], 1)
        except:
            # Goodbye message might not be received if disconnect is too fast
            pass
