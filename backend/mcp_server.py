import hmac
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from sqlalchemy import text
from starlette.responses import JSONResponse

from backend.admin_analytics import create_read_only_engine, execute_tool

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
logger = logging.getLogger("restaurant.admin_mcp")

mcp = FastMCP("Restaurant Admin Analytics", stateless_http=True)
READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def _result(name: str, **arguments: Any) -> str:
    import json

    return json.dumps(execute_tool(name, arguments), ensure_ascii=True)


@mcp.tool(description="Paid sales totals, daily breakdown, unpaid orders, and cancellations for an inclusive date range.", annotations=READ_ONLY_ANNOTATIONS)
def get_sales(start_date: str, end_date: str) -> str:
    return _result("get_sales", start_date=start_date, end_date=end_date)


@mcp.tool(description="Revenue from paid, non-cancelled orders for an inclusive date range. Revenue is before tax.", annotations=READ_ONLY_ANNOTATIONS)
def get_revenue(start_date: str, end_date: str) -> str:
    return _result("get_revenue", start_date=start_date, end_date=end_date)


@mcp.tool(description="Gross and net profit from actual saved item costs and recorded monthly operating expenses. Reports missing inputs instead of filling them in.", annotations=READ_ONLY_ANNOTATIONS)
def get_profit(start_date: str, end_date: str) -> str:
    return _result("get_profit", start_date=start_date, end_date=end_date)


@mcp.tool(description="Order status, payment status, totals, and item summaries for an inclusive date range (up to 100 records).", annotations=READ_ONLY_ANNOTATIONS)
def get_orders(start_date: str, end_date: str) -> str:
    return _result("get_orders", start_date=start_date, end_date=end_date)


@mcp.tool(description="Cancelled order records and recorded cancellation reasons for an inclusive date range (up to 100 records).", annotations=READ_ONLY_ANNOTATIONS)
def get_cancelled_orders(start_date: str, end_date: str) -> str:
    return _result("get_cancelled_orders", start_date=start_date, end_date=end_date)


@mcp.tool(description="Paid menu-item and category sales analytics for an inclusive date range, ranked by units sold.", annotations=READ_ONLY_ANNOTATIONS)
def get_food_analytics(start_date: str, end_date: str) -> str:
    return _result("get_food_analytics", start_date=start_date, end_date=end_date)


@mcp.tool(description="Current ingredient quantities, minimum stock thresholds, expiry dates, and low-stock flags.", annotations=READ_ONLY_ANNOTATIONS)
def get_inventory() -> str:
    return _result("get_inventory")


@mcp.tool(description="Recorded monthly operating expenses for an inclusive date range. Expenses are stored at monthly granularity.", annotations=READ_ONLY_ANNOTATIONS)
def get_expenses(start_date: str, end_date: str) -> str:
    return _result("get_expenses", start_date=start_date, end_date=end_date)


@mcp.tool(description="Aggregated customer and repeat-purchase metrics based only on paid, non-cancelled orders. No customer names or contact information are returned.", annotations=READ_ONLY_ANNOTATIONS)
def get_customer_analytics(start_date: str, end_date: str) -> str:
    return _result("get_customer_analytics", start_date=start_date, end_date=end_date)


@mcp.tool(description="Employee attendance for an inclusive date range. Clearly reports unavailable if the database has no supported attendance table.", annotations=READ_ONLY_ANNOTATIONS)
def get_employee_attendance(start_date: str, end_date: str) -> str:
    return _result("get_employee_attendance", start_date=start_date, end_date=end_date)


@mcp.tool(description="Actual monthly revenue and cautious month-by-month revenue/profit estimates between YYYY-MM values. Estimates require sufficient actual data; net profit remains unavailable when costs or expenses are incomplete.", annotations=READ_ONLY_ANNOTATIONS)
def forecast_sales(start_month: str, end_month: str) -> str:
    return _result("forecast_sales", start_month=start_month, end_month=end_month)


class BearerGuard:
    def __init__(self, application, token: str):
        self.application = application
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").startswith("/mcp"):
            authorization = dict(scope.get("headers", [])).get(b"authorization", b"").decode("latin-1")
            supplied = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
            if not self.token or not hmac.compare_digest(supplied, self.token):
                response = JSONResponse({"detail": "Unauthorized MCP client"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.application(scope, receive, send)


app = BearerGuard(mcp.streamable_http_app(), os.environ.get("MCP_SHARED_TOKEN", ""))


def main() -> None:
    import uvicorn

    token = os.environ.get("MCP_SHARED_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("MCP_SHARED_TOKEN must contain at least 32 characters")
    engine = create_read_only_engine()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    logger.info("Starting read-only restaurant MCP service on 127.0.0.1:8003")
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("MCP_PORT", "8003")))


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    main()
