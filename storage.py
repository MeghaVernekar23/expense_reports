"""Data access layer — SQLAlchemy for persistence, Pydantic for validated I/O.

No raw SQL: all queries go through the ORM session; all data crossing the
boundary into/out of this module is a Pydantic model. Budgets live in EUR;
expenses may be logged in EUR or INR and are converted to EUR (via fx.py,
using that day's rate) before being stored, so all spend/remaining math
stays in one currency.
"""
from contextlib import contextmanager

from sqlalchemy import func, select

import fx
from models import (
    Category,
    CategoryIn,
    CategoryOut,
    Expense,
    ExpenseIn,
    ExpenseOut,
    SessionLocal,
)
from models import init_db as _init_db


def init_db():
    _init_db()


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


def _to_expense_out(e: Expense) -> ExpenseOut:
    return ExpenseOut.model_validate(
        {
            "id": e.id,
            "category_id": e.category_id,
            "amount": e.amount,
            "currency": e.currency,
            "amount_eur": e.amount_eur,
            "fx_rate": e.fx_rate,
            "note": e.note,
            "spent_on": e.spent_on,
            "bill_path": e.bill_path,
            "category_name": e.category.name,
        }
    )


# ---------- Categories ----------

def add_category(
    name: str, budget: float, start: str | None, end: str | None, is_active: bool = True
) -> CategoryOut:
    data = CategoryIn(name=name.strip(), budget=budget, period_start=start, period_end=end, is_active=is_active)
    with get_session() as session:
        category = Category(**data.model_dump())
        session.add(category)
        session.flush()
        return CategoryOut.model_validate(category)


def update_category(
    cat_id: int, name: str, budget: float, start: str | None, end: str | None, is_active: bool | None = None
) -> CategoryOut | None:
    with get_session() as session:
        category = session.get(Category, cat_id)
        if category is None:
            return None
        data = CategoryIn(
            name=name.strip(),
            budget=budget,
            period_start=start,
            period_end=end,
            is_active=category.is_active if is_active is None else is_active,
        )
        for field, value in data.model_dump().items():
            setattr(category, field, value)
        session.flush()
        return CategoryOut.model_validate(category)


def set_category_active(cat_id: int, is_active: bool) -> CategoryOut | None:
    with get_session() as session:
        category = session.get(Category, cat_id)
        if category is None:
            return None
        category.is_active = is_active
        session.flush()
        return CategoryOut.model_validate(category)


def delete_category(cat_id: int) -> None:
    with get_session() as session:
        category = session.get(Category, cat_id)
        if category is not None:
            session.delete(category)


def get_categories() -> list[CategoryOut]:
    with get_session() as session:
        categories = session.scalars(select(Category).order_by(Category.period_start, Category.name)).all()
        return [CategoryOut.model_validate(c) for c in categories]


def get_category(cat_id: int) -> CategoryOut | None:
    with get_session() as session:
        category = session.get(Category, cat_id)
        return CategoryOut.model_validate(category) if category else None


# ---------- Expenses ----------

def add_expense(
    category_id: int,
    amount: float,
    note: str,
    spent_on: str,
    bill_path: str | None = None,
    currency: str = "EUR",
) -> ExpenseOut:
    amount_eur, fx_rate = fx.convert_to_eur(amount, currency, spent_on)
    data = ExpenseIn(
        category_id=category_id,
        amount=amount,
        currency=currency,
        amount_eur=amount_eur,
        fx_rate=fx_rate,
        note=note,
        spent_on=spent_on,
        bill_path=bill_path,
    )
    with get_session() as session:
        expense = Expense(**data.model_dump())
        session.add(expense)
        session.flush()
        session.refresh(expense, attribute_names=["category"])
        return _to_expense_out(expense)


def get_expense(expense_id: int) -> ExpenseOut | None:
    with get_session() as session:
        expense = session.get(Expense, expense_id)
        return _to_expense_out(expense) if expense else None


def delete_expense(expense_id: int) -> None:
    with get_session() as session:
        expense = session.get(Expense, expense_id)
        if expense is not None:
            session.delete(expense)


def get_expenses(category_id: int | None = None) -> list[ExpenseOut]:
    with get_session() as session:
        stmt = select(Expense).order_by(Expense.spent_on.desc(), Expense.id.desc())
        if category_id is not None:
            stmt = stmt.where(Expense.category_id == category_id)
        expenses = session.scalars(stmt).all()
        return [_to_expense_out(e) for e in expenses]


def get_total_spent(category_id: int) -> float:
    """Total spent for a category, in EUR (the base currency)."""
    with get_session() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(Expense.amount_eur), 0.0)).where(Expense.category_id == category_id)
        )
        return float(total or 0)
