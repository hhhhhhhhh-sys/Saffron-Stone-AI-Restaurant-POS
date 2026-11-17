import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update

from backend import app as api


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_engine = create_engine(f"sqlite:///{tmp_path / 'restaurant-test.db'}")
    monkeypatch.setattr(api, "engine", test_engine)
    monkeypatch.setenv("RESTAURANT_ADMIN_PASSWORD", "test-admin-pass")
    monkeypatch.setenv("RESTAURANT_STAFF_PASSWORD", "test-staff-pass")
    monkeypatch.setenv("RESTAURANT_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("RESTAURANT_STAFF_USERNAME", "staff")
    try:
        with TestClient(api.app) as test_client:
            yield test_client
    finally:
        test_engine.dispose()


def sign_in(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_staff_can_place_order_and_server_calculates_change(client: TestClient):
    staff_headers = sign_in(client, "staff", "test-staff-pass")
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    menu = client.get("/api/menu", headers=staff_headers).json()
    roti = next(item for item in menu if item["name"] == "Tandoori Roti")
    paneer = next(item for item in menu if item["name"] == "Paneer Tikka")
    admin_menu = client.get("/api/menu", headers=admin_headers).json()
    roti_admin = next(item for item in admin_menu if item["id"] == roti["id"])
    paneer_admin = next(item for item in admin_menu if item["id"] == paneer["id"])
    for item, cost in ((roti_admin, 10), (paneer_admin, 80)):
        item["cost_price"] = cost
        updated = client.put(f"/api/menu/{item['id']}", headers=admin_headers, json=item)
        assert updated.status_code == 200

    response = client.post(
        "/api/orders",
        headers=staff_headers,
        json={
            "order_type": "Dine in",
            "table_name": "Table 04",
            "cash_received": 700,
            "items": [
                {"item_id": roti["id"], "quantity": 10},
                {"item_id": paneer["id"], "quantity": 1},
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["subtotal"] == 610
    assert response.json()["tax"] == 31
    assert response.json()["total"] == 641
    assert response.json()["change_due"] == 59
    assert "cost" not in response.json()["items"][0]

    assert client.get("/api/orders", headers=staff_headers).status_code == 403
    history = client.get("/api/orders", headers=admin_headers)
    assert history.status_code == 200
    assert history.json()[0]["id"] == response.json()["id"]
    assert sum(line["quantity"] for line in history.json()[0]["items"]) == 11

    daily = client.get(f"/api/reports/daily?report_date={date.today().isoformat()}", headers=admin_headers)
    assert daily.status_code == 200
    assert daily.json()["order_count"] == 1
    assert daily.json()["sales_revenue"] == 610
    assert daily.json()["cost_of_goods"] == 180
    assert daily.json()["gross_profit"] == 430
    assert daily.json()["profit_complete"] is True
    assert daily.json()["orders"][0]["staff_name"] == "Restaurant Staff"
    assert daily.json()["orders"][0]["items"][0]["cost_price"] is not None
    assert client.get(f"/api/reports/daily?report_date={date.today().isoformat()}", headers=staff_headers).status_code == 403


def test_staff_cannot_change_menu_but_admin_can(client: TestClient):
    staff_headers = sign_in(client, "staff", "test-staff-pass")
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    item = client.get("/api/menu", headers=staff_headers).json()[0]
    item["price"] += 10

    denied = client.put(f"/api/menu/{item['id']}", headers=staff_headers, json=item)
    updated = client.put(f"/api/menu/{item['id']}", headers=admin_headers, json=item)

    assert denied.status_code == 403
    assert updated.status_code == 200
    assert updated.json()["price"] == item["price"]
    assert client.get("/api/orders", headers=staff_headers).status_code == 403


def test_order_rejects_insufficient_cash_and_unauthenticated_menu(client: TestClient):
    headers = sign_in(client, "staff", "test-staff-pass")
    item = client.get("/api/menu", headers=headers).json()[0]

    response = client.post(
        "/api/orders",
        headers=headers,
        json={"order_type": "Takeaway", "cash_received": 1, "items": [{"item_id": item["id"], "quantity": 1}]},
    )

    assert response.status_code == 400
    assert client.get("/api/menu").status_code == 401


def test_admin_can_take_orders_and_dine_in_requires_a_table(client: TestClient):
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    item = client.get("/api/menu", headers=admin_headers).json()[0]

    missing_table = client.post(
        "/api/orders",
        headers=admin_headers,
        json={"order_type": "Dine in", "cash_received": 1000, "items": [{"item_id": item["id"], "quantity": 1}]},
    )
    admin_order = client.post(
        "/api/orders",
        headers=admin_headers,
        json={
            "order_type": "Dine in",
            "table_name": "Table 12",
            "cash_received": 1000,
            "items": [{"item_id": item["id"], "quantity": 1}],
        },
    )

    assert missing_table.status_code == 422
    assert admin_order.status_code == 201
    assert admin_order.json()["table_name"] == "Table 12"


def test_daily_report_marks_missing_item_costs_as_incomplete(client: TestClient):
    staff_headers = sign_in(client, "staff", "test-staff-pass")
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    item = client.get("/api/menu", headers=staff_headers).json()[0]

    order = client.post(
        "/api/orders",
        headers=staff_headers,
        json={
            "order_type": "Takeaway",
            "cash_received": item["price"] + 100,
            "items": [{"item_id": item["id"], "quantity": 1}],
        },
    )
    report = client.get(
        f"/api/reports/daily?report_date={date.today().isoformat()}",
        headers=admin_headers,
    )

    assert order.status_code == 201
    assert report.status_code == 200
    assert report.json()["profit_complete"] is False
    assert report.json()["gross_profit"] is None
    assert report.json()["uncosted_quantity"] == 1


def test_login_role_choice_must_match_account_role(client: TestClient):
    correct_role = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "test-admin-pass", "role": "admin"},
    )
    wrong_role = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "test-admin-pass", "role": "staff"},
    )

    assert correct_role.status_code == 200
    assert correct_role.json()["user"]["role"] == "admin"
    assert wrong_role.status_code == 401


def test_kitchen_staff_can_advance_checklist_reception_can_track_but_not_edit(client: TestClient):
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    reception_headers = sign_in(client, "staff", "test-staff-pass")
    created = client.post(
        "/api/admin/employees",
        headers=admin_headers,
        json={
            "username": "kitchen.worker",
            "display_name": "Kitchen Worker",
            "password": "kitchen-password",
            "employee_type": "kitchen",
        },
    )
    assert created.status_code == 201
    kitchen_headers = sign_in(client, "kitchen.worker", "kitchen-password")
    item = client.get("/api/menu", headers=reception_headers).json()[0]
    order = client.post(
        "/api/orders",
        headers=reception_headers,
        json={
            "order_type": "Takeaway",
            "cash_received": item["price"] + 100,
            "items": [{"item_id": item["id"], "quantity": 2}],
        },
    )
    assert order.status_code == 201
    ticket = next(
        ticket
        for ticket in client.get("/api/prep/orders", headers=kitchen_headers).json()
        if ticket["id"] == order.json()["id"]
    )
    checklist_item = ticket["items"][0]
    assert checklist_item["prep_status"] == "queued"
    assert client.get("/api/menu", headers=kitchen_headers).status_code == 403
    assert client.post(
        "/api/orders",
        headers=kitchen_headers,
        json={
            "order_type": "Takeaway",
            "cash_received": item["price"] + 100,
            "items": [{"item_id": item["id"], "quantity": 1}],
        },
    ).status_code == 403

    started = client.patch(
        f"/api/prep/items/{checklist_item['id']}",
        headers=kitchen_headers,
        json={"status": "preparing"},
    )
    assert started.status_code == 200
    receptionist_ticket = next(
        ticket
        for ticket in client.get("/api/prep/orders", headers=reception_headers).json()
        if ticket["id"] == order.json()["id"]
    )
    assert receptionist_ticket["items"][0]["prep_status"] == "preparing"
    assert client.patch(
        f"/api/prep/items/{checklist_item['id']}",
        headers=reception_headers,
        json={"status": "ready"},
    ).status_code == 403
    assert client.patch(
        f"/api/prep/items/{checklist_item['id']}",
        headers=admin_headers,
        json={"status": "ready"},
    ).status_code == 403
    admin_ticket = next(
        ticket
        for ticket in client.get("/api/prep/orders", headers=admin_headers).json()
        if ticket["id"] == order.json()["id"]
    )
    assert admin_ticket["items"][0]["prep_status"] == "preparing"
    assert client.patch(
        f"/api/prep/items/{checklist_item['id']}",
        headers=kitchen_headers,
        json={"status": "ready"},
    ).status_code == 200
    assert client.patch(
        f"/api/prep/items/{checklist_item['id']}",
        headers=kitchen_headers,
        json={"status": "preparing"},
    ).status_code == 409
    ready_ticket = next(
        ticket
        for ticket in client.get("/api/prep/orders", headers=kitchen_headers).json()
        if ticket["id"] == order.json()["id"]
    )
    assert ready_ticket["items"][0]["prep_status"] == "ready"
    delivered = client.patch(
        f"/api/prep/items/{checklist_item['id']}",
        headers=kitchen_headers,
        json={"status": "delivered"},
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"
    assert all(
        ticket["id"] != order.json()["id"]
        for ticket in client.get("/api/prep/orders", headers=kitchen_headers).json()
    )
    with api.engine.connect() as connection:
        assert connection.execute(
            api.select(api.order_items.c.prep_status).where(
                api.order_items.c.id == checklist_item["id"]
            )
        ).scalar_one() == "delivered"


def test_menu_seed_photos_match_dish_names_and_adds_more_items(client: TestClient):
    headers = sign_in(client, "admin", "test-admin-pass")
    menu = client.get("/api/menu", headers=headers)
    assert menu.status_code == 200
    items = {item["name"]: item for item in menu.json()}

    assert len(items) == 27
    assert items["Garlic Naan"]["image"].endswith("/Garlic_Naan.JPG")
    assert items["Tandoori Roti"]["image"].endswith("/Tandoori_Roti-MB54.jpg")
    assert items["Dal Makhani"]["image"].endswith("Dal_Makhani%29_%282239000538%29.jpg")
    assert items["Masala Chaas"]["image"].endswith("/Masala_chaas.JPG")
    assert items["Gulab Jamun"]["image"].endswith("/Gulab_Jamun_1.jpg")
    assert items["Chicken Biryani"]["image"].endswith("DSC_009.jpg")
    assert items["Samosa"]["image"].endswith("/Samosa_4.jpg")
    assert items["Mango Lassi"]["image"].endswith("/Mango_Lassi_.jpg")
    assert items["Rasmalai"]["image"].endswith("/Rasmalai_3.jpg")
    assert {
        name for name, item in items.items() if item["category"] == "Breakfast"
    } == {"Idli", "Bara", "Dosa", "Aloo Roti", "Sattu Roti", "Jalebi", "Upma"}
    assert items["Veg Thali"]["category"] == "Thalis"
    assert items["Non-Veg Thali"]["category"] == "Thalis"
    assert items["Idli"]["image"].endswith("/Idli_Sambar-Noida-UP-SP004.jpg")
    assert items["Bara"]["image"].endswith("/Dhai_bara.jpg")
    assert items["Dosa"]["image"].endswith("/Dosa_with_Chutney_and_Sambhar.jpg")
    assert items["Aloo Roti"]["image"].endswith("/Aloo_Paratha_2.jpg")
    assert items["Jalebi"]["image"].endswith("/Jalebi-an_Indian_sweetdish.jpg")
    assert items["Upma"]["image"].endswith("/Upma_South_India.JPG")
    assert items["Masala Chaas"]["image"].endswith("/Masala_chaas.JPG")
    assert items["Chicken Masala"]["image"].endswith("/Chicken_Tikka_Masala_KellySue.JPG")
    assert items["Chicken Tikka"]["image"].endswith("/Chicken-Tikka.jpg")
    assert items["Mutton Khassa"]["image"].endswith("/Indian_mutton_Curry.JPG")
    assert items["Tawa Roti"]["image"].endswith("/Tawa_Roti.JPG")
    assert items["Plain Naan"]["image"].endswith("/Plain_Naan.jpg")
    assert items["Butter Naan"]["image"].endswith("/Butter_Naan_2.jpg")

    with api.engine.begin() as connection:
        connection.execute(
            api.menu_items.update()
            .where(api.menu_items.c.id == items["Garlic Naan"]["id"])
            .values(image="photo-1608219992759-8d74ed8d76eb")
        )
        connection.execute(
            api.menu_items.update()
            .where(api.menu_items.c.id == items["Masala Chaas"]["id"])
            .values(image="https://upload.wikimedia.org/wikipedia/commons/8/8f/Masala_Buttermilk.JPG")
        )
        connection.execute(
            api.menu_items.update()
            .where(api.menu_items.c.id == items["Upma"]["id"])
            .values(image="photo-1546833999-b9f581a1996d")
        )
        connection.execute(
            api.menu_items.update()
            .where(api.menu_items.c.id == items["Butter Naan"]["id"])
            .values(image="https://upload.wikimedia.org/wikipedia/commons/8/8f/Butter_Naan_with_three_different_Indian_curry.jpg")
        )
    api.initialize_database()
    with api.engine.connect() as connection:
        migrated_images = {
            name: connection.execute(
                api.select(api.menu_items.c.image).where(
                    api.menu_items.c.id == items[name]["id"]
                )
            ).scalar_one()
            for name in ("Garlic Naan", "Masala Chaas", "Upma", "Butter Naan")
        }
    assert migrated_images["Garlic Naan"].endswith("/Garlic_Naan.JPG")
    assert migrated_images["Masala Chaas"].endswith("/Masala_chaas.JPG")
    assert migrated_images["Upma"].endswith("/Upma_South_India.JPG")
    assert migrated_images["Butter Naan"].endswith("/Butter_Naan_2.jpg")


def test_admin_forecast_includes_sales_history_festival_uplift_and_item_rankings(client: TestClient):
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    staff_headers = sign_in(client, "staff", "test-staff-pass")
    item = client.get("/api/menu", headers=admin_headers).json()[0]
    item["cost_price"] = 20
    assert client.put(f"/api/menu/{item['id']}", headers=admin_headers, json=item).status_code == 200
    order = client.post(
        "/api/orders",
        headers=staff_headers,
        json={
            "order_type": "Takeaway",
            "cash_received": item["price"] + 100,
            "items": [{"item_id": item["id"], "quantity": 2}],
        },
    )
    assert order.status_code == 201
    previous_month = (date.today().replace(day=1) - timedelta(days=1)).replace(day=1)
    with api.engine.begin() as connection:
        connection.execute(
            api.orders.update()
            .where(api.orders.c.id == order.json()["id"])
            .values(
                created_at=datetime.combine(previous_month, datetime.min.time()),
                note="[DEMO SAMPLE] forecast test record",
            )
        )

    forecast = client.get("/api/reports/forecast?month=2026-12", headers=admin_headers)

    assert forecast.status_code == 200
    assert forecast.json()["month"] == "2026-12"
    assert forecast.json()["festival_uplift_percent"] == 20
    assert forecast.json()["forecast_sales"] > 0
    assert forecast.json()["forecast_gross_profit"] is not None
    assert forecast.json()["best_sellers"][0]["name"] == item["name"]
    assert forecast.json()["history"][-1]["kind"] == "forecast"
    assert forecast.json()["previous_month"]["order_count"] == 1
    assert forecast.json()["previous_month"]["sales_revenue"] == order.json()["total"] - order.json()["tax"]
    assert forecast.json()["previous_month"]["demo_order_count"] == 1
    assert forecast.json()["demo_order_count"] == 1
    assert forecast.json()["previous_month"]["orders"][0]["items"][0]["name"] == item["name"]
    assert forecast.json()["previous_month"]["orders"][0]["note"].startswith("[DEMO SAMPLE]")
    assert client.get("/api/reports/forecast?month=2026-13", headers=admin_headers).status_code == 422
    assert client.get("/api/reports/forecast", headers=staff_headers).status_code == 403


def test_forecast_returns_zero_until_orders_exist(client: TestClient):
    admin_headers = sign_in(client, "admin", "test-admin-pass")

    forecast = client.get("/api/reports/forecast", headers=admin_headers)

    assert forecast.status_code == 200
    assert forecast.json()["forecast_sales"] == 0
    assert forecast.json()["historical_orders"] == 0
    assert forecast.json()["previous_month"]["order_count"] == 0
    assert forecast.json()["previous_month"]["orders"] == []
    assert forecast.json()["best_sellers"] == []


def test_customer_can_cancel_order_and_restore_inventory_without_counting_cancelled_sales(client: TestClient):
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    item = client.get("/api/menu", headers=admin_headers).json()[0]
    table = client.post(
        "/api/admin/tables",
        headers=admin_headers,
        json={"table_number": "Table 23"},
    ).json()
    table_token = parse_qs(urlparse(table["order_url"]).query)["token"][0]
    ingredient = client.post(
        "/api/admin/inventory",
        headers=admin_headers,
        json={"name": "Cancellation test stock", "unit": "kg", "quantity": "10", "minimum_quantity": "1"},
    )
    assert ingredient.status_code == 201
    recipe = client.put(
        f"/api/admin/menu/{item['id']}/recipe",
        headers=admin_headers,
        json={"ingredients": [{"ingredient_id": ingredient.json()["id"], "quantity_per_item": "0.25"}]},
    )
    assert recipe.status_code == 200
    signup = client.post(
        "/api/customer/signup",
        json={"username": "cancel.customer", "display_name": "Cancel Customer", "password": "customer-password"},
    )
    assert signup.status_code == 201
    customer_headers = {"Authorization": f"Bearer {signup.json()['token']}"}
    with api.engine.begin() as connection:
        connection.execute(
            api.customers.update()
            .where(api.customers.c.id == signup.json()["user"]["id"])
            .values(loyalty_points=50)
        )
    other_signup = client.post(
        "/api/customer/signup",
        json={"username": "other.customer", "display_name": "Other Customer", "password": "customer-password"},
    )
    assert other_signup.status_code == 201
    other_headers = {"Authorization": f"Bearer {other_signup.json()['token']}"}

    order = client.post(
        f"/api/customer/orders/qr?table={table['table_number']}&token={table_token}",
        headers=customer_headers,
        json={"items": [{"item_id": item["id"], "quantity": 2}], "points_to_redeem": 10},
    )
    assert order.status_code == 201
    order_id = order.json()["id"]
    inventory = client.get("/api/admin/inventory", headers=admin_headers).json()
    stock = next(row for row in inventory if row["id"] == ingredient.json()["id"])
    assert Decimal(stock["quantity"]) == Decimal("9.500")
    assert client.get("/api/customer/me", headers=customer_headers).json()["loyalty_points"] == 40
    recipe = client.put(
        f"/api/admin/menu/{item['id']}/recipe",
        headers=admin_headers,
        json={"ingredients": [{"ingredient_id": ingredient.json()["id"], "quantity_per_item": "0.5"}]},
    )
    assert recipe.status_code == 200
    assert client.post(
        f"/api/customer/orders/{order_id}/cancel",
        headers=other_headers,
        json={"reason": "Not my order"},
    ).status_code == 404

    payment = client.post(
        f"/api/orders/{order_id}/pay",
        headers=admin_headers,
        json={"cash_received": order.json()["total"]},
    )
    assert payment.status_code == 200
    cancelled = client.post(
        f"/api/customer/orders/{order_id}/cancel",
        headers=customer_headers,
        json={"reason": "Plans changed"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["order_status"] == "cancelled"
    assert cancelled.json()["cancellation_reason"] == "Plans changed"
    assert client.get("/api/customer/me", headers=customer_headers).json()["loyalty_points"] == 50
    assert client.post(
        f"/api/customer/orders/{order_id}/cancel",
        headers=customer_headers,
        json={},
    ).status_code == 409
    assert client.post(
        f"/api/orders/{order_id}/pay",
        headers=admin_headers,
        json={"cash_received": order.json()["total"]},
    ).status_code == 409
    optional_reason_order = client.post(
        f"/api/customer/orders/qr?table={table['table_number']}&token={table_token}",
        headers=customer_headers,
        json={"items": [{"item_id": item["id"], "quantity": 1}]},
    )
    assert optional_reason_order.status_code == 201
    optional_reason_cancel = client.post(
        f"/api/customer/orders/{optional_reason_order.json()['id']}/cancel",
        headers=customer_headers,
        json={},
    )
    assert optional_reason_cancel.status_code == 200
    assert optional_reason_cancel.json()["cancellation_reason"] is None

    inventory = client.get("/api/admin/inventory", headers=admin_headers).json()
    stock = next(row for row in inventory if row["id"] == ingredient.json()["id"])
    assert Decimal(stock["quantity"]) == Decimal("10.000")
    daily = client.get(
        f"/api/reports/daily?report_date={date.today()}",
        headers=admin_headers,
    ).json()
    assert daily["order_count"] == 0
    assert daily["sales_revenue"] == 0
    assert daily["orders"][0]["order_status"] == "cancelled"
    assert client.get("/api/orders", headers=admin_headers).json()[0]["order_status"] == "cancelled"
    analytics = client.get(
        f"/api/reports/analytics?start_date={date.today()}&end_date={date.today()}",
        headers=admin_headers,
    ).json()
    assert analytics["order_count"] == 0
    assert analytics["sales_revenue"] == 0
    forecast = client.get("/api/reports/forecast", headers=admin_headers).json()
    assert forecast["historical_orders"] == 0
    monthly = client.get("/api/reports/forecast/monthly", headers=admin_headers)
    assert monthly.status_code == 200
    assert [row["month"] for row in monthly.json()["months"]] == [
        "2026-11", "2026-12", "2027-01", "2027-02", "2027-03",
    ]
    assert all(isinstance(row["projected_revenue"], int) for row in monthly.json()["months"])
    assert "recent sales trend" in monthly.json()["forecast_factors"]
    for row in monthly.json()["months"]:
        expected_status = (
            "actual" if row["month"] < date.today().strftime("%Y-%m")
            else "current" if row["month"] == date.today().strftime("%Y-%m")
            else "forecast"
        )
        assert row["status"] == expected_status


def test_completed_customer_order_cannot_be_cancelled(client: TestClient):
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    table = client.post(
        "/api/admin/tables",
        headers=admin_headers,
        json={"table_number": "Table 24"},
    ).json()
    table_token = parse_qs(urlparse(table["order_url"]).query)["token"][0]
    signup = client.post(
        "/api/customer/signup",
        json={"username": "completed.customer", "display_name": "Completed Customer", "password": "customer-password"},
    ).json()
    customer_headers = {"Authorization": f"Bearer {signup['token']}"}
    item = client.get("/api/menu", headers=admin_headers).json()[0]
    order = client.post(
        f"/api/customer/orders/qr?table={table['table_number']}&token={table_token}",
        headers=customer_headers,
        json={"items": [{"item_id": item["id"], "quantity": 1}]},
    )
    assert order.status_code == 201
    with api.engine.begin() as connection:
        connection.execute(
            api.order_items.update()
            .where(api.order_items.c.order_id == order.json()["id"])
            .values(prep_status="delivered")
        )
    cancelled = client.post(
        f"/api/customer/orders/{order.json()['id']}/cancel",
        headers=customer_headers,
        json={"reason": "Too late"},
    )
    assert cancelled.status_code == 409


def test_monthly_forecast_applies_recent_trend_and_festival_adjustments(client: TestClient, monkeypatch):
    class FrozenDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 11, 13)

    monkeypatch.setattr(api, "date", FrozenDate)
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    item = client.get("/api/menu", headers=admin_headers).json()[0]
    for month, quantity in zip(range(5, 11), range(1, 7)):
        order = client.post(
            "/api/orders",
            headers=admin_headers,
            json={
                "order_type": "Takeaway",
                "cash_received": item["price"] * quantity + 100,
                "items": [{"item_id": item["id"], "quantity": quantity}],
            },
        )
        assert order.status_code == 201
        with api.engine.begin() as connection:
            connection.execute(
                api.orders.update()
                .where(api.orders.c.id == order.json()["id"])
                .values(created_at=datetime(2026, month, 15))
            )

    forecast = client.get("/api/reports/forecast/monthly", headers=admin_headers)

    assert forecast.status_code == 200
    result = forecast.json()
    assert result["trend_adjustment_percent"] == 15
    assert result["months"][0]["status"] == "current"
    assert result["months"][1]["status"] == "forecast"
    assert any("Christmas" in festival for festival in result["months"][1]["festivals"])


def test_forecast_includes_raw_previous_month_orders(client: TestClient):
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    item = client.get("/api/menu", headers=admin_headers).json()[0]
    created = client.post(
        "/api/orders",
        headers=admin_headers,
        json={
            "order_type": "Takeaway",
            "cash_received": item["price"] + 100,
            "items": [{"item_id": item["id"], "quantity": 1}],
        },
    )
    assert created.status_code == 201
    today = date.today()
    previous_month = (today.replace(day=1) - timedelta(days=1)).replace(day=12)
    with api.engine.begin() as connection:
        connection.execute(
            update(api.orders)
            .where(api.orders.c.id == created.json()["id"])
            .values(created_at=datetime.combine(previous_month, datetime.min.time()))
        )

    forecast = client.get("/api/reports/forecast", headers=admin_headers)

    assert forecast.status_code == 200
    assert forecast.json()["previous_month"]["order_count"] == 1
    assert forecast.json()["previous_month"]["orders"][0]["id"] == created.json()["id"]


def test_admin_can_create_disable_and_reset_employee_account(client: TestClient):
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    staff_headers = sign_in(client, "staff", "test-staff-pass")

    denied = client.post(
        "/api/admin/employees",
        headers=staff_headers,
        json={"username": "new.employee", "display_name": "New Employee", "password": "new-password-123"},
    )
    created = client.post(
        "/api/admin/employees",
        headers=admin_headers,
        json={"username": "new.employee", "display_name": "New Employee", "password": "new-password-123"},
    )

    assert denied.status_code == 403
    assert created.status_code == 201
    employee = created.json()
    assert employee["is_active"] is True
    employee_headers = sign_in(client, "new.employee", "new-password-123")
    assert client.get("/api/menu", headers=employee_headers).status_code == 200
    assert client.get("/api/orders", headers=employee_headers).status_code == 403

    reset = client.put(
        f"/api/admin/employees/{employee['id']}/password",
        headers=admin_headers,
        json={"password": "replacement-password"},
    )
    assert reset.status_code == 200
    assert client.get("/api/menu", headers=employee_headers).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"username": "new.employee", "password": "replacement-password"},
    ).status_code == 200

    disabled = client.patch(
        f"/api/admin/employees/{employee['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert client.get("/api/menu", headers=employee_headers).status_code == 401


def test_customer_qr_dietary_inventory_kitchen_payment_and_loyalty(client: TestClient):
    admin_headers = sign_in(client, "admin", "test-admin-pass")
    reception_headers = sign_in(client, "staff", "test-staff-pass")
    table_response = client.post(
        "/api/admin/tables",
        headers=admin_headers,
        json={"table_number": "Table 12"},
    )
    assert table_response.status_code == 201
    table = parse_qs(urlparse(table_response.json()["order_url"]).query)

    paneer = next(item for item in client.get("/api/menu", headers=admin_headers).json() if item["name"] == "Paneer Tikka")
    paneer.update(dietary_tags=["vegetarian"], dietary_verified=True, allergens_text="dairy")
    assert client.put(f"/api/menu/{paneer['id']}", headers=admin_headers, json=paneer).status_code == 200

    ingredient = client.post(
        "/api/admin/inventory",
        headers=admin_headers,
        json={"name": "Paneer test stock", "unit": "kg", "quantity": 10, "minimum_quantity": 1},
    )
    assert ingredient.status_code == 201
    excessive_waste = client.post(
        f"/api/admin/inventory/{ingredient.json()['id']}/adjust",
        headers=admin_headers,
        json={"quantity_delta": -11, "reason": "Expired stock"},
    )
    assert excessive_waste.status_code == 409
    recipe = client.put(
        f"/api/admin/menu/{paneer['id']}/recipe",
        headers=admin_headers,
        json={"ingredients": [{"ingredient_id": ingredient.json()["id"], "quantity_per_item": 0.25}]},
    )
    assert recipe.status_code == 200

    signup = client.post(
        "/api/customer/signup",
        json={"username": "guest.customer", "display_name": "Guest Customer", "password": "customer-password"},
    )
    assert signup.status_code == 201
    customer_headers = {"Authorization": f"Bearer {signup.json()['token']}"}
    preference = client.put(
        "/api/customer/preferences",
        headers=customer_headers,
        json={"dietary_preferences": ["vegetarian"]},
    )
    assert preference.status_code == 200
    public_menu = client.get("/api/public/menu?dietary=vegetarian").json()
    assert paneer["id"] in [item["id"] for item in public_menu]
    assert all(item["dietary_verified"] for item in public_menu)
    assert client.get("/api/customer/recommendations", headers=customer_headers).status_code == 200

    with client.websocket_connect(
        "/ws/kitchen",
        subprotocols=["restaurant-auth", reception_headers["Authorization"].split(" ", maxsplit=1)[1]],
    ) as reception_socket:
        order = client.post(
            f"/api/customer/orders/qr?table={table['table'][0]}&token={table['token'][0]}",
            headers=customer_headers,
            json={"items": [{"item_id": paneer["id"], "quantity": 2}]},
        )
        assert order.status_code == 201
        assert reception_socket.receive_json() == {"type": "order.created", "order_id": order.json()["id"]}
    assert order.json()["payment_status"] == "unpaid"
    assert order.json()["total"] > 500
    pending = client.get("/api/orders/unpaid", headers=admin_headers)
    assert pending.status_code == 200
    assert pending.json()[0]["id"] == order.json()["id"]
    daily_pending = client.get(
        f"/api/reports/daily?report_date={date.today()}",
        headers=admin_headers,
    ).json()
    assert daily_pending["sales_revenue"] == 0
    assert daily_pending["unpaid_total"] == order.json()["total"]
    insufficient = client.post(
        f"/api/customer/orders/qr?table={table['table'][0]}&token={table['token'][0]}",
        headers=customer_headers,
        json={"items": [{"item_id": paneer["id"], "quantity": 40}]},
    )
    assert insufficient.status_code == 409
    assert len(client.get("/api/customer/orders", headers=customer_headers).json()) == 1
    inventory = client.get("/api/admin/inventory", headers=admin_headers).json()
    assert Decimal(next(item for item in inventory if item["id"] == ingredient.json()["id"])["quantity"]) == Decimal("9.500")

    kitchen = client.post(
        "/api/admin/employees",
        headers=admin_headers,
        json={
            "username": "test.kitchen",
            "display_name": "Test Kitchen",
            "password": "kitchen-password",
            "employee_type": "kitchen",
        },
    ).json()
    kitchen_headers = sign_in(client, kitchen["username"], "kitchen-password")
    prep_order = next(item for item in client.get("/api/prep/orders", headers=kitchen_headers).json() if item["id"] == order.json()["id"])
    prep_item = prep_order["items"][0]
    token = kitchen_headers["Authorization"].split(" ", maxsplit=1)[1]
    with client.websocket_connect("/ws/kitchen", subprotocols=["restaurant-auth", token]) as socket:
        for next_status in ("preparing", "ready", "delivered"):
            changed = client.patch(
                f"/api/prep/items/{prep_item['id']}",
                headers=kitchen_headers,
                json={"status": next_status},
            )
            assert changed.status_code == 200
            assert socket.receive_json() == {
                "type": "prep.updated",
                "item_id": prep_item["id"],
                "status": next_status,
                "payment_status": "unpaid",
            }
    assert all(item["id"] != order.json()["id"] for item in client.get("/api/prep/orders", headers=kitchen_headers).json())
    assert client.get(f"/api/customer/orders/{order.json()['id']}", headers=customer_headers).json()["payment_status"] == "unpaid"
    assert client.get(
        f"/api/reports/daily?report_date={date.today()}",
        headers=admin_headers,
    ).json()["sales_revenue"] == 0

    payment = client.post(
        f"/api/orders/{order.json()['id']}/pay",
        headers=admin_headers,
        json={"cash_received": order.json()["total"] + 20},
    )
    assert payment.status_code == 200
    assert payment.json()["change_due"] == 20
    profile = client.get("/api/customer/me", headers=customer_headers).json()
    assert profile["loyalty_points"] == order.json()["total"] // 100
    assert client.get("/api/customer/orders", headers=customer_headers).json()[0]["payment_status"] == "paid"
    daily_paid = client.get(
        f"/api/reports/daily?report_date={date.today()}",
        headers=admin_headers,
    ).json()
    assert daily_paid["sales_revenue"] == order.json()["subtotal"]

    kitchen_paid_order = client.post(
        f"/api/customer/orders/qr?table={table['table'][0]}&token={table['token'][0]}",
        headers=customer_headers,
        json={"items": [{"item_id": paneer["id"], "quantity": 1}]},
    )
    assert kitchen_paid_order.status_code == 201
    prep_ticket = next(
        ticket
        for ticket in client.get("/api/prep/orders", headers=kitchen_headers).json()
        if ticket["id"] == kitchen_paid_order.json()["id"]
    )
    kitchen_item = prep_ticket["items"][0]
    assert kitchen_item["order_id"] == kitchen_paid_order.json()["id"]
    for next_status in ("preparing", "ready"):
        updated = client.patch(
            f"/api/prep/items/{kitchen_item['id']}",
            headers=kitchen_headers,
            json={"status": next_status},
        )
        assert updated.status_code == 200
    kitchen_payment = client.post(
        f"/api/orders/{kitchen_paid_order.json()['id']}/confirm-payment",
        headers=kitchen_headers,
        json={"paid": True},
    )
    assert kitchen_payment.status_code == 403
    no_payment = client.post(
        f"/api/orders/{kitchen_paid_order.json()['id']}/confirm-payment",
        headers=reception_headers,
        json={"paid": False},
    )
    assert no_payment.status_code == 200
    assert no_payment.json()["payment_status"] == "unpaid"
    payment_confirmation = client.post(
        f"/api/orders/{kitchen_paid_order.json()['id']}/confirm-payment",
        headers=reception_headers,
        json={"paid": True},
    )
    assert payment_confirmation.status_code == 200
    assert payment_confirmation.json()["payment_status"] == "paid"
    paid_order = client.get(
        f"/api/customer/orders/{kitchen_paid_order.json()['id']}",
        headers=customer_headers,
    ).json()
    assert paid_order["payment_status"] == "paid"
    paid_report = client.get(
        f"/api/reports/daily?report_date={date.today()}",
        headers=admin_headers,
    ).json()
    assert paid_report["sales_revenue"] == order.json()["subtotal"] + kitchen_paid_order.json()["subtotal"]

    refreshed_qr = client.post(f"/api/admin/tables/{table_response.json()['id']}/qr", headers=admin_headers)
    refreshed_token = parse_qs(urlparse(refreshed_qr.json()["order_url"]).query)["token"][0]
    assert refreshed_token != table["token"][0]
    invalidated = client.post(
        f"/api/customer/orders/qr?table={table['table'][0]}&token={table['token'][0]}",
        headers=customer_headers,
        json={"items": [{"item_id": paneer["id"], "quantity": 1}]},
    )
    assert invalidated.status_code == 404
    assert client.get(f"/api/reports/analytics?start_date={date.today()}&end_date={date.today()}", headers=admin_headers).json()["paid_order_count"] == 2
    assert "order_id" in client.get(
        f"/api/reports/export.csv?start_date={date.today()}&end_date={date.today()}",
        headers=admin_headers,
    ).text
    assert client.post(
        "/api/customer/chat",
        headers=customer_headers,
        json={"question": "What allergens are in Paneer Tikka?"},
    ).json()["answer"].find("dairy") >= 0
