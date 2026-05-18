from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=False, default="")

    expenses = relationship(
        "Expense",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False, default="")

    expenses = relationship("Expense", back_populates="category")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    # SQLite schema uses legacy column name "description"
    name = Column("description", String, nullable=False, default="")
    amount = Column(Float, nullable=False)
    expense_date = Column(Date, nullable=False)
    notes = Column(String, nullable=False, default="")
    payment_method = Column(String, nullable=False, default="")

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )

    user = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")
