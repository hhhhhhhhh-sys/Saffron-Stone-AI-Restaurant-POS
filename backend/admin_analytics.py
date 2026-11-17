import calendar
import logging
import os
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine

from backend.app import (
    customers,
    ingredients,
    menu_items,
    operating_expenses,
    order_items,
    orders,
)

logger = logging.getLogger("restaurant.admin_mcp")


@lru_cache(maxsize=1)
def create_read_only_engine() -> Engine:
    from sqlalchemy import URL, create_engine

    database_url = os.environ.get("MCP_DATABASE_URL")
    if database_url:
        return create_engine(database_url, pool_pre_ping=True)

    password = os.environ.get("MYSQL_READONLY_PASSWORD")
    if not password:
        raise RuntimeError(
            "Configure MCP_DATABASE_URL or MYSQL_READONLY_PASSWORD for the MCP read-only account"
        )
    return create_engine(
        URL.create(
            "mysql+pymysql",
            username=os.environ.get("MYSQL_READONLY_USER", "restaurant_mcp_reader"),
            password=password,
            host=os.environ.get("MYSQL_HOST", "localhost"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            database=os.environ.get("MYSQL_DATABASE", "restaurant_db"),
            query={"charset": "utf8mb4"},
        ),
        pool_pre_ping=True,
    )


def _database(engine: Engine | None) -> Engine:
    return engine if engine is not None else create_read_only_engine()


def _date_range(start_date: str, end_date: str, max_days: int = 366) -> tuple[date, date]:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except (TypeError, ValueError) as error:
        raise ValueError("Dates must use YYYY-MM-DD format") from error
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    if (end - start).days + 1 > max_days:
        raise ValueError(f"Date range cannot exceed {max_days} days")
    return start, end


def _month_range(start_month: str, end_month: str) -> tuple[date, date]:
    try:
        start = date.fromisoformat(f"{start_month}-01")
        end = date.fromisoformat(f"{end_month}-01")
    except (TypeError, ValueError) as error:
        raise ValueError("Months must use YYYY-MM format") from error
    if start.strftime("%Y-%m") != start_month or end.strftime("%Y-%m") != end_month:
        raise ValueError("Months must use YYYY-MM format")
    if end < start:
        raise ValueError("end_month must be on or after start_month")
    month_count = (end.year - start.year) * 12 + end.month - start.month + 1
    if month_count > 18:
        raise ValueError("Forecast range cannot exceed 18 months")
    return start, end


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return datetime.combine(start, time.min), datetime.combine(end + timedelta(days=1), time.min)


def _order_rows(connection, start: date, end: date) -> list[dict[str, Any]]:
    start_at, end_at = _bounds(start, end)
    rows = connection.execute(
        select(
            orders.c.id,
            orders.c.created_at,
            orders.c.subtotal,
            orders.c.tax,
            orders.c.total,
            orders.c.payment_status,
            orders.c.order_status,
            orders.c.discount_amount,
            orders.c.note,
        )
        .where(orders.c.created_at >= start_at, orders.c.created_at < end_at)
        .order_by(orders.c.created_at, orders.c.id)
    ).mappings().all()
    return [dict(row) for row in rows]


def _eligible_orders(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if row["payment_status"] == "paid" and row["order_status"] != "cancelled"
    ]


def _demo_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if str(row.get("note") or "").startswith("[DEMO"))


def _sales(start_date: str, end_date: str, engine: Engine | None = None) -> dict[str, Any]:
    start, end = _date_range(start_date, end_date)
    with _database(engine).connect() as connection:
        rows = _order_rows(connection, start, end)
    paid = _eligible_orders(rows)
    daily: dict[str, dict[str, Any]] = {}
    for row in paid:
        order_date = row["created_at"].date().isoformat()
        item = daily.setdefault(order_date, {"date": order_date, "sales": 0, "orders": 0})
        item["sales"] += int(row["subtotal"] or 0)
        item["orders"] += 1
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "sales_revenue": sum(int(row["subtotal"] or 0) for row in paid),
        "paid_order_count": len(paid),
        "unpaid_order_count": sum(
            1 for row in rows
            if row["payment_status"] != "paid" and row["order_status"] != "cancelled"
        ),
        "unpaid_total": sum(
            int(row["total"] or 0) for row in rows
            if row["payment_status"] != "paid" and row["order_status"] != "cancelled"
        ),
        "cancelled_order_count": sum(1 for row in rows if row["order_status"] == "cancelled"),
        "demo_order_count": _demo_count(paid),
        "daily_sales": list(daily.values()),
        "revenue_definition": "Paid, non-cancelled order subtotal before tax; subtotal already reflects recorded discounts.",
    }


def _profit(start_date: str, end_date: str, engine: Engine | None = None) -> dict[str, Any]:
    start, end = _date_range(start_date, end_date)
    start_at, end_at = _bounds(start, end)
    db = _database(engine)
    with db.connect() as connection:
        orders_in_range = _order_rows(connection, start, end)
        paid = _eligible_orders(orders_in_range)
        lines = connection.execute(
            select(order_items.c.unit_cost, order_items.c.quantity)
            .select_from(order_items.join(orders, orders.c.id == order_items.c.order_id))
            .where(
                orders.c.created_at >= start_at,
                orders.c.created_at < end_at,
                orders.c.payment_status == "paid",
                orders.c.order_status != "cancelled",
            )
        ).mappings().all()
        monthly_expenses = connection.execute(
            select(operating_expenses.c.month, operating_expenses.c.amount)
            .where(
                operating_expenses.c.month >= start.strftime("%Y-%m"),
                operating_expenses.c.month <= end.strftime("%Y-%m"),
            )
            .order_by(operating_expenses.c.month)
        ).mappings().all()
    revenue = sum(int(row["subtotal"] or 0) for row in paid)
    missing_cost_quantity = sum(
        int(line["quantity"] or 0) for line in lines if line["unit_cost"] is None
    )
    food_cost = sum(
        int(line["unit_cost"] or 0) * int(line["quantity"] or 0)
        for line in lines if line["unit_cost"] is not None
    )
    full_month_range = start.day == 1 and end.day == calendar.monthrange(end.year, end.month)[1]
    month_count = (end.year - start.year) * 12 + end.month - start.month + 1
    recorded_by_month: dict[str, int] = defaultdict(int)
    for row in monthly_expenses:
        recorded_by_month[row["month"]] += int(row["amount"] or 0)
    expected_months = {
        (start.replace(day=1) + timedelta(days=32 * offset)).strftime("%Y-%m")
        for offset in range(month_count)
    }
    missing_expense_months = sorted(expected_months - recorded_by_month.keys())
    expenses_complete = full_month_range and not missing_expense_months
    gross_profit = revenue - food_cost if missing_cost_quantity == 0 else None
    operating_cost = sum(recorded_by_month.values()) if expenses_complete else None
    net_profit = (
        gross_profit - operating_cost
        if gross_profit is not None and operating_cost is not None
        else None
    )
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "sales_revenue": revenue,
        "food_cost": food_cost,
        "gross_profit": gross_profit,
        "operating_expenses": operating_cost,
        "net_profit": net_profit,
        "profit_complete": net_profit is not None,
        "missing_cost_quantity": missing_cost_quantity,
        "missing_expense_months": missing_expense_months,
        "expense_period_note": (
            "Operating expenses are monthly records and are included only when the requested range covers complete months."
        ),
        "demo_order_count": _demo_count(paid),
    }


def _orders(start_date: str, end_date: str, cancelled_only: bool, engine: Engine | None = None) -> dict[str, Any]:
    start, end = _date_range(start_date, end_date)
    start_at, end_at = _bounds(start, end)
    with _database(engine).connect() as connection:
        base = select(
            orders.c.id,
            orders.c.created_at,
            orders.c.order_status,
            orders.c.payment_status,
            orders.c.order_type,
            orders.c.subtotal,
            orders.c.tax,
            orders.c.total,
            orders.c.cancellation_reason,
            orders.c.note,
        ).where(orders.c.created_at >= start_at, orders.c.created_at < end_at)
        if cancelled_only:
            base = base.where(orders.c.order_status == "cancelled")
        rows = connection.execute(base.order_by(orders.c.created_at.desc(), orders.c.id.desc()).limit(100)).mappings().all()
        ids = [row["id"] for row in rows]
        items_by_order: dict[int, list[dict[str, Any]]] = defaultdict(list)
        if ids:
            item_rows = connection.execute(
                select(order_items.c.order_id, order_items.c.item_name, order_items.c.quantity)
                .where(order_items.c.order_id.in_(ids))
                .order_by(order_items.c.order_id, order_items.c.id)
            ).mappings().all()
            for item in item_rows:
                items_by_order[item["order_id"]].append(
                    {"item": item["item_name"], "quantity": int(item["quantity"])}
                )
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "cancelled_only": cancelled_only,
        "returned_orders": len(rows),
        "truncated": len(rows) == 100,
        "orders": [
            {
                "id": row["id"],
                "created_at": row["created_at"].isoformat(sep=" "),
                "order_status": row["order_status"],
                "payment_status": row["payment_status"],
                "order_type": row["order_type"],
                "subtotal": int(row["subtotal"] or 0),
                "tax": int(row["tax"] or 0),
                "total": int(row["total"] or 0),
                "cancellation_reason": row["cancellation_reason"],
                "demo_order": str(row["note"] or "").startswith("[DEMO"),
                "items": items_by_order.get(row["id"], []),
            }
            for row in rows
        ],
    }


def _food_analytics(start_date: str, end_date: str, engine: Engine | None = None) -> dict[str, Any]:
    start, end = _date_range(start_date, end_date)
    start_at, end_at = _bounds(start, end)
    with _database(engine).connect() as connection:
        rows = connection.execute(
            select(
                order_items.c.item_name,
                menu_items.c.category,
                order_items.c.quantity,
                order_items.c.unit_price,
            )
            .select_from(
                order_items.join(orders, orders.c.id == order_items.c.order_id)
                .outerjoin(menu_items, menu_items.c.id == order_items.c.menu_item_id)
            )
            .where(
                orders.c.created_at >= start_at,
                orders.c.created_at < end_at,
                orders.c.payment_status == "paid",
                orders.c.order_status != "cancelled",
            )
        ).mappings().all()
    products: dict[str, dict[str, Any]] = {}
    categories: dict[str, int] = defaultdict(int)
    for row in rows:
        product = products.setdefault(
            row["item_name"],
            {"item": row["item_name"], "units_sold": 0, "revenue": 0},
        )
        units = int(row["quantity"] or 0)
        value = units * int(row["unit_price"] or 0)
        product["units_sold"] += units
        product["revenue"] += value
        categories[row["category"] or "Other"] += value
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "products": sorted(products.values(), key=lambda row: (-row["units_sold"], row["item"]))[:25],
        "category_revenue": [
            {"category": category, "revenue": value}
            for category, value in sorted(categories.items(), key=lambda item: (-item[1], item[0]))
        ],
        "basis": "Paid, non-cancelled order items only.",
    }


def _inventory(engine: Engine | None = None) -> dict[str, Any]:
    with _database(engine).connect() as connection:
        rows = connection.execute(
            select(
                ingredients.c.name,
                ingredients.c.unit,
                ingredients.c.quantity,
                ingredients.c.minimum_quantity,
                ingredients.c.expires_at,
            ).order_by(ingredients.c.quantity, ingredients.c.name)
        ).mappings().all()
    entries = []
    for row in rows:
        quantity = Decimal(row["quantity"] or 0)
        minimum = Decimal(row["minimum_quantity"] or 0)
        entries.append(
            {
                "ingredient": row["name"],
                "quantity": float(quantity),
                "unit": row["unit"],
                "minimum_quantity": float(minimum),
                "low_stock": quantity <= minimum,
                "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
            }
        )
    return {"ingredients": entries, "low_stock_count": sum(entry["low_stock"] for entry in entries)}


def _expenses(start_date: str, end_date: str, engine: Engine | None = None) -> dict[str, Any]:
    start, end = _date_range(start_date, end_date)
    with _database(engine).connect() as connection:
        rows = connection.execute(
            select(
                operating_expenses.c.month,
                operating_expenses.c.category,
                operating_expenses.c.amount,
                operating_expenses.c.note,
            )
            .where(
                operating_expenses.c.month >= start.strftime("%Y-%m"),
                operating_expenses.c.month <= end.strftime("%Y-%m"),
            )
            .order_by(operating_expenses.c.month, operating_expenses.c.category)
        ).mappings().all()
    details = [
        {
            "month": row["month"],
            "category": row["category"],
            "amount": int(row["amount"] or 0),
            "note": row["note"],
        }
        for row in rows
    ]
    totals: dict[str, int] = defaultdict(int)
    for row in details:
        totals[row["month"]] += row["amount"]
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "monthly_granularity": True,
        "monthly_totals": [{"month": month, "amount": amount} for month, amount in sorted(totals.items())],
        "expenses": details,
    }


def _customer_analytics(start_date: str, end_date: str, engine: Engine | None = None) -> dict[str, Any]:
    start, end = _date_range(start_date, end_date)
    start_at, end_at = _bounds(start, end)
    with _database(engine).connect() as connection:
        orders_rows = connection.execute(
            select(orders.c.customer_id, orders.c.subtotal)
            .where(
                orders.c.created_at >= start_at,
                orders.c.created_at < end_at,
                orders.c.payment_status == "paid",
                orders.c.order_status != "cancelled",
                orders.c.customer_id.is_not(None),
            )
        ).mappings().all()
        new_customers = connection.execute(
            select(customers.c.id).where(
                customers.c.created_at >= start_at,
                customers.c.created_at < end_at,
                customers.c.is_active.is_(True),
            )
        ).all()
    orders_per_customer: dict[int, int] = defaultdict(int)
    revenue = 0
    for row in orders_rows:
        orders_per_customer[row["customer_id"]] += 1
        revenue += int(row["subtotal"] or 0)
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "unique_paying_customers": len(orders_per_customer),
        "new_customer_accounts": len(new_customers),
        "repeat_customers": sum(1 for count in orders_per_customer.values() if count > 1),
        "paid_order_count": len(orders_rows),
        "sales_revenue": revenue,
        "average_paid_order_value": round(revenue / len(orders_rows), 2) if orders_rows else None,
        "customer_names_or_contact_details": "Not returned.",
    }


def _employee_attendance(start_date: str, end_date: str, engine: Engine | None = None) -> dict[str, Any]:
    start, end = _date_range(start_date, end_date)
    db = _database(engine)
    existing_tables = set(inspect(db).get_table_names())
    known_tables = {"employee_attendance", "attendance", "attendance_records"}
    attendance_table = next(iter(existing_tables & known_tables), None)
    if attendance_table is None:
        return {
            "available": False,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "reason": "The existing database has no employee attendance table; no attendance records can be reported.",
        }
    return {
        "available": False,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "reason": f"Found {attendance_table}, but its column layout is not a supported attendance schema. No records were inferred.",
    }


def _forecast(start_month: str, end_month: str, engine: Engine | None = None) -> dict[str, Any]:
    start, end = _month_range(start_month, end_month)
    today = date.today()
    current_month = today.replace(day=1)
    history_start = today - timedelta(days=90)
    history_end = today
    start_at, end_at = _bounds(history_start, history_end - timedelta(days=1))
    db = _database(engine)
    with db.connect() as connection:
        history_rows = connection.execute(
            select(
                orders.c.id,
                orders.c.created_at,
                orders.c.subtotal,
                orders.c.payment_status,
                orders.c.order_status,
                orders.c.note,
            ).where(
                orders.c.created_at >= start_at,
                orders.c.created_at < end_at,
                orders.c.payment_status == "paid",
                orders.c.order_status != "cancelled",
            )
        ).mappings().all()
        item_rows = connection.execute(
            select(
                orders.c.created_at,
                order_items.c.unit_cost,
                order_items.c.quantity,
            )
            .select_from(order_items.join(orders, orders.c.id == order_items.c.order_id))
            .where(
                orders.c.created_at >= start_at,
                orders.c.created_at < end_at,
                orders.c.payment_status == "paid",
                orders.c.order_status != "cancelled",
            )
        ).mappings().all()
        expense_rows = connection.execute(
            select(operating_expenses.c.month, operating_expenses.c.amount)
            .where(operating_expenses.c.month < current_month.strftime("%Y-%m"))
            .order_by(operating_expenses.c.month.desc())
        ).mappings().all()

    daily_revenue: dict[date, int] = defaultdict(int)
    month_revenue: dict[str, int] = defaultdict(int)
    demo_count = 0
    for row in history_rows:
        order_day = row["created_at"].date()
        amount = int(row["subtotal"] or 0)
        daily_revenue[order_day] += amount
        month_revenue[order_day.strftime("%Y-%m")] += amount
        demo_count += str(row["note"] or "").startswith("[DEMO")
    history_days = len(daily_revenue)
    span_days = (max(daily_revenue) - min(daily_revenue)).days + 1 if daily_revenue else 0
    useable_history = history_days >= 10 and span_days >= 28

    weekday_totals: dict[int, int] = defaultdict(int)
    weekday_day_counts: dict[int, int] = defaultdict(int)
    for offset in range(90):
        day = history_start + timedelta(days=offset)
        weekday_totals[day.weekday()] += daily_revenue.get(day, 0)
        weekday_day_counts[day.weekday()] += 1
    weekday_average = {
        weekday: weekday_totals[weekday] / weekday_day_counts[weekday]
        for weekday in range(7)
    }
    observed_revenue = sum(daily_revenue.values())
    cost_complete = all(row["unit_cost"] is not None for row in item_rows)
    observed_food_cost = sum(
        int(row["unit_cost"] or 0) * int(row["quantity"] or 0)
        for row in item_rows if row["unit_cost"] is not None
    )
    cost_ratio = observed_food_cost / observed_revenue if observed_revenue > 0 else None
    expenses_by_month: dict[str, int] = defaultdict(int)
    for row in expense_rows:
        expenses_by_month[row["month"]] += int(row["amount"] or 0)
    recent_expense_months = [
        (current_month.replace(day=1) - timedelta(days=day)).strftime("%Y-%m")
        for day in (1, 32, 63)
    ]
    expenses_complete = all(month in expenses_by_month for month in recent_expense_months)
    estimated_monthly_expense = (
        round(sum(expenses_by_month[month] for month in recent_expense_months) / 3)
        if expenses_complete else None
    )

    results = []
    cursor = start
    while cursor <= end:
        month_key = cursor.strftime("%Y-%m")
        if cursor < current_month:
            month_begin = cursor
            next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end = next_month - timedelta(days=1)
            month_at, month_until = _bounds(month_begin, month_end)
            with db.connect() as connection:
                month_revenue_rows = connection.execute(
                    select(orders.c.subtotal)
                    .where(
                        orders.c.created_at >= month_at,
                        orders.c.created_at < month_until,
                        orders.c.payment_status == "paid",
                        orders.c.order_status != "cancelled",
                    )
                ).mappings().all()
                month_items = connection.execute(
                    select(order_items.c.unit_cost, order_items.c.quantity)
                    .select_from(order_items.join(orders, orders.c.id == order_items.c.order_id))
                    .where(
                        orders.c.created_at >= month_at,
                        orders.c.created_at < month_until,
                        orders.c.payment_status == "paid",
                        orders.c.order_status != "cancelled",
                    )
                ).mappings().all()
            actual_revenue = sum(int(row["subtotal"] or 0) for row in month_revenue_rows)
            actual_cost_complete = all(row["unit_cost"] is not None for row in month_items)
            actual_food_cost = sum(
                int(row["unit_cost"] or 0) * int(row["quantity"] or 0)
                for row in month_items if row["unit_cost"] is not None
            )
            expense_recorded = month_key in expenses_by_month
            results.append({
                "month": month_key,
                "status": "actual",
                "actual_revenue": actual_revenue,
                "predicted_revenue": None,
                "actual_net_profit": (
                    actual_revenue - actual_food_cost - expenses_by_month[month_key]
                    if actual_cost_complete and expense_recorded else None
                ),
                "predicted_net_profit": None,
                "profit_complete": actual_cost_complete and expense_recorded,
            })
        elif cursor == current_month:
            month_actual = sum(
                int(row["subtotal"] or 0)
                for row in history_rows if row["created_at"].strftime("%Y-%m") == month_key
            )
            results.append({
                "month": month_key,
                "status": "actual_to_date",
                "actual_revenue": month_actual,
                "predicted_revenue": None,
                "actual_net_profit": None,
                "predicted_net_profit": None,
                "profit_complete": False,
            })
        else:
            next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
            days_in_month = calendar.monthrange(cursor.year, cursor.month)[1]
            predicted_revenue = (
                round(sum(weekday_average[date(cursor.year, cursor.month, day).weekday()] for day in range(1, days_in_month + 1)))
                if useable_history else None
            )
            predicted_profit = (
                round(predicted_revenue * (1 - cost_ratio) - estimated_monthly_expense)
                if predicted_revenue is not None
                and cost_ratio is not None
                and cost_complete
                and estimated_monthly_expense is not None
                else None
            )
            results.append({
                "month": month_key,
                "status": "predicted",
                "actual_revenue": None,
                "predicted_revenue": predicted_revenue,
                "actual_net_profit": None,
                "predicted_net_profit": predicted_profit,
                "profit_complete": predicted_profit is not None,
                "expense_basis": "Average recorded expenses over the three preceding complete months" if estimated_monthly_expense is not None else None,
            })
            cursor = next_month
            continue
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    return {
        "start_month": start.strftime("%Y-%m"),
        "end_month": end.strftime("%Y-%m"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "historical_window_days": 90,
        "historical_order_days": history_days,
        "historical_span_days": span_days,
        "historical_paid_revenue": observed_revenue,
        "demo_order_count_in_history": demo_count,
        "months": results,
        "prediction_method": (
            "Revenue uses average actual daily paid sales by weekday over the preceding 90 days. "
            "Net profit is shown only when historical item costs and all three preceding months of recorded operating expenses are available."
        ),
        "revenue_prediction_available": useable_history,
        "revenue_unavailable_reason": None if useable_history else "Insufficient paid sales history: at least 10 sales days spanning 28 days are required.",
        "profit_prediction_available": cost_complete and cost_ratio is not None and estimated_monthly_expense is not None,
        "profit_unavailable_reason": (
            None
            if cost_complete and cost_ratio is not None and estimated_monthly_expense is not None
            else "Net profit forecast requires recorded costs for every historical sold item and operating expenses in each of the three preceding months."
        ),
        "actual_data_note": "Actual revenue is paid order subtotal before tax. Demo/sample orders in the history are included and counted separately.",
    }


def execute_tool(name: str, arguments: dict[str, Any], engine: Engine | None = None) -> dict[str, Any]:
    logger.info("MCP analytics tool invoked: %s", name)
    if name == "get_sales":
        return _sales(arguments["start_date"], arguments["end_date"], engine)
    if name == "get_revenue":
        return _sales(arguments["start_date"], arguments["end_date"], engine)
    if name == "get_profit":
        return _profit(arguments["start_date"], arguments["end_date"], engine)
    if name == "get_orders":
        return _orders(arguments["start_date"], arguments["end_date"], False, engine)
    if name == "get_cancelled_orders":
        return _orders(arguments["start_date"], arguments["end_date"], True, engine)
    if name == "get_food_analytics":
        return _food_analytics(arguments["start_date"], arguments["end_date"], engine)
    if name == "get_inventory":
        return _inventory(engine)
    if name == "get_expenses":
        return _expenses(arguments["start_date"], arguments["end_date"], engine)
    if name == "get_customer_analytics":
        return _customer_analytics(arguments["start_date"], arguments["end_date"], engine)
    if name == "get_employee_attendance":
        return _employee_attendance(arguments["start_date"], arguments["end_date"], engine)
    if name == "forecast_sales":
        return _forecast(arguments["start_month"], arguments["end_month"], engine)
    raise ValueError(f"Unknown analytics tool: {name}")
