import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert

from backend import app as api
from backend import admin_chat
from backend.admin_analytics import execute_tool
from backend.mcp_server import BearerGuard, mcp


def mock_provider_transport(monkeypatch, handler):
    client_class = admin_chat.httpx.AsyncClient
    transport = admin_chat.httpx.MockTransport(handler)
    monkeypatch.setattr(
        admin_chat.httpx,
        "AsyncClient",
        lambda **kwargs: client_class(transport=transport, **kwargs),
    )


@pytest.fixture
def analytics_engine():
    test_engine = create_engine("sqlite://")
    api.metadata.create_all(test_engine)
    with test_engine.begin() as connection:
        connection.execute(insert(api.customers).values(
            id=1,
            username="customer",
            display_name="Test Customer",
            password_hash="not-used",
            loyalty_points=0,
            created_at=datetime(2026, 1, 1),
            is_active=True,
        ))
        connection.execute(insert(api.menu_items).values(
            id=1,
            name="Test dish",
            category="Main course",
            price=50,
            cost_price=20,
            description="",
            popular=False,
            image="test",
            ingredients_text="",
            allergens_text="",
        ))
        connection.execute(insert(api.orders), [
            {
                "id": 1, "order_type": "Takeaway", "subtotal": 150, "tax": 8, "total": 158,
                "cash_received": 158, "change_due": 0, "customer_id": 1, "payment_status": "paid",
                "discount_amount": 0, "order_status": "active", "created_at": datetime(2026, 1, 1, 12),
                "cancellation_reason": None, "note": "",
            },
            {
                "id": 2, "order_type": "Takeaway", "subtotal": 100, "tax": 5, "total": 105,
                "cash_received": 105, "change_due": 0, "customer_id": None, "payment_status": "paid",
                "discount_amount": 0, "order_status": "cancelled", "created_at": datetime(2026, 1, 2, 12),
                "cancellation_reason": "Customer request", "note": "",
            },
            {
                "id": 3, "order_type": "Dine in", "subtotal": 80, "tax": 4, "total": 84,
                "cash_received": 0, "change_due": 0, "customer_id": None, "payment_status": "unpaid", "discount_amount": 0,
                "order_status": "active", "created_at": datetime(2026, 1, 3, 12),
                "cancellation_reason": None, "note": "",
            },
        ])
        connection.execute(insert(api.order_items), [
            {"id": 1, "order_id": 1, "menu_item_id": 1, "item_name": "Test dish", "unit_price": 50, "unit_cost": 20, "quantity": 3},
            {"id": 2, "order_id": 2, "menu_item_id": 1, "item_name": "Test dish", "unit_price": 50, "unit_cost": 20, "quantity": 2},
            {"id": 3, "order_id": 3, "menu_item_id": 1, "item_name": "Test dish", "unit_price": 50, "unit_cost": 20, "quantity": 1},
        ])
        connection.execute(insert(api.ingredients).values(
            id=1, name="Flour", unit="kg", quantity=3, minimum_quantity=5, updated_at=datetime(2026, 1, 1)
        ))
        connection.execute(insert(api.operating_expenses).values(
            month="2026-01", category="rent", amount=30, note="Recorded rent"
        ))
    yield test_engine
    test_engine.dispose()


def test_read_only_mcp_analytics_tools_match_database_records(analytics_engine):
    start_date, end_date = "2026-01-01", "2026-01-31"

    sales = execute_tool("get_sales", {"start_date": start_date, "end_date": end_date}, analytics_engine)
    assert sales["sales_revenue"] == 150
    assert sales["paid_order_count"] == 1
    assert sales["unpaid_total"] == 84
    assert sales["cancelled_order_count"] == 1
    assert execute_tool("get_revenue", {"start_date": start_date, "end_date": end_date}, analytics_engine)["sales_revenue"] == 150

    profit = execute_tool("get_profit", {"start_date": start_date, "end_date": end_date}, analytics_engine)
    assert profit["food_cost"] == 60
    assert profit["gross_profit"] == 90
    assert profit["operating_expenses"] == 30
    assert profit["net_profit"] == 60

    orders = execute_tool("get_orders", {"start_date": start_date, "end_date": end_date}, analytics_engine)
    cancelled = execute_tool("get_cancelled_orders", {"start_date": start_date, "end_date": end_date}, analytics_engine)
    assert orders["returned_orders"] == 3
    assert cancelled["orders"][0]["cancellation_reason"] == "Customer request"

    food = execute_tool("get_food_analytics", {"start_date": start_date, "end_date": end_date}, analytics_engine)
    assert food["products"] == [{"item": "Test dish", "units_sold": 3, "revenue": 150}]
    assert execute_tool("get_inventory", {}, analytics_engine)["low_stock_count"] == 1
    assert execute_tool("get_expenses", {"start_date": start_date, "end_date": end_date}, analytics_engine)["monthly_totals"] == [
        {"month": "2026-01", "amount": 30}
    ]

    customer = execute_tool("get_customer_analytics", {"start_date": start_date, "end_date": end_date}, analytics_engine)
    assert customer["unique_paying_customers"] == 1
    assert customer["sales_revenue"] == 150
    assert execute_tool("get_employee_attendance", {"start_date": start_date, "end_date": end_date}, analytics_engine)["available"] is False


def test_forecast_does_not_invent_results_without_sales_history(analytics_engine):
    result = execute_tool(
        "forecast_sales",
        {"start_month": "2027-01", "end_month": "2027-03"},
        analytics_engine,
    )
    assert result["revenue_prediction_available"] is False
    assert result["profit_prediction_available"] is False
    assert all(month["predicted_revenue"] is None for month in result["months"])
    assert all(month["predicted_net_profit"] is None for month in result["months"])


def test_analytics_tool_date_ranges_are_validated(analytics_engine):
    with pytest.raises(ValueError, match="on or after"):
        execute_tool("get_sales", {"start_date": "2026-02-01", "end_date": "2026-01-01"}, analytics_engine)
    with pytest.raises(ValueError, match="cannot exceed"):
        execute_tool("get_sales", {"start_date": "2025-01-01", "end_date": "2026-01-02"}, analytics_engine)


@pytest.mark.parametrize(
    "greeting",
    ["hello", "Hi!", "hie how are you?", "good morning"],
)
def test_standalone_greetings_work_without_provider(greeting, monkeypatch):
    monkeypatch.setattr(
        admin_chat,
        "_configuration",
        lambda: pytest.fail("A standalone greeting should not call the AI provider."),
    )
    result = asyncio.run(
        admin_chat.answer_admin_question([{"role": "user", "content": greeting}])
    )
    assert result["tools_used"] == []
    assert "ready to help" in result["answer"]


def test_greeting_with_a_business_question_is_not_handled_as_small_talk():
    assert not admin_chat._is_small_talk_greeting("Hello, what are today's total sales?")


def test_fastmcp_registers_the_expected_read_only_tool_catalog():
    tools = asyncio.run(mcp.list_tools())
    assert {tool.name for tool in tools} == {
        "get_sales",
        "get_revenue",
        "get_profit",
        "get_orders",
        "get_cancelled_orders",
        "get_food_analytics",
        "get_inventory",
        "get_expenses",
        "get_customer_analytics",
        "get_employee_attendance",
        "forecast_sales",
    }
    assert all(
        tool.annotations
        and tool.annotations.readOnlyHint is True
        and tool.annotations.destructiveHint is False
        for tool in tools
    )


def test_mcp_http_endpoint_requires_the_shared_bearer_token():
    inner_app = FastAPI()

    @inner_app.get("/mcp")
    def authenticated_probe():
        return {"ok": True}

    with TestClient(BearerGuard(inner_app, "test-shared-token-with-more-than-32-characters")) as client:
        assert client.get("/mcp").status_code == 401
        response = client.get(
            "/mcp",
            headers={"Authorization": "Bearer test-shared-token-with-more-than-32-characters"},
        )
        assert response.status_code == 200


def test_ai_provider_errors_are_raised_after_mcp_context_closes(monkeypatch):
    class AsyncContext:
        async def __aenter__(self):
            return (object(), object(), None)

        async def __aexit__(self, exc_type, exc_value, traceback):
            assert exc_type is None

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            assert exc_type is None

        async def initialize(self):
            return None

        async def list_tools(self):
            return SimpleNamespace(tools=[])

    monkeypatch.setattr(admin_chat, "_configuration", lambda: ("url", "key", "model", "mcp", "token"))
    monkeypatch.setattr(admin_chat, "streamablehttp_client", lambda *args, **kwargs: AsyncContext())
    monkeypatch.setattr(admin_chat, "ClientSession", FakeSession)

    async def fail_provider(*args, **kwargs):
        raise admin_chat.AdminChatError(
            "The AI provider rate limit or usage quota was reached (HTTP 429)."
        )

    monkeypatch.setattr(admin_chat, "_chat_completion", fail_provider)
    with pytest.raises(admin_chat.AdminChatError, match="usage quota.*429"):
        asyncio.run(admin_chat.answer_admin_question([{"role": "user", "content": "sales?"}]))


def test_ai_provider_retries_rate_limits_up_to_twelve_times(monkeypatch):
    calls = []
    delays = []

    def fake_request(request):
        calls.append(request)
        if len(calls) <= admin_chat.MAX_AI_429_RETRIES:
            return admin_chat.httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return admin_chat.httpx.Response(200, json={"choices": []}, request=request)

    async def fake_sleep(delay):
        delays.append(delay)

    mock_provider_transport(monkeypatch, fake_request)
    monkeypatch.setattr(admin_chat.asyncio, "sleep", fake_sleep)

    result = asyncio.run(admin_chat._chat_completion("https://provider.test/chat", "test-key", {}))

    assert result == {"choices": []}
    assert len(calls) == 13
    assert delays == [0] * admin_chat.MAX_AI_429_RETRIES


def test_ai_provider_reports_exhausted_rate_limit_retries(monkeypatch):
    calls = []
    delays = []

    def always_rate_limited(request):
        calls.append(request)
        return admin_chat.httpx.Response(429, headers={"Retry-After": "0"}, request=request)

    async def fake_sleep(delay):
        delays.append(delay)

    mock_provider_transport(monkeypatch, always_rate_limited)
    monkeypatch.setattr(admin_chat.asyncio, "sleep", fake_sleep)
    with pytest.raises(admin_chat.AdminChatError, match="after 12 retries"):
        asyncio.run(admin_chat._chat_completion("https://provider.test/chat", "test-key", {}))
    assert len(calls) == 13
    assert len(delays) == admin_chat.MAX_AI_429_RETRIES


def test_ai_provider_does_not_retry_exhausted_quota(monkeypatch):
    calls = []

    def exhausted_quota(request):
        calls.append(request)
        return admin_chat.httpx.Response(
            429,
            json={
                "error": {
                    "type": "insufficient_quota",
                    "code": "credit_balance_exhausted",
                    "message": "Credit balance exhausted",
                }
            },
            request=request,
        )

    mock_provider_transport(monkeypatch, exhausted_quota)
    with pytest.raises(admin_chat.AdminChatError, match="exhausted its credits"):
        asyncio.run(admin_chat._chat_completion("https://provider.test/chat", "test-key", {}))
    assert len(calls) == 1


def test_ai_provider_request_can_be_cancelled_during_backoff(monkeypatch):
    async def verify_cancel():
        request_sent = asyncio.Event()

        def rate_limited(request):
            request_sent.set()
            return admin_chat.httpx.Response(
                429,
                headers={"Retry-After": "30"},
                request=request,
            )

        mock_provider_transport(monkeypatch, rate_limited)
        request_task = asyncio.create_task(
            admin_chat._chat_completion("https://provider.test/chat", "test-key", {})
        )
        await asyncio.wait_for(request_sent.wait(), timeout=2)
        request_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request_task

    asyncio.run(verify_cancel())


def test_admin_chat_cancels_work_after_client_disconnect(monkeypatch):
    cancelled = []

    async def waiting_for_completion(messages):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    class DisconnectingRequest:
        checks = 0

        async def is_disconnected(self):
            self.checks += 1
            return self.checks > 1

    monkeypatch.setattr("backend.admin_chat.answer_admin_question", waiting_for_completion)
    response = asyncio.run(
        api.admin_chat(
            api.AdminChatRequest(messages=[{"role": "user", "content": "sales?"}]),
            {"id": 1},
            DisconnectingRequest(),
        )
    )

    assert response.status_code == 499
    assert cancelled == [True]


def test_admin_chat_endpoint_is_admin_only(monkeypatch, tmp_path):
    test_engine = create_engine(f"sqlite:///{tmp_path / 'admin-chat-test.db'}")
    monkeypatch.setattr(api, "engine", test_engine)
    monkeypatch.setenv("RESTAURANT_ADMIN_PASSWORD", "test-admin-pass")
    monkeypatch.setenv("RESTAURANT_STAFF_PASSWORD", "test-staff-pass")
    monkeypatch.setenv("RESTAURANT_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("RESTAURANT_STAFF_USERNAME", "staff")

    async def fake_answer(messages):
        assert messages[-1]["content"] == "What are today's sales?"
        return {"answer": "Sales were ₹0.", "tools_used": ["get_sales"], "timestamp": "2026-11-17T10:00:00"}

    monkeypatch.setattr("backend.admin_chat.answer_admin_question", fake_answer)
    try:
        with TestClient(api.app) as client:
            admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "test-admin-pass"})
            staff_login = client.post("/api/auth/login", json={"username": "staff", "password": "test-staff-pass"})
            body = {"messages": [{"role": "user", "content": "What are today's sales?"}]}
            admin_headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}
            staff_headers = {"Authorization": f"Bearer {staff_login.json()['token']}"}

            assert client.post("/api/admin/chat", json=body, headers=admin_headers).status_code == 200
            assert client.post("/api/admin/chat", json=body, headers=staff_headers).status_code == 403
            assert client.post("/api/admin/chat", json=body).status_code == 401
    finally:
        test_engine.dispose()


def test_exhausted_quota_falls_back_to_local_analytics(monkeypatch, analytics_engine):
    class AsyncContext:
        async def __aenter__(self):
            return (object(), object(), None)

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

        async def initialize(self):
            pass

        async def list_tools(self):
            return SimpleNamespace(tools=[])

        async def call_tool(self, name, arguments):
            from backend.admin_analytics import execute_tool
            data = execute_tool(name, arguments, analytics_engine)
            import json
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(data))])

    monkeypatch.setattr(admin_chat, "_configuration", lambda: ("url", "key", "model", "mcp", "token"))
    monkeypatch.setattr(admin_chat, "streamablehttp_client", lambda *args, **kwargs: AsyncContext())
    monkeypatch.setattr(admin_chat, "ClientSession", FakeSession)

    async def fail_with_quota(*args, **kwargs):
        raise admin_chat.AdminChatError(
            "The AI provider account has exhausted its credits or usage quota. Add credits or use a provider account with available quota, then retry."
        )

    monkeypatch.setattr(admin_chat, "_chat_completion", fail_with_quota)
    result = asyncio.run(
        admin_chat.answer_admin_question([{"role": "user", "content": "What are today's total sales?"}])
    )
    assert "Sales Summary" in result["answer"]
    assert "get_sales" in result["tools_used"]


def test_local_mode_answers_directly_without_ai_provider(monkeypatch, analytics_engine):
    class AsyncContext:
        async def __aenter__(self):
            return (object(), object(), None)

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

        async def call_tool(self, name, arguments):
            from backend.admin_analytics import execute_tool
            data = execute_tool(name, arguments, analytics_engine)
            import json
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(data))])

    monkeypatch.setattr(admin_chat, "_configuration", lambda: ("http://local", "local", "local-analytics", "mcp", "token"))
    monkeypatch.setattr(admin_chat, "streamablehttp_client", lambda *args, **kwargs: AsyncContext())
    monkeypatch.setattr(admin_chat, "ClientSession", FakeSession)

    def should_not_be_called(*args, **kwargs):
        raise AssertionError("_chat_completion should not be called in local mode")

    monkeypatch.setattr(admin_chat, "_chat_completion", should_not_be_called)

    inventory_result = asyncio.run(
        admin_chat.answer_admin_question([{"role": "user", "content": "Which ingredients are running low?"}])
    )
    assert "Inventory" in inventory_result["answer"]
    assert "get_inventory" in inventory_result["tools_used"]

