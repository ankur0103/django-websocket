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
                    logger.info("Lifespan shutdown: sending goodbye to all consumers")
                    await send_goodbye_to_all_consumers()
                    await send({"type": "lifespan.shutdown.complete"})
                    break
        else:
            await self.app(scope, receive, send)