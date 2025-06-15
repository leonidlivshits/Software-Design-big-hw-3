import uuid
from sqlalchemy import Column, String, DECIMAL, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from app.db import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    amount = Column(DECIMAL(18, 2), nullable=False)
    description = Column(String, nullable=True)
    status = Column(String(20), nullable=False, default="NEW")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class OrdersOutbox(Base):
    __tablename__ = "orders_outbox"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_id = Column(PG_UUID(as_uuid=True), nullable=False)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)
