import signal
import asyncio
import structlog
from django.conf import settings
from .consumers import send_goodbye_to_all_consumers, active_consumers

logger = structlog.get_logger(__name__)

# Global flag to track shutdown state
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle SIGTERM and SIGINT signals for graceful shutdown."""
    global shutdown_requested
    
    signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    logger.info(f"🚨 Received {signal_name} signal, initiating graceful shutdown...")
    
    if shutdown_requested:
        logger.warning("⚠️  Shutdown already in progress, forcing exit")
        exit(1)
    
    shutdown_requested = True
    logger.info(f"🔄 Starting graceful shutdown process for {signal_name}")
    
    # Schedule the graceful shutdown in the event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(graceful_shutdown())
        else:
            # If no event loop is running, run the shutdown directly
            asyncio.run(graceful_shutdown())
    except RuntimeError:
        # No event loop available, exit immediately
        logger.error("No event loop available for graceful shutdown")
        exit(1)
    except Exception as e:
        logger.error(f"Error during signal handling: {e}")
        # Fall back to immediate exit
        exit(1)

async def graceful_shutdown():
    """Perform graceful shutdown of all WebSocket connections."""
    global shutdown_requested
    
    logger.info("🔄 Starting graceful shutdown process")
    
    # Send goodbye messages to all active consumers
    if active_consumers:
        logger.info(f"📤 Sending goodbye messages to {len(active_consumers)} active connections")
        await send_goodbye_to_all_consumers()
    else:
        logger.info("📭 No active connections to close")
    
    # Close all WebSocket connections with code 1001 (going away)
    close_tasks = []
    for consumer in list(active_consumers):
        if consumer.is_connected:
            task = asyncio.create_task(close_consumer_gracefully(consumer))
            close_tasks.append(task)
    
    if close_tasks:
        # Wait for all connections to close with timeout
        timeout = getattr(settings, 'GRACEFUL_SHUTDOWN_TIMEOUT', 10)
        logger.info(f"⏳ Waiting up to {timeout} seconds for connections to close gracefully...")
        try:
            await asyncio.wait_for(asyncio.gather(*close_tasks, return_exceptions=True), timeout=timeout)
            logger.info("✅ All WebSocket connections closed gracefully")
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Graceful shutdown timeout after {timeout} seconds, forcing close")
            # Force close remaining connections
            for consumer in list(active_consumers):
                if consumer.is_connected:
                    try:
                        await consumer.close(code=1001)
                    except Exception as e:
                        logger.error(f"❌ Error forcing close: {e}")
    else:
        logger.info("✅ No connections to close")
    
    logger.info("🎉 Graceful shutdown completed successfully")

async def close_consumer_gracefully(consumer):
    """Close a single consumer gracefully."""
    try:
        # Close with code 1001 (going away)
        await consumer.close(code=1001)
        logger.info(f"Consumer closed gracefully", connection_id=consumer.connection_id)
    except Exception as e:
        logger.error(f"Error closing consumer gracefully", connection_id=consumer.connection_id, error=str(e))

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    logger.info("🔄 Setting up signal handlers for graceful shutdown...")
    try:
        # Store original handlers to restore if needed
        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)
        
        # Set our custom handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("✅ Signal handlers configured for SIGTERM and SIGINT")
        logger.debug(f"Original SIGTERM handler: {original_sigterm}")
        logger.debug(f"Original SIGINT handler: {original_sigint}")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup signal handlers: {e}")
        # Continue without signal handlers rather than crashing 