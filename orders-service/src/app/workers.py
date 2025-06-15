import asyncio
import json
import logging

from aio_pika import Message, ExchangeType
from app.messaging import (
    get_channel,
    PAYMENT_EXCHANGE,
    QUEUE_PAYMENT_REQUESTS,
    QUEUE_PAYMENT_RESULTS
)
from app.schemas import PaymentRequestEvent
from app.crud import update_order_status
from app.db import get_session
from app.models import OrdersOutbox, Order
from sqlalchemy import select, func
from app.config import settings

logger = logging.getLogger("orders.workers")

async def outbox_publisher():
    INTERVAL = settings.OUTBOX_POLL_INTERVAL

    while True:
        async for session in get_session():
            stmt = select(OrdersOutbox).where(OrdersOutbox.published_at.is_(None))
            result = await session.execute(stmt)
            events = result.scalars().all()
            logger.info("[Orders] Pending outbox events: %d", len(events))

            if events:
                channel = await get_channel()
                exchange = await channel.declare_exchange(
                    PAYMENT_EXCHANGE, ExchangeType.DIRECT, durable=True
                )

                for ev in events:
                    payload = ev.payload
                    logger.info("[Orders] Publishing request: %s", payload)
                    await exchange.publish(
                        Message(body=json.dumps(payload).encode()),
                        routing_key=QUEUE_PAYMENT_REQUESTS
                    )
                    ev.published_at = func.now()
                    session.add(ev)

                await session.commit()
                logger.info("[Orders] Outbox publish commit complete")

        await asyncio.sleep(INTERVAL)

async def result_consumer():
    channel = await get_channel()
    queue = await channel.declare_queue(QUEUE_PAYMENT_RESULTS, durable=True)
    await channel.set_qos(prefetch_count=settings.RESULT_CONSUMER_PREFETCH)

    logger.info("[Orders] Starting result_consumer on '%s'", QUEUE_PAYMENT_RESULTS)
    async with queue.iterator() as it:
        async for message in it:
            async with message.process():
                body = message.body.decode()
                logger.info("[Orders] Received result message: %s", body)
                try:
                    data = json.loads(body)
                    order_id = data["order_id"]
                    result   = data["result"]
                except Exception as e:
                    logger.error("[Orders] Invalid result format: %s", e)
                    continue

                new_status = "FINISHED" if result == "success" else "CANCELLED"
                async for session in get_session():
                    order = await session.get(Order, order_id)
                    if not order:
                        logger.warning("[Orders] Order %s not found", order_id)
                        continue
                    if order.status in ("FINISHED", "CANCELLED"):
                        logger.info("[Orders] Order %s already final status %s", order_id, order.status)
                        continue

                    order.status = new_status
                    order.updated_at = func.now()
                    session.add(order)
                    await session.commit()
                    logger.info("[Orders] Order %s status updated to %s", order_id, new_status)
