import asyncio
import logging
import httpx
from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from app import crud, schemas, workers
from app.db import engine, Base, get_session
from app.messaging import init_rabbit, close_rabbit
import uvicorn

logger = logging.getLogger(__name__)
app = FastAPI(title="Orders Service")
PAYMENTS_BASE = "http://payments-service:8000"

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


@app.post("/orders", response_model=schemas.OrderRead)
async def create_order(
    order_in: schemas.OrderCreateRequest,
    user_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session)
):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYMENTS_BASE}/accounts/{user_id}/hold",
            json={"order_id": str(uuid_order := uuid4()), "amount": order_in.amount}
        )
    if resp.status_code == 400:
        raise HTTPException(400, "Insufficient funds")
    resp.raise_for_status()
    new_order = await crud.create_order(
        schemas.OrderCreate(order_id=uuid_order,
                             user_id=user_id,
                             amount=order_in.amount,
                             description=order_in.description),
        session
    )
    return new_order


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
