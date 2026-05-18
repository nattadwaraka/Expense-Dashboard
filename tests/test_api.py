"""HTTP API tests for Expense Dashboard."""

import pytest


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_root_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert b"Expense" in r.content


# --- Users ---


def test_user_crud_flow(client):
    r = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    assert r.status_code == 200
    uid = r.json()["id"]

    r = client.get("/users")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get(f"/users/{uid}")
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"

    r = client.put(f"/users/{uid}", json={"name": "Alice B"})
    assert r.status_code == 200
    assert r.json()["name"] == "Alice B"

    r = client.delete(f"/users/{uid}")
    assert r.status_code == 200
    r = client.get(f"/users/{uid}")
    assert r.status_code == 404


def test_create_user_duplicate_email(client):
    client.post("/users", json={"name": "A", "email": "dup@example.com"})
    r = client.post("/users", json={"name": "B", "email": "dup@example.com"})
    assert r.status_code == 400
    assert "already" in r.json()["detail"].lower()


def test_create_user_invalid_email(client):
    r = client.post("/users", json={"name": "A", "email": "not-an-email"})
    assert r.status_code == 422


def test_update_user_email_conflict(client):
    a = client.post("/users", json={"name": "A", "email": "a@example.com"}).json()["id"]
    b = client.post("/users", json={"name": "B", "email": "b@example.com"}).json()["id"]
    r = client.put(f"/users/{b}", json={"email": "a@example.com"})
    assert r.status_code == 400


def test_get_user_not_found(client):
    assert client.get("/users/99999").status_code == 404


# --- Categories ---


def test_category_crud_and_delete_blocked_when_in_use(client):
    cid = client.post("/categories", json={"name": "Food"}).json()["id"]
    uid = client.post("/users", json={"name": "U", "email": "u@example.com"}).json()[
        "id"
    ]
    client.post(
        "/expenses",
        json={
            "user_id": uid,
            "category_id": cid,
            "amount": 10,
            "expense_date": "2026-05-01",
            "name": "Lunch",
        },
    )

    r = client.delete(f"/categories/{cid}")
    assert r.status_code == 400
    assert "in use" in r.json()["detail"].lower()

    r = client.put(f"/categories/{cid}", json={"name": "Meals"})
    assert r.status_code == 200
    assert r.json()["name"] == "Meals"


def test_create_category_duplicate_name(client):
    client.post("/categories", json={"name": "X"})
    r = client.post("/categories", json={"name": "X"})
    assert r.status_code == 400


def test_delete_category_success_when_unused(client):
    cid = client.post("/categories", json={"name": "Z"}).json()["id"]
    r = client.delete(f"/categories/{cid}")
    assert r.status_code == 200


# --- Expenses ---


def test_expense_requires_valid_user_and_category(client):
    cid = client.post("/categories", json={"name": "C"}).json()["id"]
    uid = client.post("/users", json={"name": "U", "email": "u2@example.com"}).json()[
        "id"
    ]

    r = client.post(
        "/expenses",
        json={
            "user_id": 99999,
            "category_id": cid,
            "amount": 1,
            "expense_date": "2026-01-01",
            "name": "x",
        },
    )
    assert r.status_code == 404

    r = client.post(
        "/expenses",
        json={
            "user_id": uid,
            "category_id": 99999,
            "amount": 1,
            "expense_date": "2026-01-01",
            "name": "x",
        },
    )
    assert r.status_code == 404


def test_expense_amount_must_be_positive(client):
    cid = client.post("/categories", json={"name": "C2"}).json()["id"]
    uid = client.post("/users", json={"name": "U", "email": "u3@example.com"}).json()[
        "id"
    ]
    r = client.post(
        "/expenses",
        json={
            "user_id": uid,
            "category_id": cid,
            "amount": 0,
            "expense_date": "2026-01-01",
            "name": "x",
        },
    )
    assert r.status_code == 400


def test_list_expenses_requires_existing_user(client):
    assert client.get("/expenses?user_id=99999").status_code == 404


def test_expense_update_and_delete(client):
    cid = client.post("/categories", json={"name": "Cat"}).json()["id"]
    uid = client.post("/users", json={"name": "U", "email": "u4@example.com"}).json()[
        "id"
    ]
    eid = client.post(
        "/expenses",
        json={
            "user_id": uid,
            "category_id": cid,
            "amount": 5,
            "expense_date": "2026-03-15",
            "name": "Coffee",
        },
    ).json()["id"]

    r = client.get(f"/expenses/{eid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Coffee"

    r = client.put(f"/expenses/{eid}", json={"amount": 7.5})
    assert r.status_code == 200
    assert r.json()["amount"] == 7.5

    r = client.get("/expenses", params={"user_id": uid})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["category"] == "Cat"
    assert rows[0]["user_id"] == uid

    u2 = client.post("/users", json={"name": "Other", "email": "other@example.com"}).json()["id"]
    assert client.put(f"/expenses/{eid}", json={"user_id": u2}).status_code == 200
    assert client.get(f"/expenses/{eid}").json()["user_id"] == u2

    assert client.delete(f"/expenses/{eid}").status_code == 200
    assert client.get(f"/expenses/{eid}").status_code == 404


def test_update_expense_invalid_amount(client):
    cid = client.post("/categories", json={"name": "C3"}).json()["id"]
    uid = client.post("/users", json={"name": "U", "email": "u5@example.com"}).json()[
        "id"
    ]
    eid = client.post(
        "/expenses",
        json={
            "user_id": uid,
            "category_id": cid,
            "amount": 2,
            "expense_date": "2026-01-02",
            "name": "x",
        },
    ).json()["id"]
    r = client.put(f"/expenses/{eid}", json={"amount": -1})
    assert r.status_code == 400


# --- Monthly summary ---


def test_monthly_summary_totals(client):
    cid = client.post("/categories", json={"name": "A"}).json()["id"]
    cid2 = client.post("/categories", json={"name": "B"}).json()["id"]
    uid = client.post("/users", json={"name": "U", "email": "u6@example.com"}).json()[
        "id"
    ]
    client.post(
        "/expenses",
        json={
            "user_id": uid,
            "category_id": cid,
            "amount": 100,
            "expense_date": "2026-06-10",
            "name": "a",
        },
    )
    client.post(
        "/expenses",
        json={
            "user_id": uid,
            "category_id": cid2,
            "amount": 50,
            "expense_date": "2026-06-20",
            "name": "b",
        },
    )

    r = client.get(
        "/expenses/summary/monthly",
        params={"user_id": uid, "year": 2026, "month": 6},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_amount"] == 150
    cats = {row["category"]: row["total"] for row in data["category_summary"]}
    assert cats["A"] == 100
    assert cats["B"] == 50


def test_monthly_summary_invalid_month(client):
    uid = client.post("/users", json={"name": "U", "email": "u7@example.com"}).json()[
        "id"
    ]
    r = client.get(
        "/expenses/summary/monthly",
        params={"user_id": uid, "year": 2026, "month": 13},
    )
    assert r.status_code == 400


def test_monthly_summary_user_not_found(client):
    r = client.get(
        "/expenses/summary/monthly",
        params={"user_id": 99999, "year": 2026, "month": 1},
    )
    assert r.status_code == 404


def test_monthly_summary_all_users(client):
    cid = client.post("/categories", json={"name": "CatAll"}).json()["id"]
    u1 = client.post("/users", json={"name": "P1", "email": "p1@example.com"}).json()["id"]
    u2 = client.post("/users", json={"name": "P2", "email": "p2@example.com"}).json()["id"]
    client.post(
        "/expenses",
        json={
            "user_id": u1,
            "category_id": cid,
            "amount": 40,
            "expense_date": "2026-07-01",
            "name": "a",
        },
    )
    client.post(
        "/expenses",
        json={
            "user_id": u2,
            "category_id": cid,
            "amount": 60,
            "expense_date": "2026-07-15",
            "name": "b",
        },
    )
    r = client.get("/expenses/summary/monthly", params={"year": 2026, "month": 7})
    assert r.status_code == 200
    assert r.json()["total_amount"] == 100
    assert r.json()["user_id"] is None


def test_reports_yearly_and_timeseries(client):
    cid = client.post("/categories", json={"name": "C"}).json()["id"]
    uid = client.post("/users", json={"name": "U", "email": "ry@example.com"}).json()["id"]
    client.post(
        "/expenses",
        json={
            "user_id": uid,
            "category_id": cid,
            "amount": 10,
            "expense_date": "2025-06-01",
            "name": "old",
        },
    )
    client.post(
        "/expenses",
        json={
            "user_id": uid,
            "category_id": cid,
            "amount": 30,
            "expense_date": "2026-03-01",
            "name": "new",
        },
    )
    r = client.get("/reports/summary/year", params={"year": 2026, "user_id": uid})
    assert r.status_code == 200
    d = r.json()
    assert d["total_amount"] == 30
    assert len(d["months"]) == 12
    assert d["months"][2]["total"] == 30  # March

    r2 = client.get(
        "/reports/timeseries/years",
        params={"from_year": 2025, "to_year": 2026, "user_id": uid},
    )
    assert r2.status_code == 200
    pts = {p["year"]: p["total"] for p in r2.json()["points"]}
    assert pts[2025] == 10
    assert pts[2026] == 30


def test_reports_by_user_month_and_year(client):
    cid = client.post("/categories", json={"name": "X"}).json()["id"]
    u1 = client.post("/users", json={"name": "A", "email": "a8@example.com"}).json()["id"]
    u2 = client.post("/users", json={"name": "B", "email": "b8@example.com"}).json()["id"]
    client.post(
        "/expenses",
        json={
            "user_id": u1,
            "category_id": cid,
            "amount": 5,
            "expense_date": "2026-04-10",
            "name": "e",
        },
    )
    client.post(
        "/expenses",
        json={
            "user_id": u2,
            "category_id": cid,
            "amount": 15,
            "expense_date": "2026-04-20",
            "name": "e2",
        },
    )
    r = client.get("/reports/by-user", params={"year": 2026, "month": 4})
    assert r.status_code == 200
    d = r.json()
    assert d["grand_total"] == 20
    by_id = {x["user_id"]: x["total"] for x in d["users"]}
    assert by_id[u1] == 5
    assert by_id[u2] == 15

    r2 = client.get("/reports/by-user", params={"year": 2026})
    assert r2.json()["grand_total"] == 20


def test_delete_user_cascades_expenses(client):
    cid = client.post("/categories", json={"name": "Keep"}).json()["id"]
    uid = client.post("/users", json={"name": "Gone", "email": "gone@example.com"}).json()[
        "id"
    ]
    client.post(
        "/expenses",
        json={
            "user_id": uid,
            "category_id": cid,
            "amount": 1,
            "expense_date": "2026-01-01",
            "name": "e",
        },
    )
    assert client.delete(f"/users/{uid}").status_code == 200
    assert client.get("/expenses", params={"user_id": uid}).status_code == 404
