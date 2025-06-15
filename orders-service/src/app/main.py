import asyncio
import logging
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app import crud, schemas, workers
from app.db import engine, Base, get_session
from app.messaging import init_rabbit, close_rabbit
import uvicorn

logger = logging.getLogger(__name__)
app = FastAPI(title="Orders Service")

@app.on_event("startup")
async def startup_event():
    #Миграции
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Rabbit (кролика накормили кобальтом)
    await init_rabbit()

    # Воркеры
    app.state.outbox_task = asyncio.create_task(workers.outbox_publisher())
    app.state.result_consumer_task = asyncio.create_task(workers.result_consumer())

@app.on_event("shutdown")
async def shutdown_event():
    app.state.outbox_task.cancel()
    app.state.result_consumer_task.cancel()
    await close_rabbit()


@app.post("/orders", response_model=schemas.OrderRead)
async def create_order(
    order_in: schemas.OrderCreateRequest,
    user_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """
    Создаёт новый заказ. Ожидает JSON бади { "amount": <float>, "description": "<str>" }.
    
    Пример:
    POST /orders?user_id=123e4567-e89b-12d3-a456-426614174000
    Body: {"amount": 100.50, "description": "Пример заказа"}
    """
    try:
        db_order = schemas.OrderCreate(
            user_id=str(user_id),
            amount=order_in.amount,
            description=order_in.description
        )
        
        new_order = await crud.create_order(db_order, session)
        return new_order
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

# @app.post("/orders/{user_id}", response_model=schemas.OrderRead)
# async def create_order(
#     user_id: UUID,
#     order_in: schemas.OrderCreate,
#     session: AsyncSession = Depends(get_session)
# ):
#     """
#     Создаёт новый заказ и публикует событие на проверку и списание средств.
#     Процесс оплаты полностью асинхронный через RabbitMQ.
#     """
#     try:
#         new_order = await crud.create_order(user_id, order_in, session)
#         return new_order
#     except Exception as e:
#         logger.error(f"Error creating order: {e}")
#         raise HTTPException(status_code=422, detail=str(e))

@app.get("/orders", response_model=list[schemas.OrderRead])
async def list_orders(
    user_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    return await crud.get_orders_by_user(user_id, session)

@app.get("/orders/{order_id}", response_model=schemas.OrderRead)
async def get_order(
    order_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    order = await crud.get_order(order_id, user_id, session)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
