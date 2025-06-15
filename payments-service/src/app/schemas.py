from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class AccountCreate(BaseModel):
    user_id: UUID

class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма для пополнения (положительное число)")


class AccountRead(BaseModel):
    user_id: UUID
    balance: float
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

class PaymentRequestEvent(BaseModel):
    order_id: UUID
    user_id: UUID
    amount: float

class PaymentResultEvent(BaseModel):
    order_id: UUID
    user_id: UUID
    amount: float
    result: str
    reason: Optional[str]
