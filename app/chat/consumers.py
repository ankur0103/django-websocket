import json
import uuid
import asyncio
import structlog
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from django.conf import settings
from monitoring.metrics import connection_tracker

# Global tracking for graceful shutdown
active_consumers = set()
active_requests = set()  # Track in-flight message processing

# Session storage for reconnection
session_store = {}  # session_uuid -> message_count

logger = structlog.get_logger(__name__)



async def send_goodbye_to_all_consumers():
    """Send goodbye message to all active consumers during shutdown."""
    logger.info("Sending goodbye messages to all active connections", count=len(active_consumers))
    
    goodbye_tasks = []
    for consumer in list(active_consumers):
        if consumer.is_connected:
            task = asyncio.create_task(send_goodbye_to_consumer(consumer))
            goodbye_tasks.append(task)
    
    if goodbye_tasks:
        # Wait for all goodbye messages to be sent
        await asyncio.gather(*goodbye_tasks, return_exceptions=True)
        logger.info("All goodbye messages sent")

async def send_goodbye_to_consumer(consumer):
    """Send goodbye message to a specific consumer."""
    try:
        await consumer.send(text_data=json.dumps({
            "bye": True,
            "total": consumer.message_count
        }))
        logger.info(
            "Goodbye message sent",
            connection_id=consumer.connection_id,
            message_count=consumer.message_count
        )
    except Exception as e:
        logger.error("Failed to send goodbye message", connection_id=consumer.connection_id, error=str(e))

def cleanup_old_sessions():
    """Clean up sessions that are no longer active (only very old ones)."""
    global session_store
    
    # For now, keep all sessions for reconnection
    # In production, you might want to add timestamp tracking and remove sessions older than X hours
    logger.info("Session cleanup skipped - keeping all sessions for reconnection", active_sessions=len(session_store))

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection_id = None
        self.message_count = 0
        self.session_uuid = None
        self.heartbeat_task = None
        self.is_connected = False

    async def connect(self):
        """Handle WebSocket connection."""
        try:
            logger.info("Starting WebSocket connection process")
            
            # Extract session UUID from query parameters for reconnection
            query_string = self.scope.get('query_string', b'').decode()
            if 'session_uuid=' in query_string:
                self.session_uuid = query_string.split('session_uuid=')[1].split('&')[0]
                logger.info("Reconnecting client", session_uuid=self.session_uuid)
                
                # Check if session exists and resume counter
                if self.session_uuid in session_store:
                    self.message_count = session_store[self.session_uuid]
                    logger.info("Session resumed", session_uuid=self.session_uuid, message_count=self.message_count)
                else:
                    logger.info("Session not found, starting fresh", session_uuid=self.session_uuid)
            else:
                # Generate new session UUID for new connections
                self.session_uuid = str(uuid.uuid4())
                logger.info("New client connection", session_uuid=self.session_uuid)
            
            # Generate connection ID
            self.connection_id = str(uuid.uuid4())
            logger.info("Generated connection ID", connection_id=self.connection_id)
            
            # Clean up old sessions periodically (every 10th connection)
            if len(active_consumers) % 10 == 0:
                cleanup_old_sessions()
            
            # Accept the connection
            logger.info("Accepting WebSocket connection", connection_id=self.connection_id)
            await self.accept()
            logger.info("WebSocket connection accepted", connection_id=self.connection_id)
            
            # Send session UUID to client
            await self.send(text_data=json.dumps({
                "session_uuid": self.session_uuid
            }))
            logger.info("Session UUID sent to client", session_uuid=self.session_uuid)
            
            self.is_connected = True
            logger.info("Connection marked as connected", connection_id=self.connection_id)
            
            # Track connection
            logger.info("Adding to connection tracker", connection_id=self.connection_id)
            connection_tracker.add_connection(self.connection_id)
            
            logger.info("Adding to active consumers", connection_id=self.connection_id)
            active_consumers.add(self)
            logger.info("Consumer added to active_consumers", 
                       connection_id=self.connection_id, 
                       active_count=len(active_consumers))
            
            # Start heartbeat
            logger.info("Starting heartbeat task", connection_id=self.connection_id)
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("Heartbeat task created", connection_id=self.connection_id)
            
            logger.info(
                "WebSocket connected successfully",
                connection_id=self.connection_id,
                session_uuid=self.session_uuid,
                color=getattr(settings, 'APP_COLOR', 'unknown')
            )
            
        except Exception as e:
            logger.error("WebSocket connection failed", error=str(e), connection_id=getattr(self, 'connection_id', 'unknown'))
            # Safely increment error metric
            try:
                from monitoring.metrics import websocket_errors_total
                websocket_errors_total.labels(
                    color=getattr(settings, 'APP_COLOR', 'unknown'), 
                    error_type="connection_failed"
                ).inc()
            except Exception:
                pass
            raise

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        try:
            self.is_connected = False
            
            # Cancel heartbeat task
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # Log disconnect with special handling for graceful shutdown
            if close_code == 1001:
                logger.info(
                    "WebSocket disconnected (graceful shutdown)",
                    connection_id=self.connection_id,
                    message_count=self.message_count,
                    close_code=close_code,
                    color=getattr(settings, 'APP_COLOR', 'unknown')
                )
            elif close_code == 1012:  # Service restart
                logger.info(
                    "WebSocket disconnected (service restart)",
                    connection_id=self.connection_id,
                    message_count=self.message_count,
                    close_code=close_code,
                    color=getattr(settings, 'APP_COLOR', 'unknown')
                )
            elif close_code == 1006:
                logger.warning(
                    "WebSocket disconnected abnormally (code 1006)",
                    connection_id=self.connection_id,
                    message_count=self.message_count,
                    close_code=close_code,
                    color=getattr(settings, 'APP_COLOR', 'unknown')
                )
                
                
            else:
                logger.info(
                    "WebSocket disconnected",
                    connection_id=self.connection_id,
                    message_count=self.message_count,
                    close_code=close_code,
                    color=getattr(settings, 'APP_COLOR', 'unknown')
                )
            
            # Remove from tracking
            if self.connection_id:
                connection_tracker.remove_connection(self.connection_id)
            
            # Remove from tracking
            active_consumers.discard(self)
            
            # Keep session in store for potential reconnection
            # Only remove if explicitly requested or after a long timeout
            if self.session_uuid and self.session_uuid in session_store:
                logger.info("Session kept in store for reconnection", session_uuid=self.session_uuid, message_count=session_store[self.session_uuid])
            
        except Exception as e:
            logger.error("Error during disconnect", error=str(e))
            # Safely increment error metric
            try:
                from monitoring.metrics import websocket_errors_total
                websocket_errors_total.labels(
                    color=getattr(settings, 'APP_COLOR', 'unknown'), 
                    error_type="disconnect_error"
                ).inc()
            except Exception:
                pass



    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        start_time = asyncio.get_event_loop().time()
        request_id = str(uuid.uuid4())
        
        # Track this request as in-flight
        active_requests.add(request_id)
        
        try:
            # Parse message
            data = json.loads(text_data)
            
            # Handle disconnect action
            if data.get('action') == 'disconnect':
                # Send goodbye message
                await self.send(text_data=json.dumps({
                    "bye": True,
                    "total": self.message_count
                }))
                
                logger.info(
                    "Disconnect requested",
                    connection_id=self.connection_id,
                    message_count=self.message_count,
                    color=getattr(settings, 'APP_COLOR', 'unknown')
                )
                return
            
            # Handle regular message
            message = data.get('message', '')
            
            # Increment message counter
            self.message_count += 1
            
            # Update session store with current count
            if self.session_uuid:
                session_store[self.session_uuid] = self.message_count
            
            # Send response with count
            response = {
                "count": self.message_count
            }
            
            await self.send(text_data=json.dumps(response))
            
            # Record metrics safely
            try:
                from monitoring.metrics import websocket_messages_total, websocket_message_duration
                websocket_messages_total.labels(
                    color=getattr(settings, 'APP_COLOR', 'unknown'), 
                    type="received"
                ).inc()
                
                duration = asyncio.get_event_loop().time() - start_time
                websocket_message_duration.labels(color=getattr(settings, 'APP_COLOR', 'unknown')).observe(duration)
            except Exception:
                pass
            
            logger.info(
                "Message processed",
                connection_id=self.connection_id,
                message_count=self.message_count,
                message_length=len(message),
                duration=asyncio.get_event_loop().time() - start_time,
                color=getattr(settings, 'APP_COLOR', 'unknown')
            )
            
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON received", error=str(e))
            # Safely increment error metric
            try:
                from monitoring.metrics import websocket_errors_total
                websocket_errors_total.labels(
                    color=getattr(settings, 'APP_COLOR', 'unknown'), 
                    error_type="json_decode_error"
                ).inc()
            except Exception:
                pass
            await self.send(text_data=json.dumps({
                "error": "Invalid JSON format"
            }))
            

        except Exception as e:
            logger.error("Error processing message", error=str(e))
            # Safely increment error metric
            try:
                from monitoring.metrics import websocket_errors_total
                websocket_errors_total.labels(
                    color=getattr(settings, 'APP_COLOR', 'unknown'), 
                    error_type="processing_error"
                ).inc()
            except Exception:
                pass
            await self.send(text_data=json.dumps({
                "error": "Internal server error"
            }))
        finally:
            # Remove request from tracking
            active_requests.discard(request_id)


    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages."""
        logger.info("Heartbeat loop started", connection_id=self.connection_id)
        try:
            while self.is_connected:
                try:
                    await asyncio.sleep(getattr(settings, 'HEARTBEAT_INTERVAL', 30))
                    
                    if self.is_connected:
                        heartbeat = {
                            "ts": datetime.utcnow().isoformat() + "Z"
                        }
                        await self.send(text_data=json.dumps(heartbeat))
                        
                        logger.debug(
                            "Heartbeat sent",
                            connection_id=self.connection_id,
                            color=getattr(settings, 'APP_COLOR', 'unknown')
                        )
                    else:
                        logger.info("Connection no longer connected, stopping heartbeat", connection_id=self.connection_id)
                        break
                        
                except asyncio.CancelledError:
                    logger.info("Heartbeat task cancelled", connection_id=self.connection_id)
                    break
                except Exception as e:
                    logger.error("Heartbeat error", error=str(e), connection_id=self.connection_id)
                    break
        except Exception as e:
            logger.error("Heartbeat loop outer error", error=str(e), connection_id=self.connection_id)
        finally:
            logger.info("Heartbeat loop ended", connection_id=self.connection_id)
        
    async def close(self, code=1000):
        """Close the WebSocket connection with specified code."""
        if self.is_connected:
            try:
                await super().close(code=code)
                logger.info(f"WebSocket connection closed with code {code}", connection_id=self.connection_id)
            except Exception as e:
                logger.error(f"Error closing WebSocket connection", connection_id=self.connection_id, error=str(e))
        
 