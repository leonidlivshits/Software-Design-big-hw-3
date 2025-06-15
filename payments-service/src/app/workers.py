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
from app.crud import process_payment_event
from app.db import get_session
from app.models import PaymentsOutbox
from sqlalchemy import select, func
from app.config import settings

logger = logging.getLogger("payments.workers")

async def inbox_consumer():
    channel = await get_channel()
    queue = await channel.declare_queue(QUEUE_PAYMENT_REQUESTS, durable=True)
    await channel.set_qos(prefetch_count=settings.INBOX_PREFETCH_COUNT)

    logger.info("[Payments] Starting inbox_consumer on queue '%s'", QUEUE_PAYMENT_REQUESTS)
    async with queue.iterator() as it:
        async for message in it:
            async with message.process():
                body = message.body.decode()
                logger.info("[Payments] Received raw message: %s", body)
                try:
                    data = json.loads(body)
                    event = PaymentRequestEvent(**data)
                except Exception as e:
                    logger.error("[Payments] Invalid message format: %s", e)
                    continue

                logger.info("[Payments] Processing payment for order %s, user %s, amount %s",
                            event.order_id, event.user_id, event.amount)

                async for session in get_session():
                    try:
                        await process_payment_event(event, session)
                        logger.info("[Payments] process_payment_event committed for order %s", event.order_id)
                    except Exception as e:
                        logger.error("[Payments] process_payment_event failed: %s", e)

async def outbox_publisher():
    INTERVAL = settings.OUTBOX_POLL_INTERVAL

    while True:
        async for session in get_session():
            stmt = select(PaymentsOutbox).where(PaymentsOutbox.published_at.is_(None))
            result = await session.execute(stmt)
            events = result.scalars().all()
            logger.info("[Payments] Found %d pending outbox events", len(events))

            if events:
                channel = await get_channel()
                exchange = await channel.declare_exchange(
                    PAYMENT_EXCHANGE, ExchangeType.DIRECT, durable=True
                )

                for ev in events:
                    payload = ev.payload
                    logger.info("[Payments] Publishing to '%s': %s", QUEUE_PAYMENT_RESULTS, payload)
                    message = Message(body=json.dumps(payload).encode())
                    await exchange.publish(message, routing_key=QUEUE_PAYMENT_RESULTS)
                    ev.published_at = func.now()
                    session.add(ev)

                await session.commit()
                logger.info("[Payments] Outbox publish commit complete")

        await asyncio.sleep(INTERVAL)
