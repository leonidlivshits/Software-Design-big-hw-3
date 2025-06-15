from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# class OrderCreateRequest(BaseModel):
#     amount: float = Field(..., gt=0)
#     description: str | None = None

class OrderCreateRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Сумма заказа (положительное число)")
    description: Optional[str] = Field(None, description="Описание заказа")

class OrderCreate(BaseModel):
    user_id: UUID
    amount: float = Field(..., gt=0)
    description: Optional[str]

class OrderRead(BaseModel):
    id: UUID
    user_id: UUID
    amount: float
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class PaymentRequestEvent(BaseModel):
    order_id: UUID
    user_id: UUID
    amount: float
