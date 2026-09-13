"""SQLAlchemy ORM models and Pydantic schemas."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Float, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

DB_PATH = Path(__file__).parent / "expenses.db"
engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    # not unique: the same category name recurs once per billing period
    # (e.g. "Food" for 13 Sep - 13 Oct, then again for 13 Oct - 13 Nov)
    name: Mapped[str] = mapped_column(String, nullable=False)
    budget: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    period_start: Mapped[str | None] = mapped_column(String, nullable=True)
    period_end: Mapped[str | None] = mapped_column(String, nullable=True)
    # manual on/off switch — independent of the period dates. Only active
    # categories show on the dashboard / are selectable when logging spend.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="EUR")
    amount_eur: Mapped[float] = mapped_column(Float, nullable=False)
    fx_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # INR per 1 EUR, on spent_on date
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    spent_on: Mapped[str] = mapped_column(String, nullable=False)
    bill_path: Mapped[str | None] = mapped_column(String, nullable=True)

    category: Mapped["Category"] = relationship(back_populates="expenses")


def init_db():
    Base.metadata.create_all(engine)


# ---------------------------------------------------------------- Schemas ----

class CategoryIn(BaseModel):
    name: str = Field(min_length=1)
    budget: float = Field(ge=0)
    period_start: str | None = None
    period_end: str | None = None
    is_active: bool = True


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    budget: float
    period_start: str | None
    period_end: str | None
    is_active: bool

    @property
    def month_label(self) -> str:
        """Label for the custom billing period this category instance covers,
        e.g. '13 Sep - 13 Oct'. Falls back to 'No period' when dates are unset."""
        if not self.period_start:
            return "No period"
        try:
            from datetime import datetime

            start = datetime.strptime(self.period_start, "%Y-%m-%d")
        except ValueError:
            return "No period"
        if self.period_end:
            try:
                end = datetime.strptime(self.period_end, "%Y-%m-%d")
                return f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"
            except ValueError:
                pass
        return f"From {start.strftime('%d %b')}"


class ExpenseIn(BaseModel):
    category_id: int
    amount: float = Field(gt=0)
    currency: str = Field(default="EUR", pattern="^(EUR|INR)$")
    amount_eur: float = Field(gt=0)
    fx_rate: float | None = None
    note: str | None = None
    spent_on: str
    bill_path: str | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    amount: float
    currency: str
    amount_eur: float
    fx_rate: float | None
    note: str | None
    spent_on: str
    bill_path: str | None
    category_name: str
