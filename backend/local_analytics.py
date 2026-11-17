import calendar
import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Callable, Coroutine

logger = logging.getLogger("restaurant.admin_chat.local")

MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def _format_inr(amount: int | float | None) -> str:
    if amount is None:
        return "N/A"
    return f"₹{amount:,.0f}" if isinstance(amount, (int, float)) and amount == int(amount) else f"₹{amount:,.2f}"


def parse_date_range(query: str, default_period: str = "today") -> tuple[str, str, str]:
    today = date.today()
    q = query.casefold()

    iso_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", query)
    if len(iso_dates) >= 2:
        return iso_dates[0], iso_dates[1], f"{iso_dates[0]} to {iso_dates[1]}"
    if len(iso_dates) == 1:
        return iso_dates[0], iso_dates[0], iso_dates[0]

    for name, month_num in MONTH_NAMES.items():
        pattern = rf"\b{name}\b(?:\s+(\d{{4}}))?"
        match = re.search(pattern, q)
        if match:
            year = int(match.group(1)) if match.group(1) else today.year
            last_day = calendar.monthrange(year, month_num)[1]
            start = date(year, month_num, 1)
            end = date(year, month_num, last_day)
            return start.isoformat(), end.isoformat(), f"{name.capitalize()} {year}"

    if "yesterday" in q:
        target = today - timedelta(days=1)
        return target.isoformat(), target.isoformat(), "Yesterday"

    if "last week" in q:
        start_of_last_week = today - timedelta(days=today.weekday() + 7)
        end_of_last_week = start_of_last_week + timedelta(days=6)
        return start_of_last_week.isoformat(), end_of_last_week.isoformat(), "Last Week"

    if "this week" in q:
        start_of_week = today - timedelta(days=today.weekday())
        return start_of_week.isoformat(), today.isoformat(), "This Week"

    if "last month" in q:
        first_of_this_month = today.replace(day=1)
        last_day_of_last_month = first_of_this_month - timedelta(days=1)
        first_of_last_month = last_day_of_last_month.replace(day=1)
        return first_of_last_month.isoformat(), last_day_of_last_month.isoformat(), "Last Month"

    if "this month" in q or default_period == "this_month":
        first_of_this_month = today.replace(day=1)
        return first_of_this_month.isoformat(), today.isoformat(), "This Month"

    if "last year" in q:
        year = today.year - 1
        return f"{year}-01-01", f"{year}-12-31", f"Year {year}"

    if "this year" in q:
        return f"{today.year}-01-01", today.isoformat(), f"Year {today.year}"

    return today.isoformat(), today.isoformat(), "Today"


def parse_month_range(query: str) -> tuple[str, str]:
    today = date.today()
    q = query.casefold()

    explicit_months = re.findall(r"\b\d{4}-\d{2}\b", query)
    if len(explicit_months) >= 2:
        return explicit_months[0], explicit_months[1]
    if len(explicit_months) == 1:
        return today.strftime("%Y-%m"), explicit_months[0]

    found_months: list[str] = []
    for match in re.finditer(r"\b([a-z]+)\s+(\d{4})\b", q):
        month_word, year_str = match.groups()
        if month_word in MONTH_NAMES:
            month_num = MONTH_NAMES[month_word]
            found_months.append(f"{year_str}-{month_num:02d}")

    if len(found_months) >= 2:
        return found_months[0], found_months[1]
    if len(found_months) == 1:
        return today.strftime("%Y-%m"), found_months[0]

    end_month = today.replace(day=1) + timedelta(days=120)
    return today.strftime("%Y-%m"), end_month.strftime("%Y-%m")


def detect_query_intent(query: str) -> str:
    q = query.casefold().strip()

    if any(k in q for k in ["why have sales decreased", "why did sales drop", "why sales decreased", "sales decline", "sales drop", "decrease in sales"]):
        return "sales_decrease"

    if any(k in q for k in ["compare", "vs", "versus", "comparison"]):
        return "sales_compare"

    if any(k in q for k in ["predict", "forecast", "projection", "future sales", "march 2027", "next month"]):
        return "forecast"

    if any(k in q for k in ["attendance", "present", "absent", "who came to work", "employee attendance", "staff attendance"]):
        return "attendance"

    if any(k in q for k in ["food item", "dish", "dishes", "sell the most", "sell most", "best seller", "bestseller", "top seller", "popular dish", "sell the least", "least sold", "category sales"]):
        return "food_analytics"

    if any(k in q for k in ["inventory", "ingredient", "ingredients", "low stock", "running low", "expire", "expiry", "reorder", "shortage", "stock level"]):
        return "inventory"

    if any(k in q for k in ["cancelled order", "cancellation", "why cancelled", "cancelled orders"]):
        return "cancelled_orders"

    if any(k in q for k in ["recent order", "show order", "list order", "today's order", "orders placed"]):
        return "orders"

    if any(k in q for k in ["profit", "margin", "food cost", "gross profit", "net profit"]):
        return "profit"

    if any(k in q for k in ["expense", "expenses", "operating expense", "rent", "bills", "overhead"]):
        return "expenses"

    if any(k in q for k in ["customer", "customers", "repeat", "loyalty", "average order value", "patron"]):
        return "customers"

    if any(k in q for k in ["sale", "sales", "revenue", "income", "turnover", "total sales", "how much made", "how much sold"]):
        return "sales"

    if any(k in q for k in ["help", "what can you do", "features", "options", "commands"]):
        return "help"

    return "general"


async def handle_sales(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    default_period = "this_month" if "month" in query.casefold() else "today"
    start_date, end_date, period_label = parse_date_range(query, default_period=default_period)
    data = await call_tool("get_sales", {"start_date": start_date, "end_date": end_date})

    revenue = data.get("sales_revenue", 0)
    paid_orders = data.get("paid_order_count", 0)
    unpaid_orders = data.get("unpaid_order_count", 0)
    unpaid_total = data.get("unpaid_total", 0)
    cancelled_orders = data.get("cancelled_order_count", 0)
    demo_orders = data.get("demo_order_count", 0)
    daily_sales = data.get("daily_sales", [])

    lines = [
        f"### Sales Summary ({period_label}: {start_date} to {end_date})",
        "",
        f"- **Paid Sales Revenue:** {_format_inr(revenue)}",
        f"- **Paid Orders:** {paid_orders}",
        f"- **Unpaid Orders:** {unpaid_orders} (Total: {_format_inr(unpaid_total)})",
        f"- **Cancelled Orders:** {cancelled_orders}",
    ]

    if demo_orders > 0:
        lines.append(f"- **Demo / Sample Orders:** {demo_orders} included in dataset")

    if len(daily_sales) > 1:
        lines.extend([
            "",
            "**Daily Breakdown:**",
            "",
            "| Date | Paid Sales | Paid Orders |",
            "| :--- | :--- | :--- |",
        ])
        for day in daily_sales[-14:]:
            lines.append(f"| {day['date']} | {_format_inr(day['sales'])} | {day['orders']} |")
        if len(daily_sales) > 14:
            lines.append(f"*(Showing last 14 of {len(daily_sales)} days in range)*")

    lines.extend([
        "",
        "*Note: Sales revenue reflects paid, non-cancelled order subtotals before tax (discounts included).* ",
    ])
    return "\n".join(lines)


async def handle_sales_compare(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    today = date.today()
    q = query.casefold()

    if "yesterday" in q or "today" in q:
        p1_start = (today - timedelta(days=1)).isoformat()
        p1_end = p1_start
        p1_label = "Yesterday"
        p2_start = today.isoformat()
        p2_end = p2_start
        p2_label = "Today"
    else:
        first_of_this_month = today.replace(day=1)
        last_day_of_last_month = first_of_this_month - timedelta(days=1)
        first_of_last_month = last_day_of_last_month.replace(day=1)

        p1_start = first_of_last_month.isoformat()
        p1_end = last_day_of_last_month.isoformat()
        p1_label = f"Last Month ({first_of_last_month.strftime('%b %Y')})"

        p2_start = first_of_this_month.isoformat()
        p2_end = today.isoformat()
        p2_label = f"This Month ({first_of_this_month.strftime('%b %Y')} to date)"

    d1 = await call_tool("get_sales", {"start_date": p1_start, "end_date": p1_end})
    d2 = await call_tool("get_sales", {"start_date": p2_start, "end_date": p2_end})

    rev1, rev2 = d1.get("sales_revenue", 0), d2.get("sales_revenue", 0)
    ord1, ord2 = d1.get("paid_order_count", 0), d2.get("paid_order_count", 0)
    canc1, canc2 = d1.get("cancelled_order_count", 0), d2.get("cancelled_order_count", 0)

    rev_diff = rev2 - rev1
    rev_pct = f"{(rev_diff / rev1 * 100):+.1f}%" if rev1 else "N/A"
    ord_diff = ord2 - ord1
    ord_pct = f"{(ord_diff / ord1 * 100):+.1f}%" if ord1 else "N/A"

    lines = [
        f"### Sales Comparison: {p1_label} vs {p2_label}",
        "",
        f"| Metric | {p1_label} | {p2_label} | Difference |",
        "| :--- | :--- | :--- | :--- |",
        f"| **Sales Revenue** | {_format_inr(rev1)} | {_format_inr(rev2)} | {_format_inr(rev_diff)} ({rev_pct}) |",
        f"| **Paid Orders** | {ord1} | {ord2} | {ord_diff:+d} ({ord_pct}) |",
        f"| **Cancelled Orders** | {canc1} | {canc2} | {canc2 - canc1:+d} |",
        "",
        "*Note: Actual sales revenue is paid order subtotal before tax. Subtotals include recorded item discounts.*",
    ]

    total_demos = d1.get("demo_order_count", 0) + d2.get("demo_order_count", 0)
    if total_demos > 0:
        lines.append(f"*(Includes {total_demos} recorded sample demo orders across both periods)*")

    return "\n".join(lines)


async def handle_sales_decrease(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    today = date.today()
    recent_start = (today - timedelta(days=14)).isoformat()
    recent_end = today.isoformat()
    prior_start = (today - timedelta(days=28)).isoformat()
    prior_end = (today - timedelta(days=15)).isoformat()

    recent_sales = await call_tool("get_sales", {"start_date": recent_start, "end_date": recent_end})
    prior_sales = await call_tool("get_sales", {"start_date": prior_start, "end_date": prior_end})
    cancelled = await call_tool("get_cancelled_orders", {"start_date": recent_start, "end_date": recent_end})

    r_rev = recent_sales.get("sales_revenue", 0)
    p_rev = prior_sales.get("sales_revenue", 0)
    r_orders = recent_sales.get("paid_order_count", 0)
    p_orders = prior_sales.get("paid_order_count", 0)
    c_count = cancelled.get("returned_orders", 0)

    rev_diff = r_rev - p_rev
    pct_change = f"{(rev_diff / p_rev * 100):+.1f}%" if p_rev else "N/A"

    lines = [
        "### Sales Trend & Order Analysis",
        "",
        "Comparing the last 14 days against the preceding 14-day period:",
        "",
        "| Metric | Preceding 14 Days | Last 14 Days | Change |",
        "| :--- | :--- | :--- | :--- |",
        f"| **Paid Revenue** | {_format_inr(p_rev)} | {_format_inr(r_rev)} | {_format_inr(rev_diff)} ({pct_change}) |",
        f"| **Paid Orders** | {p_orders} | {r_orders} | {r_orders - p_orders:+d} |",
        f"| **Cancelled Orders** | {prior_sales.get('cancelled_order_count', 0)} | {c_count} | {c_count - prior_sales.get('cancelled_order_count', 0):+d} |",
        "",
        "**Observed Patterns in the Data:**",
        f"- **Order Volume:** Total paid orders shifted from {p_orders} to {r_orders}.",
        f"- **Cancellations:** {c_count} orders were cancelled during the recent 14-day window.",
    ]

    reasons = [o.get("cancellation_reason") for o in cancelled.get("orders", []) if o.get("cancellation_reason")]
    if reasons:
        top_reason = max(set(reasons), key=reasons.count)
        lines.append(f"- **Top Cancellation Reason:** '{top_reason}' ({reasons.count(top_reason)} instances).")

    demo_count = recent_sales.get("demo_order_count", 0)
    if demo_count > 0:
        lines.append(f"- **Sample Data:** {demo_count} sample demo orders are recorded in the recent window.")

    lines.extend([
        "",
        "> **Important Business Note:**",
        "> Correlation does not prove causation. Changes in restaurant sales can result from weekday/weekend distribution, seasonal events, local festivals, weather, or menu adjustments. The database records show trends in revenue and order volume, but external factors should also be evaluated.",
    ])
    return "\n".join(lines)


async def handle_profit(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    start_date, end_date, period_label = parse_date_range(query, default_period="this_month")
    data = await call_tool("get_profit", {"start_date": start_date, "end_date": end_date})

    revenue = data.get("sales_revenue", 0)
    food_cost = data.get("food_cost", 0)
    gross_profit = data.get("gross_profit")
    operating_expenses = data.get("operating_expenses")
    net_profit = data.get("net_profit")
    is_complete = data.get("profit_complete", False)
    missing_cost_qty = data.get("missing_cost_quantity", 0)
    missing_expense_months = data.get("missing_expense_months", [])

    lines = [
        f"### Profit & Cost Analysis ({period_label}: {start_date} to {end_date})",
        "",
        f"- **Sales Revenue:** {_format_inr(revenue)}",
        f"- **Food / Ingredient Cost:** {_format_inr(food_cost)}",
        f"- **Gross Profit:** {_format_inr(gross_profit) if gross_profit is not None else 'Incomplete (cost records missing)'}",
        f"- **Operating Expenses:** {_format_inr(operating_expenses) if operating_expenses is not None else 'Incomplete / Missing full month records'}",
        f"- **Net Profit:** {_format_inr(net_profit) if net_profit is not None else 'Unavailable (incomplete cost or expense records)'}",
        "",
    ]

    if not is_complete:
        lines.append("**Incomplete Data Notice:**")
        if missing_cost_qty > 0:
            lines.append(f"- {missing_cost_qty} sold item(s) do not have recorded unit costs in the menu database.")
        if missing_expense_months:
            lines.append(f"- Operating expense records are missing for month(s): {', '.join(missing_expense_months)}.")
        lines.append("- As per financial accounting standards, net profit is not estimated when actual costs or expenses are incomplete.")
    else:
        margin = (net_profit / revenue * 100) if revenue else 0
        lines.append(f"**Net Profit Margin:** {margin:.1f}%")

    return "\n".join(lines)


async def handle_food_analytics(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    start_date, end_date, period_label = parse_date_range(query, default_period="this_month")
    data = await call_tool("get_food_analytics", {"start_date": start_date, "end_date": end_date})

    products = data.get("products", [])
    categories = data.get("category_revenue", [])

    if not products:
        return f"No food sales records found for {period_label} ({start_date} to {end_date})."

    lines = [
        f"### Top Selling Menu Items ({period_label}: {start_date} to {end_date})",
        "",
        "| Rank | Dish / Item | Units Sold | Revenue |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for index, item in enumerate(products[:10], start=1):
        lines.append(f"| {index} | **{item['item']}** | {item['units_sold']} | {_format_inr(item['revenue'])} |")

    if categories:
        lines.extend([
            "",
            "### Category Revenue Breakdown",
            "",
            "| Category | Total Revenue |",
            "| :--- | :--- |",
        ])
        for cat in categories:
            lines.append(f"| {cat['category']} | {_format_inr(cat['revenue'])} |")

    lines.extend([
        "",
        "*Based strictly on paid, non-cancelled order records.*",
    ])
    return "\n".join(lines)


async def handle_inventory(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    data = await call_tool("get_inventory", {})
    ingredients_list = data.get("ingredients", [])
    low_stock_count = data.get("low_stock_count", 0)

    low_stock_items = [item for item in ingredients_list if item.get("low_stock")]

    lines = ["### Restaurant Inventory Status", ""]

    if low_stock_count > 0:
        lines.extend([
            f"⚠️ **Attention: {low_stock_count} ingredient(s) are running low!**",
            "",
            "| Ingredient | Current Stock | Minimum Required | Unit | Status |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])
        for item in low_stock_items:
            lines.append(
                f"| **{item['ingredient']}** | {item['quantity']} | {item['minimum_quantity']} | {item['unit']} | **Low Stock** |"
            )
        lines.extend(["", "Please arrange purchase orders for the low-stock ingredients."])
    else:
        lines.extend([
            "✅ **All ingredients are adequately stocked.** There are currently **0** low-stock items.",
            "",
            "| Ingredient | Current Stock | Minimum Threshold | Unit |",
            "| :--- | :--- | :--- | :--- |",
        ])
        for item in ingredients_list[:12]:
            lines.append(
                f"| {item['ingredient']} | {item['quantity']} | {item['minimum_quantity']} | {item['unit']} |"
            )
        if len(ingredients_list) > 12:
            lines.append(f"*(Showing 12 of {len(ingredients_list)} total inventory ingredients)*")

    expiring = [item for item in ingredients_list if item.get("expires_at")]
    if expiring:
        lines.extend([
            "",
            "**Upcoming Expiries:**",
            *(f"- **{item['ingredient']}:** expires on {item['expires_at']}" for item in expiring[:5]),
        ])

    return "\n".join(lines)


async def handle_forecast(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    start_month, end_month = parse_month_range(query)
    data = await call_tool("forecast_sales", {"start_month": start_month, "end_month": end_month})

    months = data.get("months", [])
    rev_available = data.get("revenue_prediction_available", False)
    profit_available = data.get("profit_prediction_available", False)
    profit_reason = data.get("profit_unavailable_reason")
    demo_count = data.get("demo_order_count_in_history", 0)

    lines = [
        f"### Revenue & Profit Forecast ({start_month} to {end_month})",
        "",
        "| Month | Status | Revenue | Net Profit | Notes |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for m in months:
        status_label = "Actual to date" if m["status"] == "actual_to_date" else "Estimated"
        rev_val = _format_inr(m.get("actual_revenue") or m.get("predicted_revenue"))
        profit_val = _format_inr(m.get("actual_net_profit") or m.get("predicted_net_profit"))
        if profit_val == "N/A":
            profit_val = "Unavailable"

        notes = "Recorded sales" if m["status"] == "actual_to_date" else "90-day weekday trend"
        lines.append(f"| {m['month']} | {status_label} | {rev_val} | {profit_val} | {notes} |")

    lines.extend([
        "",
        "**Forecast Methodology & Disclosures:**",
        f"- **Revenue Prediction:** {'Available based on 90-day historical weekday patterns.' if rev_available else 'Unavailable due to insufficient sales history.'}",
        f"- **Net Profit Prediction:** {profit_reason or ('Available' if profit_available else 'Unavailable')}",
    ])

    if demo_count > 0:
        lines.append(f"- **Sample Data:** {demo_count} sample demo orders in history are included in the baseline calculations.")

    lines.append("- **Estimate Disclaimer:** Forecasts are statistical approximations and do not guarantee future revenue.")

    return "\n".join(lines)


async def handle_cancelled_orders(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    start_date, end_date, period_label = parse_date_range(query, default_period="this_month")
    data = await call_tool("get_cancelled_orders", {"start_date": start_date, "end_date": end_date})

    returned_orders = data.get("returned_orders", 0)
    orders_list = data.get("orders", [])

    if returned_orders == 0:
        return f"### Cancelled Orders ({period_label}: {start_date} to {end_date})\n\n✅ Great news! There are **0 cancelled orders** recorded in this period."

    lines = [
        f"### Cancelled Orders ({period_label}: {start_date} to {end_date})",
        "",
        f"Total cancelled orders recorded: **{returned_orders}**",
        "",
        "| Order ID | Date & Time | Amount | Reason |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for o in orders_list[:15]:
        reason = o.get("cancellation_reason") or "Not specified"
        lines.append(f"| #{o['id']} | {o['created_at']} | {_format_inr(o['total'])} | {reason} |")

    if returned_orders > 15:
        lines.append(f"*(Showing 15 of {returned_orders} total cancellations)*")

    return "\n".join(lines)


async def handle_orders(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    start_date, end_date, period_label = parse_date_range(query, default_period="today")
    data = await call_tool("get_orders", {"start_date": start_date, "end_date": end_date})

    orders_list = data.get("orders", [])
    returned_orders = data.get("returned_orders", 0)

    if not orders_list:
        return f"### Orders ({period_label}: {start_date} to {end_date})\n\nNo orders found for this period."

    lines = [
        f"### Orders Overview ({period_label}: {start_date} to {end_date})",
        "",
        f"Total orders: **{returned_orders}**",
        "",
        "| Order ID | Time | Type | Status | Payment | Total | Items |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for o in orders_list[:10]:
        items_summary = ", ".join(f"{it['quantity']}x {it['item']}" for it in o.get("items", [])[:3])
        if len(o.get("items", [])) > 3:
            items_summary += "…"
        lines.append(
            f"| #{o['id']} | {o['created_at'][11:16]} | {o['order_type']} | {o['order_status']} | {o['payment_status']} | {_format_inr(o['total'])} | {items_summary} |"
        )

    if returned_orders > 10:
        lines.append(f"*(Showing 10 of {returned_orders} orders)*")

    return "\n".join(lines)


async def handle_expenses(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    start_date, end_date, period_label = parse_date_range(query, default_period="this_month")
    data = await call_tool("get_expenses", {"start_date": start_date, "end_date": end_date})

    monthly_totals = data.get("monthly_totals", [])
    expenses_list = data.get("expenses", [])

    if not expenses_list:
        return f"### Operating Expenses\n\nNo operating expenses recorded for {period_label} ({start_date} to {end_date})."

    lines = [
        f"### Operating Expenses ({period_label})",
        "",
        "| Month | Category | Amount | Note |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for exp in expenses_list:
        note = exp.get("note") or "—"
        lines.append(f"| {exp['month']} | {exp['category'].capitalize()} | {_format_inr(exp['amount'])} | {note} |")

    if monthly_totals:
        lines.extend([
            "",
            "**Monthly Totals:**",
            *(f"- **{m['month']}:** {_format_inr(m['amount'])}" for m in monthly_totals),
        ])

    return "\n".join(lines)


async def handle_customers(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    start_date, end_date, period_label = parse_date_range(query, default_period="this_month")
    data = await call_tool("get_customer_analytics", {"start_date": start_date, "end_date": end_date})

    lines = [
        f"### Customer & Loyalty Analytics ({period_label}: {start_date} to {end_date})",
        "",
        f"- **Unique Paying Customers:** {data.get('unique_paying_customers', 0)}",
        f"- **Repeat Customers:** {data.get('repeat_customers', 0)}",
        f"- **New Customer Accounts:** {data.get('new_customer_accounts', 0)}",
        f"- **Total Paid Orders:** {data.get('paid_order_count', 0)}",
        f"- **Average Paid Order Value:** {_format_inr(data.get('average_paid_order_value'))}",
        f"- **Total Customer Sales Revenue:** {_format_inr(data.get('sales_revenue', 0))}",
        "",
        "*Privacy Policy: Aggregated metrics only. Customer names and contact details are never disclosed.*",
    ]
    return "\n".join(lines)


async def handle_attendance(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    start_date, end_date, _ = parse_date_range(query, default_period="today")
    data = await call_tool("get_employee_attendance", {"start_date": start_date, "end_date": end_date})
    reason = data.get("reason", "Employee attendance is not tracked in the current database.")
    return f"### Employee Attendance\n\n**Status: Unavailable**\n\n{reason}\n\n*To enable attendance tracking, configure a supported employee attendance schema.*"


def handle_help() -> str:
    return """### Restaurant Business Assistant
I can answer questions directly using your restaurant's live business records:

- 📊 **Sales & Revenue:** "What are today's total sales?", "Compare this month's sales with last month."
- 🍲 **Menu & Dishes:** "Which food items sell the most?", "Show category sales."
- 📦 **Inventory:** "Which ingredients are running low?", "Show current stock."
- 📈 **Predictions:** "Predict revenue and profit until March 2027.", "Show sales forecast."
- 📉 **Trend Analysis:** "Why have sales decreased?"
- 💰 **Profit & Costs:** "What is our profit this month?", "Food cost analysis."
- 🧾 **Orders:** "Show recent orders", "Show cancelled orders and reasons."
- 👥 **Customers:** "Customer analytics", "Repeat customer count."
- 🏢 **Expenses:** "Show operating expenses this month."

Feel free to ask any question about your restaurant records!"""


async def handle_general(query: str, call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> str:
    today_str = date.today().isoformat()
    sales_data = await call_tool("get_sales", {"start_date": today_str, "end_date": today_str})
    inv_data = await call_tool("get_inventory", {})

    lines = [
        f"### Restaurant Status Overview (Today: {today_str})",
        "",
        f"- **Today's Paid Sales:** {_format_inr(sales_data.get('sales_revenue', 0))} across {sales_data.get('paid_order_count', 0)} order(s).",
        f"- **Inventory Alerts:** {inv_data.get('low_stock_count', 0)} item(s) currently low in stock.",
        "",
        "How can I help you today? You can ask about:",
        "- **Sales & Comparisons:** *'Compare this month with last month'*",
        "- **Top Dishes:** *'Which food items sell the most?'*",
        "- **Inventory:** *'Which ingredients are running low?'*",
        "- **Forecasts:** *'Predict revenue and profit until March 2027'*",
        "- **Analysis:** *'Why have sales decreased?'*",
    ]
    return "\n".join(lines)


async def answer_with_local_analytics(
    call_tool: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]],
    query: str,
) -> str:
    intent = detect_query_intent(query)
    logger.info("Local analytics intent detected: %s for query: %s", intent, query[:60])

    if intent == "help":
        return handle_help()
    if intent == "sales_decrease":
        return await handle_sales_decrease(query, call_tool)
    if intent == "sales_compare":
        return await handle_sales_compare(query, call_tool)
    if intent == "forecast":
        return await handle_forecast(query, call_tool)
    if intent == "food_analytics":
        return await handle_food_analytics(query, call_tool)
    if intent == "inventory":
        return await handle_inventory(query, call_tool)
    if intent == "profit":
        return await handle_profit(query, call_tool)
    if intent == "cancelled_orders":
        return await handle_cancelled_orders(query, call_tool)
    if intent == "orders":
        return await handle_orders(query, call_tool)
    if intent == "expenses":
        return await handle_expenses(query, call_tool)
    if intent == "customers":
        return await handle_customers(query, call_tool)
    if intent == "attendance":
        return await handle_attendance(query, call_tool)
    if intent == "sales":
        return await handle_sales(query, call_tool)

    return await handle_general(query, call_tool)
