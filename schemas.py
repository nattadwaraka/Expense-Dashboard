from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# =========================
# USERS
# =========================


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str = ""


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str = ""


# =========================
# CATEGORIES
# =========================


class CategoryCreate(BaseModel):
    name: str
    description: str = ""


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Category(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str = ""


# =========================
# EXPENSES
# =========================


class ExpenseCreate(BaseModel):
    user_id: int
    category_id: int
    amount: float
    expense_date: date
    name: str = ""
    notes: str = ""
    payment_method: str = ""


class ExpenseUpdate(BaseModel):
    user_id: Optional[int] = None
    category_id: Optional[int] = None
    amount: Optional[float] = None
    expense_date: Optional[date] = None
    name: Optional[str] = None
    notes: Optional[str] = None
    payment_method: Optional[str] = None


class Expense(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category_id: int
    name: str
    amount: float
    expense_date: date
    notes: str = ""
    payment_method: str = ""


class ExpenseListItem(BaseModel):
    id: int
    user_id: int
    name: str
    amount: float
    expense_date: date
    category: str
    notes: str = ""
    payment_method: str = ""
