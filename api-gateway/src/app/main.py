import logging
from fastapi import FastAPI, HTTPException, Query, Body, Response
import httpx
from uuid import UUID
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
app = FastAPI(title="API Gateway")

PAYMENTS_BASE = "http://payments-service:8000"
ORDERS_BASE   = "http://orders-service:8000"

# Для сваггера
class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма для пополнения (положительное число)")

class OrderCreateRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма заказа (положительное число)")
    description: str | None = Field(None, description="Описание заказа")


@app.post("/accounts/{user_id}")
async def proxy_create_account(user_id: UUID):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{PAYMENTS_BASE}/accounts/{user_id}")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

@app.post("/accounts/{user_id}/deposit")
async def proxy_deposit(user_id: UUID, deposit: DepositRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYMENTS_BASE}/accounts/{user_id}/deposit",
            json=deposit.dict()
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

@app.get("/accounts/{user_id}")
async def proxy_get_account(user_id: UUID):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{PAYMENTS_BASE}/accounts/{user_id}")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))


@app.post(
    "/orders",
    description="Создание заказа. user_id — query-параметр, тело: amount и description"
)
async def proxy_create_order(
    user_id: UUID = Query(..., description="ID пользователя, делающего заказ"),
    order: OrderCreateRequest = Body(...)
):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{ORDERS_BASE}/orders?user_id={user_id}",
            json=order.dict()
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

@app.get(
    "/orders",
    description="Получение списка заказов пользователя"
)
async def proxy_list_orders(user_id: UUID = Query(..., description="ID пользователя")):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{ORDERS_BASE}/orders?user_id={user_id}")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

@app.get(
    "/orders/{order_id}",
    description="Получение конкретного заказа"
)
async def proxy_get_order(
    order_id: UUID,
    user_id: UUID = Query(..., description="ID пользователя")
):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{ORDERS_BASE}/orders/{order_id}?user_id={user_id}"
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8000)
