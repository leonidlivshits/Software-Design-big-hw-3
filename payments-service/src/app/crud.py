from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import UUID, select, func,  update, delete
from sqlalchemy.exc import IntegrityError, NoResultFound
from fastapi.encoders import jsonable_encoder

from app.models import Account, PaymentsInbox, PaymentsOutbox, Account, Hold
from app.schemas import PaymentRequestEvent

class AccountExistsError(Exception):
    pass

class InsufficientFunds(Exception):
    pass

async def create_account(
    user_id: str,
    session: AsyncSession
) -> Account:
    account = Account(
        user_id=user_id,
        balance=Decimal("0")
    )
    session.add(account)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AccountExistsError()
    await session.refresh(account)
    return account

async def get_account(
    user_id: str,
    session: AsyncSession
) -> Account | None:
    return await session.get(Account, user_id)

async def deposit(
    user_id: str,
    amount: float,
    session: AsyncSession
) -> Account | None:
    stmt = select(Account).where(Account.user_id == user_id).with_for_update()
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        return None

    account.balance += Decimal(str(amount))
    account.updated_at = func.now()
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account

async def process_payment_event(
    event: PaymentRequestEvent,
    session: AsyncSession
) -> None:
    raw = jsonable_encoder(event)

    inbox_rec = PaymentsInbox(
        message_id=raw["order_id"], # строка
        event_type="payment_requested",
        payload=raw
    )
    session.add(inbox_rec)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return

    # Проверяем и блокируем счёт
    account = await session.get(Account, raw["user_id"], with_for_update=True)
    if not account:
        out_payload = {
            "order_id": raw["order_id"],
            "user_id": raw["user_id"],
            "amount": raw["amount"],
            "result": "failed",
            "reason": "no_account"
        }
        event_type = "payment_failed"
    else:
        if account.balance < Decimal(str(raw["amount"])):
            out_payload = {
                "order_id": raw["order_id"],
                "user_id": raw["user_id"],
                "amount": raw["amount"],
                "result": "failed",
                "reason": "insufficient_funds"
            }
            event_type = "payment_failed"
        else:
            account.balance -= Decimal(str(raw["amount"]))
            account.updated_at = func.now()
            session.add(account)

            out_payload = {
                "order_id": raw["order_id"],
                "user_id": raw["user_id"],
                "amount": raw["amount"],
                "result": "success"
            }
            event_type = "payment_succeeded"

    outbox_rec = PaymentsOutbox(
        aggregate_id=raw["order_id"],
        event_type=event_type,
        payload=out_payload
    )
    session.add(outbox_rec)

    await session.commit()

async def hold_amount(order_id: UUID, user_id: UUID, amount: Decimal, session: AsyncSession):
    stmt = select(Account).where(Account.user_id==user_id).with_for_update()
    account = (await session.execute(stmt)).scalar_one_or_none()
    if not account or account.balance < amount:
        raise InsufficientFunds()
    account.balance -= amount
    session.add(account)
    session.add(Hold(order_id=order_id, user_id=user_id, amount=amount))
    await session.commit()

async def release_hold(order_id: UUID, session: AsyncSession):
    stmt = select(Hold).where(Hold.order_id==order_id, Hold.released_at.is_(None), Hold.captured_at.is_(None)).with_for_update()
    hold = (await session.execute(stmt)).scalar_one_or_none()
    if not hold:
        raise NoResultFound()

    stmt_acc = select(Account).where(Account.user_id==hold.user_id).with_for_update()
    account = (await session.execute(stmt_acc)).scalar_one()
    account.balance += hold.amount
    hold.released_at = func.now()
    session.add_all([account, hold])
    await session.commit()