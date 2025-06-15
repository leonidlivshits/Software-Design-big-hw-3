import asyncio
import logging
from aio_pika import connect_robust, ExchangeType
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel
from app.config import settings

logger = logging.getLogger("payments.messaging")

PAYMENT_EXCHANGE       = "payment_exchange"
QUEUE_PAYMENT_REQUESTS = "payment_requests"
QUEUE_PAYMENT_RESULTS  = "payment_results"

rabbit_connection: AbstractRobustConnection | None = None
rabbit_channel:    AbstractRobustChannel     | None = None

async def init_rabbit(retry_attempts: int = 5, retry_delay: int = 2) -> None:
    global rabbit_connection, rabbit_channel
    url = f"amqp://{settings.RABBIT_USER}:{settings.RABBIT_PASSWORD}@{settings.RABBIT_HOST}:{settings.RABBIT_PORT}/"

    for attempt in range(1, retry_attempts + 1):
        try:
            logger.info(f"[Payments] Connecting to RabbitMQ (attempt {attempt}/{retry_attempts})")
            rabbit_connection = await connect_robust(url)
            rabbit_channel    = await rabbit_connection.channel()

            exchange = await rabbit_channel.declare_exchange(
                PAYMENT_EXCHANGE, ExchangeType.DIRECT, durable=True
            )
            queue_req = await rabbit_channel.declare_queue(
                QUEUE_PAYMENT_REQUESTS, durable=True
            )
            await queue_req.bind(exchange, QUEUE_PAYMENT_REQUESTS)
            queue_res = await rabbit_channel.declare_queue(
                QUEUE_PAYMENT_RESULTS, durable=True
            )
            await queue_res.bind(exchange, QUEUE_PAYMENT_RESULTS)

            logger.info("[Payments] RabbitMQ setup complete")
            return
        except Exception as e:
            logger.error(f"[Payments] RabbitMQ init failed: {e}")
            if attempt < retry_attempts:
                await asyncio.sleep(retry_delay)
            else:
                logger.critical("[Payments] Could not connect to RabbitMQ, giving up")
                raise

async def get_channel() -> AbstractRobustChannel:
    if rabbit_channel is None:
        await init_rabbit()
    return rabbit_channel

async def close_rabbit() -> None:
    global rabbit_connection
    if rabbit_connection:
        await rabbit_connection.close()
        logger.info("[Payments] RabbitMQ connection closed")
