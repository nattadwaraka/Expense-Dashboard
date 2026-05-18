import os
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import extract, func, text
from sqlalchemy.orm import Session

import models
import schemas
from database import Base, SessionLocal, engine, ensure_columns

Base.metadata.create_all(bind=engine)
ensure_columns()

with engine.begin() as conn:
    conn.execute(
        text("UPDATE expenses SET description = '' WHERE description IS NULL")
    )
    conn.execute(text("UPDATE users SET phone = '' WHERE phone IS NULL"))
    conn.execute(text("UPDATE categories SET description = '' WHERE description IS NULL"))
    conn.execute(text("UPDATE expenses SET notes = '' WHERE notes IS NULL"))
    conn.execute(text("UPDATE expenses SET payment_method = '' WHERE payment_method IS NULL"))

app = FastAPI(title="Expense Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_index():
    base = os.path.dirname(os.path.abspath(__file__))
    return FileResponse(os.path.join(base, "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


# ==================================================
# USERS
# ==================================================


@app.post("/users", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    u = models.User(**user.model_dump())
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@app.get("/users", response_model=list[schemas.User])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@app.get("/users/{user_id}", response_model=schemas.User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(models.User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u


@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db)):
    u = db.get(models.User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data:
        clash = (
            db.query(models.User)
            .filter(models.User.email == data["email"], models.User.id != user_id)
            .first()
        )
        if clash:
            raise HTTPException(status_code=400, detail="Email already in use")
    for k, v in data.items():
        setattr(u, k, v)
    db.commit()
    db.refresh(u)
    return u


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(models.User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(u)
    db.commit()
    return {"message": "User deleted"}


# ==================================================
# CATEGORIES
# ==================================================


@app.post("/categories", response_model=schemas.Category)
def create_category(cat: schemas.CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Category).filter(models.Category.name == cat.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    c = models.Category(**cat.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@app.get("/categories", response_model=list[schemas.Category])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()


@app.get("/categories/{category_id}", response_model=schemas.Category)
def get_category(category_id: int, db: Session = Depends(get_db)):
    c = db.get(models.Category, category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")
    return c


@app.put("/categories/{category_id}", response_model=schemas.Category)
def update_category(
    category_id: int, payload: schemas.CategoryUpdate, db: Session = Depends(get_db)
):
    c = db.get(models.Category, category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        clash = (
            db.query(models.Category)
            .filter(
                models.Category.name == data["name"], models.Category.id != category_id
            )
            .first()
        )
        if clash:
            raise HTTPException(status_code=400, detail="Category name already in use")
    for k, v in data.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@app.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    c = db.get(models.Category, category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")
    in_use = (
        db.query(models.Expense)
        .filter(models.Expense.category_id == category_id)
        .first()
    )
    if in_use:
        raise HTTPException(
            status_code=400, detail="Category is in use and cannot be deleted"
        )
    db.delete(c)
    db.commit()
    return {"message": "Category deleted"}


# ==================================================
# EXPENSES
# ==================================================


@app.post("/expenses", response_model=schemas.Expense)
def add_expense(exp: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    if exp.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    user = db.get(models.User, exp.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    category = db.get(models.Category, exp.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    e = models.Expense(**exp.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@app.get("/expenses/summary/monthly")
def monthly_summary(
    year: int,
    month: int,
    user_id: int | None = Query(default=None, description="Omit for all users"),
    db: Session = Depends(get_db),
):
    """Totals for one calendar month, optionally scoped to a single user."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    if not (1900 <= year <= 2100):
        raise HTTPException(status_code=400, detail="Year out of supported range")
    if user_id is not None and not db.get(models.User, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    exp_filters = [
        models.Expense.expense_date >= start,
        models.Expense.expense_date < end,
    ]
    if user_id is not None:
        exp_filters.append(models.Expense.user_id == user_id)

    total = (
        db.query(func.coalesce(func.sum(models.Expense.amount), 0))
        .filter(*exp_filters)
        .scalar()
    )

    cat_q = (
        db.query(models.Category.name, func.sum(models.Expense.amount))
        .join(models.Expense)
        .filter(*exp_filters)
        .group_by(models.Category.name)
    )
    categories = cat_q.all()

    return {
        "year": year,
        "month": month,
        "user_id": user_id,
        "total_amount": float(total or 0),
        "category_summary": [{"category": c, "total": float(a)} for c, a in categories],
    }


# ==================================================
# REPORTS (monthly / yearly / by user — for dashboards & charts)
# ==================================================


def _year_range_dates(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year + 1, 1, 1)


@app.get("/reports/summary/year")
def report_yearly_summary(
    year: int,
    user_id: int | None = Query(default=None, description="Omit for all users"),
    db: Session = Depends(get_db),
):
    """Full-year total, category breakdown, and per-calendar-month totals."""
    if not (1900 <= year <= 2100):
        raise HTTPException(status_code=400, detail="Year out of supported range")
    if user_id is not None and not db.get(models.User, user_id):
        raise HTTPException(status_code=404, detail="User not found")

    start, end = _year_range_dates(year)
    exp_filters = [
        models.Expense.expense_date >= start,
        models.Expense.expense_date < end,
    ]
    if user_id is not None:
        exp_filters.append(models.Expense.user_id == user_id)

    total = (
        db.query(func.coalesce(func.sum(models.Expense.amount), 0))
        .filter(*exp_filters)
        .scalar()
    )

    categories = (
        db.query(models.Category.name, func.sum(models.Expense.amount))
        .join(models.Expense)
        .filter(*exp_filters)
        .group_by(models.Category.name)
        .all()
    )

    monthly_raw = (
        db.query(
            extract("month", models.Expense.expense_date).label("m"),
            func.sum(models.Expense.amount),
        )
        .filter(*exp_filters)
        .group_by(extract("month", models.Expense.expense_date))
        .all()
    )
    by_month = {int(m): float(s or 0) for m, s in monthly_raw}
    months = [{"month": m, "total": by_month.get(m, 0.0)} for m in range(1, 13)]

    return {
        "year": year,
        "user_id": user_id,
        "total_amount": float(total or 0),
        "category_summary": [{"category": c, "total": float(a)} for c, a in categories],
        "months": months,
    }


@app.get("/reports/timeseries/years")
def report_timeseries_years(
    from_year: int = Query(..., ge=1900, le=2100),
    to_year: int = Query(..., ge=1900, le=2100),
    user_id: int | None = Query(default=None, description="Omit for all users"),
    db: Session = Depends(get_db),
):
    """Total spend per calendar year (inclusive range), one row per year."""
    if from_year > to_year:
        raise HTTPException(status_code=400, detail="from_year must be <= to_year")
    if user_id is not None and not db.get(models.User, user_id):
        raise HTTPException(status_code=404, detail="User not found")

    points = []
    for y in range(from_year, to_year + 1):
        start, end = _year_range_dates(y)
        flt = [
            models.Expense.expense_date >= start,
            models.Expense.expense_date < end,
        ]
        if user_id is not None:
            flt.append(models.Expense.user_id == user_id)
        t = db.query(func.coalesce(func.sum(models.Expense.amount), 0)).filter(*flt).scalar()
        points.append({"year": y, "total": float(t or 0)})

    return {
        "from_year": from_year,
        "to_year": to_year,
        "user_id": user_id,
        "points": points,
    }


@app.get("/reports/by-user")
def report_by_user(
    year: int = Query(..., ge=1900, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Spend per profile for the given year, or a single month within that year."""
    if month is None:
        start, end = _year_range_dates(year)
    else:
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)

    rows = (
        db.query(
            models.User.id,
            models.User.name,
            func.coalesce(func.sum(models.Expense.amount), 0),
        )
        .outerjoin(
            models.Expense,
            (models.Expense.user_id == models.User.id)
            & (models.Expense.expense_date >= start)
            & (models.Expense.expense_date < end),
        )
        .group_by(models.User.id, models.User.name)
        .order_by(models.User.name)
        .all()
    )
    users_out = [
        {"user_id": uid, "name": name, "total": float(t or 0)} for uid, name, t in rows
    ]
    grand = sum(u["total"] for u in users_out)
    return {
        "year": year,
        "month": month,
        "users": users_out,
        "grand_total": grand,
    }


@app.get("/expenses", response_model=list[schemas.ExpenseListItem])
def get_expenses(user_id: int, db: Session = Depends(get_db)):
    if not db.get(models.User, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    rows = (
        db.query(
            models.Expense.id,
            models.Expense.user_id,
            models.Expense.name,
            models.Expense.amount,
            models.Expense.expense_date,
            models.Expense.notes,
            models.Expense.payment_method,
            models.Category.name.label("category"),
        )
        .join(models.Category)
        .filter(models.Expense.user_id == user_id)
        .order_by(models.Expense.expense_date.desc(), models.Expense.id.desc())
        .all()
    )
    return [
        schemas.ExpenseListItem(
            id=r.id,
            user_id=r.user_id,
            name=r.name or "",
            amount=r.amount,
            expense_date=r.expense_date,
            category=r.category,
            notes=r.notes or "",
            payment_method=r.payment_method or "",
        )
        for r in rows
    ]


@app.get("/expenses/{expense_id}", response_model=schemas.Expense)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    e = db.get(models.Expense, expense_id)
    if not e:
        raise HTTPException(status_code=404, detail="Expense not found")
    return e


@app.put("/expenses/{expense_id}", response_model=schemas.Expense)
def update_expense(
    expense_id: int, payload: schemas.ExpenseUpdate, db: Session = Depends(get_db)
):
    e = db.get(models.Expense, expense_id)
    if not e:
        raise HTTPException(status_code=404, detail="Expense not found")
    data = payload.model_dump(exclude_unset=True)
    if "amount" in data and data["amount"] is not None and data["amount"] <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    if "user_id" in data and data["user_id"] is not None:
        if not db.get(models.User, data["user_id"]):
            raise HTTPException(status_code=404, detail="User not found")
    if "category_id" in data and data["category_id"] is not None:
        if not db.get(models.Category, data["category_id"]):
            raise HTTPException(status_code=404, detail="Category not found")
    for k, v in data.items():
        setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return e


@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    e = db.get(models.Expense, expense_id)
    if not e:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(e)
    db.commit()
    return {"message": "Expense deleted"}
