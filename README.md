# Expense Dashboard

A full-stack **expense tracker** proof of concept: **FastAPI** + **SQLAlchemy** + **SQLite** on the backend, and a single **HTML/CSS/JavaScript** dashboard (no build step). The API and UI are served from the same origin so you can open the app at `http://127.0.0.1:8000/` without CORS issues.

---

## Overview

- **Users (profiles)** — name, email, phone; full CRUD; optional “active profile” shortcut in the header.
- **Categories** — name and description; full CRUD; delete blocked while expenses reference a category.
- **Expenses** — title, amount, date, category, optional **notes** and **payment method**; assign to **any** profile (not only the active one); list filter per profile; full CRUD including moving an expense to another user.
- **Reports** — monthly category totals, yearly rollups, multi-year trends, and per-user comparisons; **Chart.js** (CDN) for charts. Scope: all users, active profile, or a single named profile.

---

## Features

| Area | Details |
|------|---------|
| **Users** | Create, read, update, delete; optional phone; select active profile for shortcuts. |
| **Categories** | Create, read, update, delete; optional description; cannot delete if in use. |
| **Expenses** | Create for any profile; edit/delete; validation on amount and date; notes & payment type. |
| **Reports & charts** | Month picker + category table; spend by month (year); spend by profile (all-users scope) or **by category** (single-user scope); totals by calendar year over a configurable range. |
| **UI** | Dark theme, responsive layout, loading indicator, toasts, empty states, skip link, `/docs` link. |

---

## Tech stack

| Layer | Stack |
|-------|--------|
| **Runtime** | Python **3.10+** recommended |
| **API** | FastAPI, Pydantic v2 (`EmailStr` requires `email-validator`) |
| **ORM / DB** | SQLAlchemy 2.x, SQLite (`expense_tracker.db` by default) |
| **Server** | Uvicorn (`uvicorn[standard]`) |
| **Tests** | pytest, httpx (FastAPI `TestClient`) |
| **Frontend** | HTML5, CSS3, vanilla JS; **Chart.js** loaded from jsDelivr CDN |

---

## Project layout

```
Expense-Dashboard/
├── main.py              # FastAPI app, routes, startup DB migration hooks
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic request/response models
├── database.py          # Engine, session, SQLite PRAGMAs, ensure_columns()
├── index.html           # Single-page dashboard (served at `/`)
├── expense_tracker.db   # Default SQLite file (optional to gitignore)
├── requirements.txt
├── pytest.ini
├── .gitignore
├── tests/
│   ├── conftest.py      # In-memory DB + reset per test
│   └── test_api.py      # API integration tests
└── README.md
```

---

## Setup

### 1. Virtual environment

```bash
python -m venv venv
```

Activate:

- **Windows:** `venv\Scripts\activate`
- **macOS / Linux:** `source venv/bin/activate`

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
uvicorn main:app --reload
```

| URL | Purpose |
|-----|---------|
| `http://127.0.0.1:8000/` | Dashboard (same origin as API) |
| `http://127.0.0.1:8000/docs` | OpenAPI (Swagger UI) |
| `http://127.0.0.1:8000/health` | Liveness JSON `{"status":"ok"}` |

**Important:** open the dashboard via the server URL above. Opening `index.html` as a `file://` page will usually break API calls (CORS / security).

### 4. Optional: custom database URL

Set **`EXPENSE_DB_URL`** before import (used by tests and optional local overrides), for example:

```bash
export EXPENSE_DB_URL="sqlite:////absolute/path/to/custom.db"
uvicorn main:app --reload
```

Tests set `EXPENSE_DB_URL` to an in-memory database in `tests/conftest.py`.

---

## Tests

```bash
pytest
```

Integration tests hit the real FastAPI app with an **isolated in-memory** SQLite database (`StaticPool` so SQLite `:memory:` works across threads).

---

## API reference

### Users

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/users` | Create user |
| `GET` | `/users` | List users |
| `GET` | `/users/{user_id}` | Get one user |
| `PUT` | `/users/{user_id}` | Update user |
| `DELETE` | `/users/{user_id}` | Delete user (cascades expenses) |

### Categories

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/categories` | Create category |
| `GET` | `/categories` | List categories |
| `GET` | `/categories/{category_id}` | Get one category |
| `PUT` | `/categories/{category_id}` | Update category |
| `DELETE` | `/categories/{category_id}` | Delete (400 if referenced by expenses) |

### Expenses

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/expenses` | Create expense |
| `GET` | `/expenses?user_id=` | List expenses for a user (includes `notes`, `payment_method`) |
| `GET` | `/expenses/{expense_id}` | Get one expense |
| `PUT` | `/expenses/{expense_id}` | Update (optional `user_id` to reassign owner) |
| `DELETE` | `/expenses/{expense_id}` | Delete expense |

### Summaries & reports

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/expenses/summary/monthly` | Query: `year`, `month`; optional `user_id` (omit = all users) |
| `GET` | `/reports/summary/year` | Query: `year`; optional `user_id` — totals, category breakdown, 12 monthly points |
| `GET` | `/reports/timeseries/years` | Query: `from_year`, `to_year`; optional `user_id` |
| `GET` | `/reports/by-user` | Query: `year`; optional `month` (1–12) — spend per profile |

---

## Data shapes (JSON)

**User**

```json
{
  "id": 1,
  "name": "User Name",
  "email": "user@example.com",
  "phone": ""
}
```

**Category**

```json
{
  "id": 1,
  "name": "Food",
  "description": ""
}
```

**Expense**

```json
{
  "id": 101,
  "user_id": 1,
  "category_id": 2,
  "name": "Lunch",
  "amount": 250,
  "expense_date": "2024-04-15",
  "notes": "",
  "payment_method": ""
}
```

---

## Rules & validation

- Expense **amount** must be greater than zero.
- Expense **date** is required; new expenses cannot be future-dated in the UI (editing may allow correcting legacy rows).
- **Duplicate** user emails and category names are rejected where applicable.
- **Categories** in use cannot be deleted.
- Destructive actions in the UI use **confirm** dialogs.

---

## Limitations (POC)

- No authentication or authorization.
- No role-based access control.
- Charts depend on a **CDN**; offline or strict CSP may block Chart.js.
- Not hardened for production (logging, rate limits, HTTPS termination, etc.).

---

## Future ideas

- JWT or session-based auth.
- Export CSV/PDF.
- Richer analytics (budgets, tags).
- Docker image and CI pipeline.
- Optional React/Vue frontend while keeping the same API.

---

## Contributing & Git

- Use the provided **`.gitignore`** for venvs, caches, and local env files.
- Uncomment ignoring **`expense_tracker.db`** in `.gitignore` if you do not want to commit a local database.

---

## License / author

Expense Dashboard — proof of concept built with **FastAPI** and **vanilla JavaScript** for learning and demos.
