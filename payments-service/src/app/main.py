import asyncio
import logging
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from decimal import Decimal
from app import crud, schemas, workers
from app.db import engine, Base, get_session
from app.messaging import init_rabbit, close_rabbit
import uvicorn

logger = logging.getLogger(__name__)
app = FastAPI(title="Payments Service")

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await init_rabbit()

    app.state.inbox_task  = asyncio.create_task(workers.inbox_consumer())
    app.state.outbox_task = asyncio.create_task(workers.outbox_publisher())

@app.on_event("shutdown")
async def shutdown_event():
    app.state.inbox_task.cancel()
    app.state.outbox_task.cancel()
    await close_rabbit()

@app.post("/accounts/{user_id}", response_model=schemas.AccountRead)
async def create_account(
    user_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        return await crud.create_account(str(user_id), session)
    except crud.AccountExistsError:
        raise HTTPException(status_code=400, detail="Account already exists")

@app.post("/accounts/{user_id}/deposit", response_model=schemas.AccountRead)
async def deposit(
    user_id: UUID,
    deposit_in: schemas.DepositRequest,
    session: AsyncSession = Depends(get_session)
):
    acc = await crud.deposit(str(user_id), deposit_in.amount, session)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc

@app.get("/accounts/{user_id}", response_model=schemas.AccountRead)
async def get_account(
    user_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    acc = await crud.get_account(str(user_id), session)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc


@app.post("/accounts/{user_id}/hold", status_code=200)
async def api_hold(user_id: UUID, req: schemas.HoldRequest, session: AsyncSession = Depends(get_session)):
    try:
        await crud.hold_amount(req.order_id, user_id, Decimal(str(req.amount)), session)
    except crud.InsufficientFunds:
        raise HTTPException(400, "Insufficient funds")
    return {"status":"held"}

@app.post("/accounts/{user_id}/release", status_code=200)
async def api_release(user_id: UUID, req: schemas.ReleaseRequest, session: AsyncSession = Depends(get_session)):
    try:
        await crud.release_hold(req.order_id, session)
    except crud.NoResultFound:
        raise HTTPException(404, "Hold not found")
    return {"status":"released"}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
