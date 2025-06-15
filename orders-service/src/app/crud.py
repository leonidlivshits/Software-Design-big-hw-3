from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, func
from app.models import Order, OrdersOutbox
from app.schemas import OrderCreate
from uuid import UUID

async def create_order(
    order_in: OrderCreate,
    session: AsyncSession
) -> Order:
    """
    Создаёт новый заказ и вставляет событие в outbox.
    """
    # добавляем запись в таблицу orders
    order = Order(
        user_id=order_in.user_id,
        amount=order_in.amount,
        description=order_in.description,
        status="NEW"
    )
    session.add(order)
    await session.flush()  # чтобы получить order.id

    # добавляем запись в orders_outbox
    payload = {
        "order_id": str(order.id),
        "user_id": str(order.user_id),
        "amount": float(order.amount)
    }
    outbox_rec = OrdersOutbox(
        aggregate_id=order.id,
        event_type="payment_requested",
        payload=payload
    )
    session.add(outbox_rec)

    await session.commit()
    await session.refresh(order)
    return order

async def get_orders_by_user(
    user_id: UUID,
    session: AsyncSession
) -> List[Order]:
    """
    Возвращает список заказов для данного user_id.
    """
    result = await session.execute(select(Order).where(Order.user_id == user_id))
    return result.scalars().all()

async def get_order(
    order_id: UUID,
    user_id: UUID,
    session: AsyncSession
) -> Order | None:
    """
    Возвращает заказ по его ID и user_id или None, если не найден.
    """
    result = await session.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def update_order_status(
    order_id: UUID,
    new_status: str,
    session: AsyncSession
) -> None:
    """
    Обновляет статус заказа (используется фоновым воркером при получении результата оплаты).
    """
    await session.execute(
        update(Order)
        .where(Order.id == order_id)
        .values(status=new_status, updated_at=func.now())
    )
    await session.commit()