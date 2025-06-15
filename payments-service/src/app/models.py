import uuid
from sqlalchemy import Column, DateTime, Numeric, String, DECIMAL, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from app.db import Base

class Account(Base):
    __tablename__ = "accounts"

    user_id = Column(PG_UUID(as_uuid=True), primary_key=True)
    balance = Column(DECIMAL(18, 2), nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class PaymentsInbox(Base):
    __tablename__ = "payments_inbox"

    message_id = Column(PG_UUID(as_uuid=True), primary_key=True)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)
    processed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class PaymentsOutbox(Base):
    __tablename__ = "payments_outbox"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_id = Column(PG_UUID(as_uuid=True), nullable=False)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)

class Hold(Base):
    __tablename__ = "holds"

    order_id   = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(PG_UUID(as_uuid=True), nullable=False)
    amount     = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    released_at= Column(DateTime(timezone=True), nullable=True)
    captured_at= Column(DateTime(timezone=True), nullable=True)
