import math
import os
import random
from datetime import date, datetime, time as dtime, timedelta
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, insert, func, delete, inspect

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

# Standard item costs for menu items (approx 25% to 38% food cost)
DEFAULT_ITEM_COSTS = {
    "Butter Chicken": 110,
    "Paneer Tikka": 85,
    "Garlic Naan": 18,
    "Tandoori Roti": 8,
    "Dal Makhani": 70,
    "Shahi Paneer": 95,
    "Masala Chaas": 15,
    "Gulab Jamun": 25,
    "Chicken Biryani": 95,
    "Samosa": 14,
    "Mango Lassi": 28,
    "Rasmalai": 38,
    "Idli": 20,
    "Bara": 18,
    "Dosa": 30,
    "Aloo Roti": 20,
    "Sattu Roti": 18,
    "Jalebi": 16,
    "Upma": 22,
    "Veg Thali": 75,
    "Non-Veg Thali": 115,
    "Chicken Masala": 95,
    "Chicken Tikka": 85,
    "Mutton Khassa": 135,
    "Tawa Roti": 6,
    "Plain Naan": 15,
    "Butter Naan": 20,
}

FESTIVAL_EVENTS = [
    # 2025
    {"name": "Diwali Festival", "start": date(2025, 10, 19), "end": date(2025, 10, 23), "uplift": 0.65, "fav_types": ["Desserts", "Thalis", "Main course"]},
    {"name": "Navratri & Dussehra", "start": date(2025, 9, 22), "end": date(2025, 10, 2), "uplift": 0.40, "fav_types": ["Thalis", "Breakfast", "Desserts"]},
    {"name": "Durga Puja", "start": date(2025, 9, 28), "end": date(2025, 10, 2), "uplift": 0.45, "fav_types": ["Main course", "Starters", "Desserts"]},
    {"name": "Christmas & New Year", "start": date(2025, 12, 24), "end": date(2026, 1, 2), "uplift": 0.55, "fav_types": ["Main course", "Starters", "Drinks"]},
    {"name": "Raksha Bandhan", "start": date(2025, 8, 9), "end": date(2025, 8, 10), "uplift": 0.35, "fav_types": ["Desserts", "Thalis"]},
    {"name": "Independence Day", "start": date(2025, 8, 15), "end": date(2025, 8, 15), "uplift": 0.35, "fav_types": ["Thalis", "Starters"]},
    # 2026
    {"name": "Republic Day", "start": date(2026, 1, 26), "end": date(2026, 1, 26), "uplift": 0.35, "fav_types": ["Thalis", "Breakfast"]},
    {"name": "Holi Festival", "start": date(2026, 3, 3), "end": date(2026, 3, 5), "uplift": 0.45, "fav_types": ["Desserts", "Drinks", "Starters"]},
    {"name": "Eid ul-Fitr", "start": date(2026, 3, 19), "end": date(2026, 3, 21), "uplift": 0.50, "fav_types": ["Main course", "Starters", "Desserts"]},
    {"name": "Eid al-Adha", "start": date(2026, 5, 26), "end": date(2026, 5, 28), "uplift": 0.45, "fav_types": ["Main course", "Starters"]},
    {"name": "Raksha Bandhan", "start": date(2026, 8, 28), "end": date(2026, 8, 29), "uplift": 0.35, "fav_types": ["Desserts", "Thalis"]},
    {"name": "Independence Day", "start": date(2026, 8, 15), "end": date(2026, 8, 15), "uplift": 0.35, "fav_types": ["Thalis", "Starters"]},
    {"name": "Navratri & Dussehra", "start": date(2026, 10, 11), "end": date(2026, 10, 21), "uplift": 0.40, "fav_types": ["Thalis", "Breakfast", "Desserts"]},
    {"name": "Durga Puja", "start": date(2026, 10, 17), "end": date(2026, 10, 21), "uplift": 0.45, "fav_types": ["Main course", "Starters", "Desserts"]},
    {"name": "Diwali Festival", "start": date(2026, 11, 6), "end": date(2026, 11, 10), "uplift": 0.70, "fav_types": ["Desserts", "Thalis", "Main course"]},
    {"name": "Christmas & New Year", "start": date(2026, 12, 24), "end": date(2027, 1, 2), "uplift": 0.55, "fav_types": ["Main course", "Starters", "Drinks"]},
    # 2027
    {"name": "Republic Day", "start": date(2027, 1, 26), "end": date(2027, 1, 26), "uplift": 0.35, "fav_types": ["Thalis", "Breakfast"]},
    {"name": "Holi Festival", "start": date(2027, 3, 22), "end": date(2027, 3, 24), "uplift": 0.45, "fav_types": ["Desserts", "Drinks", "Starters"]},
]

POPULAR_MULTIPLIERS = {
    "Chicken Biryani": 3.0,
    "Butter Chicken": 2.8,
    "Paneer Tikka": 2.5,
    "Garlic Naan": 3.5,
    "Butter Naan": 3.0,
    "Tandoori Roti": 2.5,
    "Dal Makhani": 2.2,
    "Veg Thali": 2.4,
    "Non-Veg Thali": 2.2,
    "Gulab Jamun": 2.0,
    "Masala Chaas": 1.8,
    "Mango Lassi": 1.8,
    "Dosa": 1.7,
    "Idli": 1.5,
}

SAMPLE_GUEST_NAMES = [
    "Rahul Sharma", "Pooja Verma", "Amit Patel", "Sneha Rao", "Vikram Singh",
    "Ananya Gupta", "Rohan Mehta", "Priya Nair", "Siddharth Joshi", "Kavita Reddy",
    "Deepak Chopra", "Neha Bansal", "Aditya Mishra", "Swati Kulkarni", "Karan Malhotra",
    "Divya Kapoor", "Manish Tiwari", "Ritu Saxena", "Gaurav Sen", "Meera Bhatt",
]


def populate_menu_costs(connection, menu_items_table):
    """Ensure all menu items have a realistic cost_price."""
    rows = connection.execute(select(menu_items_table.c.id, menu_items_table.c.name, menu_items_table.c.price, menu_items_table.c.cost_price)).mappings().all()
    for row in rows:
        name = row["name"]
        cost = row["cost_price"]
        if cost is None or cost == 0:
            assigned_cost = DEFAULT_ITEM_COSTS.get(name, max(5, int(row["price"] * 0.32)))
            connection.execute(
                menu_items_table.update()
                .where(menu_items_table.c.id == row["id"])
                .values(cost_price=assigned_cost)
            )


def seed_festival_calendar(connection, festival_table):
    """Seed festival calendar entries."""
    existing_count = connection.execute(select(func.count(festival_table.c.id))).scalar()
    if existing_count and existing_count > 0:
        return
    for fest in FESTIVAL_EVENTS:
        connection.execute(
            insert(festival_table).values(
                name=fest["name"],
                start_date=fest["start"],
                end_date=fest["end"],
                uplift_percentage=Decimal(str(round(fest["uplift"] * 100, 2))),
                expense_inflation_percentage=Decimal(str(round(fest["uplift"] * 40, 2))), # higher cost during festival
                description=f"Annual {fest['name']} celebrations and high customer volume window",
            )
        )


def seed_operating_expenses(connection, expenses_table, start_month: date, end_month: date):
    """Seed realistic monthly fixed & operational expenses."""
    existing_months = set(connection.execute(select(expenses_table.c.month).distinct()).scalars().all())
    
    current = start_month.replace(day=1)
    end = end_month.replace(day=1)
    
    # Categories of expenses
    while current <= end:
        month_str = current.strftime("%Y-%m")
        if month_str not in existing_months:
            m = current.month
            is_festival_month = m in (10, 11, 12, 3)
            
            # Base expenses with slight variations
            rent = 35000
            staffing = 52000 if is_festival_month else 46000
            utilities = random.randint(13000, 16000)
            maintenance = random.randint(5500, 8000)
            marketing = random.randint(8000, 12000) if is_festival_month else random.randint(3500, 5000)
            
            expenses = [
                ("rent", rent, "Premises commercial lease"),
                ("staffing", staffing, "Kitchen, service, and cleaning staff salaries" + (" (incl festival bonus/overtime)" if is_festival_month else "")),
                ("utilities", utilities, "Electricity, commercial gas, and water"),
                ("maintenance", maintenance, "Kitchen equipment servicing, repairs, and sanitization"),
                ("marketing", marketing, "Local promotions, menu leaflets, social media advertising"),
            ]
            
            for cat, amt, note in expenses:
                connection.execute(
                    insert(expenses_table).values(
                        month=month_str,
                        category=cat,
                        amount=amt,
                        note=note,
                    )
                )
        # Advance month
        current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)


def generate_synthetic_sales(engine, metadata, force_regenerate: bool = False):
    """
    Generate ~12 months of relationally consistent synthetic sales data.
    Clearly marks records with is_synthetic = TRUE and [DEMO SYNTHETIC] note.
    Preserves all existing real customer and business transactions.
    """
    orders_table = metadata.tables["orders"]
    order_items_table = metadata.tables["order_items"]
    menu_items_table = metadata.tables["menu_items"]
    festival_table = metadata.tables["festival_calendar"]
    expenses_table = metadata.tables["operating_expenses"]
    users_table = metadata.tables["users"]
    customers_table = metadata.tables["customers"]

    with engine.begin() as conn:
        # 1. Menu item costs
        populate_menu_costs(conn, menu_items_table)
        
        # 2. Festival calendar
        seed_festival_calendar(conn, festival_table)
        
        # Check existing synthetic count
        existing_synthetic = conn.execute(
            select(func.count(orders_table.c.id)).where(orders_table.c.is_synthetic == True)
        ).scalar()
        
        # If we already have 1000+ synthetic records and not forced, skip
        if existing_synthetic and existing_synthetic > 1000 and not force_regenerate:
            print(f"Synthetic historical dataset already populated ({existing_synthetic} orders). Skipping generation.")
            return existing_synthetic

        if force_regenerate:
            print("Force regenerating synthetic records: cleaning previous synthetic data...")
            # Delete synthetic orders (cascade deletes order_items)
            conn.execute(delete(orders_table).where(orders_table.c.is_synthetic == True))

        # 3. Seed operating expenses for Nov 2025 - Dec 2026
        seed_operating_expenses(conn, expenses_table, date(2025, 11, 1), date(2026, 12, 1))

        # Retrieve available menu items
        menu_rows = conn.execute(select(menu_items_table)).mappings().all()
        if not menu_rows:
            print("No menu items found. Cannot generate sales.")
            return 0
            
        menu_items_by_id = {row["id"]: row for row in menu_rows}
        item_list = list(menu_rows)
        item_weights = [POPULAR_MULTIPLIERS.get(row["name"], 1.0) for row in item_list]

        # Staff user id for order creation
        staff_id = conn.execute(select(users_table.c.id).where(users_table.c.role == "staff").limit(1)).scalar() or 4
        
        # Customers for optional linking
        cust_ids = conn.execute(select(customers_table.c.id).limit(10)).scalars().all()

        # Date range: 2025-11-01 to 2026-11-13 (today)
        start_date = date(2025, 11, 1)
        end_date = date(2026, 11, 13)
        
        curr_date = start_date
        total_orders_generated = 0
        total_revenue_generated = 0
        total_cost_generated = 0

        random.seed(42) # Reproducible realistic distribution

        print(f"Generating realistic sales data from {start_date} to {end_date}...")
        
        orders_batch = []
        # We will insert orders day by day
        while curr_date <= end_date:
            weekday = curr_date.weekday() # 0 = Monday, 6 = Sunday
            is_weekend = weekday in (4, 5, 6) # Friday, Saturday, Sunday
            
            # Check festival uplift
            fest_match = None
            for fest in FESTIVAL_EVENTS:
                if fest["start"] <= curr_date <= fest["end"]:
                    fest_match = fest
                    break

            # Daily base order volume
            if is_weekend:
                base_volume = random.randint(26, 38)
            else:
                base_volume = random.randint(14, 22)

            if fest_match:
                volume = int(base_volume * (1.0 + fest_match["uplift"]))
            else:
                volume = base_volume

            # Generate orders for this day
            for order_idx in range(volume):
                # Determine order time: Lunch peak (12:30-15:30) vs Dinner peak (19:00-22:45) vs Off-peak
                r_time = random.random()
                if r_time < 0.42:
                    # Lunch rush
                    hour = random.randint(12, 15)
                    minute = random.randint(0, 59)
                elif r_time < 0.88:
                    # Dinner rush
                    hour = random.randint(19, 22)
                    minute = random.randint(0, 59)
                elif r_time < 0.95:
                    # Breakfast / Early
                    hour = random.randint(8, 11)
                    minute = random.randint(0, 59)
                else:
                    # Afternoon tea / snacks
                    hour = random.randint(16, 18)
                    minute = random.randint(0, 59)

                order_time = dtime(hour, minute, random.randint(0, 59))
                order_dt = datetime.combine(curr_date, order_time)

                # Order type: ~55% Dine in, ~30% Takeaway, ~15% Delivery
                r_type = random.random()
                if r_type < 0.55:
                    order_type = "Dine in"
                    table_name = f"Table {random.randint(1, 24):02d}"
                elif r_type < 0.85:
                    order_type = "Takeaway"
                    table_name = None
                else:
                    order_type = "Delivery"
                    table_name = None

                guest_name = random.choice(SAMPLE_GUEST_NAMES) if random.random() < 0.65 else None
                cust_id = random.choice(cust_ids) if cust_ids and random.random() < 0.35 else None

                # Select items for this order: typically 2 to 5 items
                num_items = random.choices([1, 2, 3, 4, 5, 6], weights=[0.1, 0.35, 0.3, 0.15, 0.08, 0.02])[0]
                
                # Bias towards festival favorite types if in festival
                if fest_match and random.random() < 0.5:
                    fav_cands = [it for it in item_list if it["category"] in fest_match["fav_types"]]
                    cands = fav_cands if fav_cands else item_list
                    w = [POPULAR_MULTIPLIERS.get(it["name"], 1.0) for it in cands]
                    chosen_items = random.choices(cands, weights=w, k=num_items)
                else:
                    chosen_items = random.choices(item_list, weights=item_weights, k=num_items)

                # Aggregate quantities for duplicate items in same order
                order_lines = {}
                for it in chosen_items:
                    qty = 1 if it["category"] in ("Main course", "Thalis") else random.choices([1, 2, 3], weights=[0.7, 0.25, 0.05])[0]
                    order_lines[it["id"]] = order_lines.get(it["id"], 0) + qty

                subtotal = 0
                total_cost = 0
                items_data = []
                for item_id, qty in order_lines.items():
                    m_row = menu_items_by_id[item_id]
                    unit_p = m_row["price"]
                    unit_c = m_row["cost_price"] or DEFAULT_ITEM_COSTS.get(m_row["name"], int(unit_p * 0.32))
                    subtotal += unit_p * qty
                    total_cost += unit_c * qty
                    items_data.append({
                        "menu_item_id": item_id,
                        "item_name": m_row["name"],
                        "unit_price": unit_p,
                        "unit_cost": unit_c,
                        "quantity": qty,
                        "prep_status": "delivered",
                    })

                # Discounts: 15% probability of a 5-15% discount
                discount = 0
                if random.random() < 0.15 or (fest_match and random.random() < 0.30):
                    discount_pct = random.choice([0.05, 0.10, 0.15])
                    discount = round(subtotal * discount_pct)

                taxable_amount = max(0, subtotal - discount)
                tax = round(taxable_amount * 0.05)
                total = taxable_amount + tax
                cash_received = math.ceil(total / 100) * 100 if random.random() < 0.6 else total
                change_due = max(0, cash_received - total)

                note_prefix = f"[DEMO SYNTHETIC] {fest_match['name']}" if fest_match else "[DEMO SYNTHETIC]"

                # Insert order record
                res = conn.execute(
                    insert(orders_table).values(
                        order_type=order_type,
                        table_name=table_name,
                        guest_name=guest_name,
                        note=note_prefix,
                        subtotal=subtotal,
                        tax=tax,
                        total=total,
                        cash_received=cash_received,
                        change_due=change_due,
                        created_by=staff_id,
                        customer_id=cust_id,
                        payment_status="paid",
                        discount_amount=discount,
                        created_at=order_dt,
                        is_synthetic=True,
                    )
                )
                order_id = res.inserted_primary_key[0]

                # Insert order items
                for line in items_data:
                    conn.execute(
                        insert(order_items_table).values(
                            order_id=order_id,
                            menu_item_id=line["menu_item_id"],
                            item_name=line["item_name"],
                            unit_price=line["unit_price"],
                            unit_cost=line["unit_cost"],
                            quantity=line["quantity"],
                            prep_status="delivered",
                        )
                    )

                total_orders_generated += 1
                total_revenue_generated += subtotal - discount
                total_cost_generated += total_cost

            curr_date += timedelta(days=1)

        print(f"Generated {total_orders_generated} synthetic orders.")
        print(f"Total Net Sales Revenue: INR {total_revenue_generated:,}")
        print(f"Total Food Ingredient Costs: INR {total_cost_generated:,}")
        print(f"Gross Margin: {round((1 - total_cost_generated / max(1, total_revenue_generated)) * 100, 1)}%")

    return total_orders_generated


if __name__ == "__main__":
    from backend.app import engine, metadata
    generate_synthetic_sales(engine, metadata, force_regenerate=False)
