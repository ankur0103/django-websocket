from chat.consumers import send_goodbye_to_all_consumers
import structlog

logger = structlog.get_logger(__name__)

class LifespanMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    import uuid
                    shutdown_request_id = str(uuid.uuid4())
                    logger.info("Lifespan shutdown: sending goodbye to all consumers", request_id=shutdown_request_id)
                    await send_goodbye_to_all_consumers()
                    await send({"type": "lifespan.shutdown.complete"})
                    break
        else:
            await self.app(scope, receive, send)