import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
import urllib.parse
import calendar
import csv
import io
from contextlib import asynccontextmanager, suppress
from datetime import date, datetime, time as datetime_time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Date,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    URL,
    Column,
    UniqueConstraint,
    JSON,
    create_engine,
    delete,
    func,
    insert,
    inspect,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

SESSION_TTL_SECONDS = 60 * 60 * 12
logger = logging.getLogger("restaurant.api")
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

SEED_MENU = [
    (1, "Butter Chicken", "Main course", 320, "Creamy tomato curry", True, "photo-1603894584373-5ac82b2ae398"),
    (2, "Paneer Tikka", "Starters", 260, "Charred, smoky & tender", True, "photo-1567188040759-fb8a883dc6d8"),
    (3, "Garlic Naan", "Breads", 65, "Fresh from the tandoor", False, "https://upload.wikimedia.org/wikipedia/commons/0/0d/Garlic_Naan.JPG"),
    (4, "Tandoori Roti", "Breads", 35, "Whole wheat · tandoor baked", False, "https://upload.wikimedia.org/wikipedia/commons/8/8e/Tandoori_Roti-MB54.jpg"),
    (5, "Dal Makhani", "Main course", 240, "Slow-cooked overnight", True, "https://upload.wikimedia.org/wikipedia/commons/4/4d/Creamy_Lentils_%28Dal_Makhani%29_%282239000538%29.jpg"),
    (6, "Shahi Paneer", "Main course", 290, "Paneer in a rich cashew gravy", False, "photo-1631452180519-c014fe946bc7"),
    (7, "Masala Chaas", "Drinks", 60, "Chilled spiced buttermilk", False, "https://upload.wikimedia.org/wikipedia/commons/2/2e/Masala_chaas.JPG"),
    (8, "Gulab Jamun", "Desserts", 90, "Two warm, syrupy bites", False, "https://upload.wikimedia.org/wikipedia/commons/2/29/Gulab_Jamun_1.jpg"),
    (9, "Chicken Biryani", "Main course", 280, "Fragrant basmati rice with spiced chicken", True, "https://upload.wikimedia.org/wikipedia/commons/5/5b/Chicken_biriyani-_My_cafe_restaurant_-_Meghalaya_DSC_009.jpg"),
    (10, "Samosa", "Starters", 50, "Crisp pastry filled with spiced potatoes", False, "https://upload.wikimedia.org/wikipedia/commons/e/ed/Samosa_4.jpg"),
    (11, "Mango Lassi", "Drinks", 95, "Chilled yogurt blended with ripe mango", False, "https://upload.wikimedia.org/wikipedia/commons/4/4e/Mango_Lassi_.jpg"),
    (12, "Rasmalai", "Desserts", 120, "Soft cottage-cheese dumplings in saffron milk", False, "https://upload.wikimedia.org/wikipedia/commons/1/10/Rasmalai_3.jpg"),
    (13, "Idli", "Breakfast", 80, "Soft steamed idlis served with sambar", False, "https://upload.wikimedia.org/wikipedia/commons/0/02/Idli_Sambar-Noida-UP-SP004.jpg"),
    (14, "Bara", "Breakfast", 70, "Traditional lentil bara with yogurt", False, "https://upload.wikimedia.org/wikipedia/commons/e/e9/Dhai_bara.jpg"),
    (15, "Dosa", "Breakfast", 110, "Crisp dosa served with chutney and sambar", True, "https://upload.wikimedia.org/wikipedia/commons/6/64/Dosa_with_Chutney_and_Sambhar.jpg"),
    (16, "Aloo Roti", "Breakfast", 70, "Whole-wheat roti stuffed with spiced potato", False, "https://upload.wikimedia.org/wikipedia/commons/e/e9/Aloo_Paratha_2.jpg"),
    (17, "Sattu Roti", "Breakfast", 60, "Bihar-style roti filled with seasoned sattu", False, "https://upload.wikimedia.org/wikipedia/commons/8/8e/Tandoori_Roti-MB54.jpg"),
    (18, "Jalebi", "Breakfast", 60, "Crisp, syrup-soaked jalebi", False, "https://upload.wikimedia.org/wikipedia/commons/8/85/Jalebi-an_Indian_sweetdish.jpg"),
    (19, "Upma", "Breakfast", 80, "Savory semolina upma with vegetables", False, "https://upload.wikimedia.org/wikipedia/commons/0/09/Upma_South_India.JPG"),
    (20, "Veg Thali", "Thalis", 220, "A complete vegetarian meal with seasonal sides", True, "photo-1546833999-b9f581a1996d"),
    (21, "Non-Veg Thali", "Thalis", 320, "A complete meal with chicken curry and sides", True, "https://upload.wikimedia.org/wikipedia/commons/5/5b/Chicken_biriyani-_My_cafe_restaurant_-_Meghalaya_DSC_009.jpg"),
    (22, "Chicken Masala", "Main course", 280, "Chicken simmered in a rich spiced masala gravy", False, "https://upload.wikimedia.org/wikipedia/commons/4/44/Chicken_Tikka_Masala_KellySue.JPG"),
    (23, "Chicken Tikka", "Starters", 260, "Chargrilled chicken marinated with Indian spices", True, "https://upload.wikimedia.org/wikipedia/commons/9/9d/Chicken-Tikka.jpg"),
    (24, "Mutton Khassa", "Main course", 360, "Slow-cooked mutton in a traditional spiced curry", False, "https://upload.wikimedia.org/wikipedia/commons/f/f2/Indian_mutton_Curry.JPG"),
    (25, "Tawa Roti", "Breads", 25, "Whole-wheat roti cooked on a hot tawa", False, "https://upload.wikimedia.org/wikipedia/commons/5/5c/Tawa_Roti.JPG"),
    (26, "Plain Naan", "Breads", 55, "Soft, freshly baked plain naan", False, "https://upload.wikimedia.org/wikipedia/commons/b/b8/Plain_Naan.jpg"),
    (27, "Butter Naan", "Breads", 70, "Freshly baked naan brushed with butter", False, "https://upload.wikimedia.org/wikipedia/commons/2/29/Butter_Naan_2.jpg"),
]
LEGACY_MENU_IMAGES = {
    "Garlic Naan": ("photo-1608219992759-8d74ed8d76eb",),
    "Tandoori Roti": ("photo-1626074353765-517a681e40be",),
    "Dal Makhani": ("photo-1546833999-b9f581a1996d",),
    "Masala Chaas": (
        "photo-1556679343-c7306c1976bc",
        "https://upload.wikimedia.org/wikipedia/commons/8/8f/Masala_Buttermilk.JPG",
    ),
    "Upma": ("photo-1546833999-b9f581a1996d",),
    "Gulab Jamun": ("photo-1666190094760-ccf9a4f3e7d4",),
    "Butter Naan": (
        "https://upload.wikimedia.org/wikipedia/commons/8/8f/Butter_Naan_with_three_different_Indian_curry.jpg",
    ),
}

metadata = MetaData()
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(80), nullable=False, unique=True),
    Column("display_name", String(120), nullable=False),
    Column("role", String(16), nullable=False),
    Column("employee_type", String(16), nullable=False, server_default="reception"),
    Column("password_hash", String(256), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default="1"),
    CheckConstraint("role IN ('admin', 'staff')", name="ck_users_role"),
)
sessions = Table(
    "sessions",
    metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("expires_at", Integer, nullable=False),
    Index("ix_sessions_expires_at", "expires_at"),
)
customers = Table(
    "customers",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(80), nullable=False, unique=True),
    Column("display_name", String(120), nullable=False),
    Column("email", String(254), unique=True),
    Column("password_hash", String(256), nullable=False),
    Column("loyalty_points", Integer, nullable=False, server_default="0"),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("is_active", Boolean, nullable=False, server_default="1"),
)
customer_preferences = Table(
    "customer_preferences",
    metadata,
    Column("customer_id", Integer, ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True),
    Column("dietary_preferences", JSON),
    Column("updated_at", DateTime, nullable=False, server_default=func.current_timestamp()),
)
customer_sessions = Table(
    "customer_sessions",
    metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("customer_id", Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
    Column("expires_at", Integer, nullable=False),
    Index("ix_customer_sessions_expires_at", "expires_at"),
)
restaurant_tables = Table(
    "restaurant_tables",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("table_number", String(60), nullable=False, unique=True),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("is_active", Boolean, nullable=False, server_default="1"),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
)
ingredients = Table(
    "ingredients",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(120), nullable=False, unique=True),
    Column("unit", String(24), nullable=False),
    Column("quantity", Numeric(12, 3), nullable=False, server_default="0"),
    Column("minimum_quantity", Numeric(12, 3), nullable=False, server_default="0"),
    Column("expires_at", Date),
    Column("updated_at", DateTime, nullable=False, server_default=func.current_timestamp()),
)
recipe_ingredients = Table(
    "recipe_ingredients",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("menu_item_id", Integer, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False),
    Column("ingredient_id", Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False),
    Column("quantity_per_item", Numeric(12, 3), nullable=False),
    UniqueConstraint("menu_item_id", "ingredient_id", name="uq_recipe_menu_ingredient"),
)
inventory_transactions = Table(
    "inventory_transactions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ingredient_id", Integer, ForeignKey("ingredients.id"), nullable=False),
    Column("order_id", Integer, ForeignKey("orders.id", ondelete="SET NULL")),
    Column(
        "order_item_id",
        Integer,
        ForeignKey(
            "order_items.id",
            ondelete="SET NULL",
            name="fk_inventory_transaction_order_item",
        ),
    ),
    Column("quantity_delta", Numeric(12, 3), nullable=False),
    Column("reason", String(160), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Index("ix_inventory_transactions_created_at", "created_at"),
    Index("ix_inventory_transactions_order_item", "order_item_id"),
)
loyalty_transactions = Table(
    "loyalty_transactions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer_id", Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
    Column("order_id", Integer, ForeignKey("orders.id", ondelete="SET NULL")),
    Column("points_delta", Integer, nullable=False),
    Column("reason", String(80), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    UniqueConstraint("order_id", "reason", name="uq_loyalty_order_reason"),
    Index("ix_loyalty_customer_created", "customer_id", "created_at"),
)
chat_messages = Table(
    "chat_messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer_id", Integer, ForeignKey("customers.id", ondelete="SET NULL")),
    Column("question", Text, nullable=False),
    Column("answer", Text, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Index("ix_chat_messages_customer_created", "customer_id", "created_at"),
)
menu_items = Table(
    "menu_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(120), nullable=False),
    Column("category", String(60), nullable=False),
    Column("price", Integer, nullable=False),
    Column("cost_price", Integer),
    Column("description", String(300), nullable=False, server_default=""),
    Column("popular", Integer, nullable=False, server_default="0"),
    Column("image", String(120), nullable=False, server_default="photo-1546833999-b9f581a1996d"),
    Column("ingredients_text", Text, nullable=False, default=""),
    Column("allergens_text", Text, nullable=False, default=""),
    Column("dietary_tags", JSON),
    Column("dietary_verified", Boolean, nullable=False, server_default="0"),
    Column("spice_level", Integer),
    Column("calories", Integer),
    CheckConstraint("price > 0", name="ck_menu_items_price_positive"),
    CheckConstraint("cost_price IS NULL OR cost_price >= 0", name="ck_menu_items_cost_nonnegative"),
)
orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("order_type", String(16), nullable=False),
    Column("table_name", String(60)),
    Column("guest_name", String(120)),
    Column("note", String(500), nullable=False, server_default=""),
    Column("subtotal", Integer, nullable=False),
    Column("tax", Integer, nullable=False),
    Column("total", Integer, nullable=False),
    Column("cash_received", Integer, nullable=False),
    Column("change_due", Integer, nullable=False),
    Column("created_by", Integer, ForeignKey("users.id")),
    Column("customer_id", Integer, ForeignKey("customers.id", ondelete="SET NULL")),
    Column("payment_status", String(16), nullable=False, server_default="paid"),
    Column("discount_amount", Integer, nullable=False, server_default="0"),
    Column("order_status", String(16), nullable=False, server_default="active"),
    Column("cancellation_reason", String(500)),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("is_synthetic", Boolean, nullable=False, server_default="0"),
    CheckConstraint("order_type IN ('Dine in', 'Takeaway', 'Delivery')", name="ck_orders_type"),
    Index("ix_orders_created_at", "created_at"),
    Index("ix_orders_synthetic", "is_synthetic"),
)
order_items = Table(
    "order_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("order_id", Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
    Column("menu_item_id", Integer, ForeignKey("menu_items.id", ondelete="SET NULL")),
    Column("item_name", String(120), nullable=False),
    Column("unit_price", Integer, nullable=False),
    Column("unit_cost", Integer),
    Column("quantity", Integer, nullable=False),
    Column("prep_status", String(16), nullable=False, server_default="queued"),
    CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
    CheckConstraint("unit_cost IS NULL OR unit_cost >= 0", name="ck_order_items_cost_nonnegative"),
    Index("ix_order_items_order_id", "order_id"),
)
table_reservations = Table(
    "table_reservations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer_id", Integer, ForeignKey("customers.id", ondelete="SET NULL")),
    Column("guest_name", String(120), nullable=False),
    Column("contact_phone", String(32), nullable=False),
    Column("party_size", Integer, nullable=False),
    Column("reservation_date", Date, nullable=False),
    Column("reservation_time", String(16), nullable=False),
    Column("table_number", String(60)),
    Column("special_requests", String(500), nullable=False, server_default=""),
    Column("status", String(20), nullable=False, server_default="confirmed"),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    CheckConstraint("status IN ('confirmed', 'seated', 'completed', 'cancelled')", name="ck_reservation_status"),
    Index("ix_reservations_date", "reservation_date"),
)
festival_calendar = Table(
    "festival_calendar",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(100), nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("uplift_percentage", Numeric(5, 2), nullable=False, server_default="20.00"),
    Column("expense_inflation_percentage", Numeric(5, 2), nullable=False, server_default="10.00"),
    Column("description", String(300), nullable=False, server_default=""),
    Index("ix_festival_dates", "start_date", "end_date"),
)
operating_expenses = Table(
    "operating_expenses",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("month", String(7), nullable=False),
    Column("category", String(60), nullable=False),
    Column("amount", Integer, nullable=False),
    Column("note", String(255), nullable=False, server_default=""),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Index("ix_operating_expenses_month", "month"),
)
sales_forecasts = Table(
    "sales_forecasts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("target_month", String(7), nullable=False),
    Column("generated_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("model_name", String(60), nullable=False),
    Column("predicted_revenue", Integer, nullable=False),
    Column("predicted_profit", Integer, nullable=False),
    Column("confidence_min_revenue", Integer, nullable=False),
    Column("confidence_max_revenue", Integer, nullable=False),
    Column("confidence_min_profit", Integer, nullable=False),
    Column("confidence_max_profit", Integer, nullable=False),
    Column("actual_revenue", Integer),
    Column("actual_profit", Integer),
    Column("is_current_month", Boolean, nullable=False, server_default="0"),
    Index("ix_sales_forecasts_month", "target_month"),
)
forecasting_model_metrics = Table(
    "forecasting_model_metrics",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("model_name", String(60), nullable=False),
    Column("evaluation_date", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("mae", Numeric(12, 2), nullable=False),
    Column("rmse", Numeric(12, 2), nullable=False),
    Column("mape", Numeric(6, 2), nullable=False),
    Column("selected_as_best", Boolean, nullable=False, server_default="0"),
    Column("details", JSON),
)


def create_database_engine() -> Engine:
    database_url = os.environ.get("RESTAURANT_DATABASE_URL")
    if database_url:
        return create_engine(database_url, pool_pre_ping=True)
    return create_engine(
        URL.create(
            "mysql+pymysql",
            username=os.environ.get("MYSQL_USER", "root"),
            password=os.environ.get("MYSQL_PASSWORD"),
            host=os.environ.get("MYSQL_HOST", "localhost"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            database=os.environ.get("MYSQL_DATABASE", "restaurant_db"),
            query={"charset": "utf8mb4"},
        ),
        pool_pre_ping=True,
    )


engine = create_database_engine()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Saffron & Stone API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def hash_password(password: str, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=actual_salt, n=2**14, r=8, p=1)
    return f"{actual_salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, digest_hex = stored_hash.split(":", maxsplit=1)
    actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(actual.hex(), digest_hex)


def initialize_database() -> None:
    metadata.create_all(engine)
    with engine.begin() as connection:
        if "is_active" not in {column["name"] for column in inspect(connection).get_columns("users")}:
            connection.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"
            )
        user_columns = {column["name"] for column in inspect(connection).get_columns("users")}
        if "employee_type" not in user_columns:
            connection.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN employee_type VARCHAR(16) NOT NULL DEFAULT 'reception'"
            )
        menu_columns = {column["name"] for column in inspect(connection).get_columns("menu_items")}
        if "cost_price" not in menu_columns:
            connection.exec_driver_sql("ALTER TABLE menu_items ADD COLUMN cost_price INTEGER NULL")
        text_definitions = (
            ("TEXT NULL" if engine.dialect.name == "mysql" else "TEXT NOT NULL DEFAULT ''")
        )
        for column_name, definition in (
            ("ingredients_text", text_definitions),
            ("allergens_text", text_definitions),
            ("dietary_tags", "JSON NULL"),
            ("dietary_verified", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("spice_level", "INTEGER NULL"),
            ("calories", "INTEGER NULL"),
        ):
            if column_name not in menu_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE menu_items ADD COLUMN {column_name} {definition}"
                )
        if engine.dialect.name == "mysql":
            connection.exec_driver_sql(
                "UPDATE menu_items SET ingredients_text = '' WHERE ingredients_text IS NULL"
            )
            connection.exec_driver_sql(
                "UPDATE menu_items SET allergens_text = '' WHERE allergens_text IS NULL"
            )
            connection.exec_driver_sql(
                "ALTER TABLE menu_items "
                "MODIFY COLUMN ingredients_text TEXT NOT NULL, "
                "MODIFY COLUMN allergens_text TEXT NOT NULL"
            )
        order_columns = {column["name"]: column for column in inspect(connection).get_columns("orders")}
        if "customer_id" not in order_columns:
            connection.exec_driver_sql("ALTER TABLE orders ADD COLUMN customer_id INTEGER NULL")
            if engine.dialect.name == "mysql":
                connection.exec_driver_sql(
                    "ALTER TABLE orders ADD CONSTRAINT fk_orders_customer "
                    "FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE SET NULL"
                )
        if "payment_status" not in order_columns:
            connection.exec_driver_sql(
                "ALTER TABLE orders ADD COLUMN payment_status VARCHAR(16) NOT NULL DEFAULT 'paid'"
            )
        if "discount_amount" not in order_columns:
            connection.exec_driver_sql(
                "ALTER TABLE orders ADD COLUMN discount_amount INTEGER NOT NULL DEFAULT 0"
            )
        if "order_status" not in order_columns:
            connection.exec_driver_sql(
                "ALTER TABLE orders ADD COLUMN order_status VARCHAR(16) NOT NULL DEFAULT 'active'"
            )
        if "cancellation_reason" not in order_columns:
            connection.exec_driver_sql(
                "ALTER TABLE orders ADD COLUMN cancellation_reason VARCHAR(500) NULL"
            )
        if "created_by" in order_columns and not order_columns["created_by"]["nullable"]:
            if engine.dialect.name == "mysql":
                connection.exec_driver_sql("ALTER TABLE orders MODIFY COLUMN created_by INT NULL")
        order_item_columns = {column["name"] for column in inspect(connection).get_columns("order_items")}
        if "unit_cost" not in order_item_columns:
            connection.exec_driver_sql("ALTER TABLE order_items ADD COLUMN unit_cost INTEGER NULL")
        if "prep_status" not in order_item_columns:
            connection.exec_driver_sql(
                "ALTER TABLE order_items ADD COLUMN prep_status VARCHAR(16) NOT NULL DEFAULT 'queued'"
            )
        inventory_columns = {
            column["name"] for column in inspect(connection).get_columns("inventory_transactions")
        }
        if "order_item_id" not in inventory_columns:
            connection.exec_driver_sql(
                "ALTER TABLE inventory_transactions ADD COLUMN order_item_id INTEGER NULL"
            )
        inventory_indexes = {
            index["name"] for index in inspect(connection).get_indexes("inventory_transactions")
        }
        if "ix_inventory_transactions_order_item" not in inventory_indexes:
            connection.exec_driver_sql(
                "CREATE INDEX ix_inventory_transactions_order_item "
                "ON inventory_transactions (order_item_id)"
            )
        if engine.dialect.name == "mysql":
            inventory_foreign_keys = {
                foreign_key["name"] for foreign_key in inspect(connection).get_foreign_keys("inventory_transactions")
            }
            if "fk_inventory_transaction_order_item" not in inventory_foreign_keys:
                connection.exec_driver_sql(
                    "ALTER TABLE inventory_transactions "
                    "ADD CONSTRAINT fk_inventory_transaction_order_item "
                    "FOREIGN KEY (order_item_id) REFERENCES order_items (id) ON DELETE SET NULL"
                )
        today_start = datetime.combine(date.today(), datetime_time.min)
        connection.execute(
            update(order_items)
            .where(
                order_items.c.prep_status == "queued",
                order_items.c.order_id.in_(
                    select(orders.c.id).where(orders.c.created_at < today_start)
                ),
            )
            .values(prep_status="ready")
        )
        for legacy_username in ("admin", "staff", "restaurant_admin", "restaurant_staff"):
            legacy_user_id = connection.execute(
                select(users.c.id).where(users.c.username == legacy_username)
            ).scalar_one_or_none()
            if legacy_user_id is None:
                continue
            connection.execute(delete(sessions).where(sessions.c.user_id == legacy_user_id))
            has_orders = connection.execute(
                select(orders.c.id).where(orders.c.created_by == legacy_user_id).limit(1)
            ).first()
            if has_orders:
                connection.execute(
                    update(users).where(users.c.id == legacy_user_id).values(is_active=False)
                )
            else:
                connection.execute(delete(users).where(users.c.id == legacy_user_id))
        for item in SEED_MENU:
            existing_item = connection.execute(
                select(menu_items.c.id, menu_items.c.name, menu_items.c.image)
                .where(menu_items.c.id == item[0])
            ).mappings().first()
            if existing_item is not None and existing_item["name"] != item[1]:
                existing_item = connection.execute(
                    select(menu_items.c.id, menu_items.c.name, menu_items.c.image)
                    .where(menu_items.c.name == item[1])
                ).mappings().first()
            if existing_item is None:
                values = {
                    "name": item[1],
                    "category": item[2],
                    "price": item[3],
                    "description": item[4],
                    "popular": int(item[5]),
                    "image": item[6],
                }
                if connection.execute(
                    select(menu_items.c.id).where(menu_items.c.id == item[0])
                ).first() is None:
                    values["id"] = item[0]
                connection.execute(insert(menu_items).values(**values))
            elif (
                existing_item["name"] == item[1]
                and existing_item["image"] in LEGACY_MENU_IMAGES.get(item[1], ())
            ):
                connection.execute(
                    update(menu_items)
                    .where(menu_items.c.id == item[0])
                    .values(image=item[6])
                )
        for username, display_name, role, password_env in (
            (
                os.environ.get("RESTAURANT_ADMIN_USERNAME", "harsh@123"),
                "Harsh",
                "admin",
                "RESTAURANT_ADMIN_PASSWORD",
            ),
            (
                os.environ.get("RESTAURANT_STAFF_USERNAME", "staff@123"),
                "Restaurant Staff",
                "staff",
                "RESTAURANT_STAFF_PASSWORD",
            ),
        ):
            exists = connection.execute(select(users.c.id).where(users.c.username == username)).first()
            if exists is None:
                password = os.environ.get(password_env)
                if not password:
                    raise RuntimeError(
                        f"Set {password_env} in .env before creating the initial {role} account"
                    )
                connection.execute(
                    insert(users).values(
                        username=username,
                        display_name=display_name,
                        role=role,
                        employee_type="admin" if role == "admin" else "reception",
                        password_hash=hash_password(password),
                    )
                )
            elif os.environ.get(password_env):
                connection.execute(
                    update(users)
                    .where(users.c.username == username)
                    .values(password_hash=hash_password(os.environ[password_env]))
                )
        for k_user in ("aarav.kitchen782", "tara.kitchen481", "anaya.kitchen917", "mira.kitchen431"):
            if connection.execute(select(users.c.id).where(users.c.username == k_user)).first():
                connection.execute(
                    update(users)
                    .where(users.c.username == k_user)
                    .values(password_hash=hash_password("Staff@123"))
                )
        try:
            from backend.synthetic_data import seed_festival_calendar, seed_operating_expenses
            seed_festival_calendar(connection, festival_calendar)
            seed_operating_expenses(connection, operating_expenses, date(2025, 11, 1), date(2026, 12, 1))
        except Exception:
            pass


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)
    role: Literal["admin", "staff"] | None = None


class EmployeeCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=256)
    employee_type: Literal["reception", "kitchen"] = "reception"


class EmployeeStatusUpdate(BaseModel):
    is_active: bool


class EmployeePasswordUpdate(BaseModel):
    password: str = Field(min_length=8, max_length=256)


class PrepStatusUpdate(BaseModel):
    status: Literal["preparing", "ready", "delivered"]


class PaymentConfirmation(BaseModel):
    paid: bool


class CustomerSignup(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=256)
    email: str | None = Field(default=None, max_length=254)


class CustomerLogin(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class CustomerPreferences(BaseModel):
    dietary_preferences: list[Literal["vegetarian", "non-vegetarian", "vegan", "gluten-free", "dairy-free"]] = Field(default_factory=list)


class TableCreate(BaseModel):
    table_number: str = Field(min_length=1, max_length=60)


class TableStatusUpdate(BaseModel):
    is_active: bool


class IngredientInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=24)
    quantity: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    minimum_quantity: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=3)
    expires_at: date | None = None


class IngredientAdjustment(BaseModel):
    quantity_delta: Decimal = Field(max_digits=12, decimal_places=3)
    reason: str = Field(min_length=1, max_length=160)

    @field_validator("quantity_delta")
    @classmethod
    def require_nonzero_change(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("Quantity change cannot be zero")
        return value


class RecipeLineInput(BaseModel):
    ingredient_id: int = Field(gt=0)
    quantity_per_item: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class RecipeInput(BaseModel):
    ingredients: list[RecipeLineInput] = Field(min_length=1, max_length=100)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AdminChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def require_nonblank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


class AdminChatRequest(BaseModel):
    messages: list[AdminChatMessage] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def require_latest_user_message(self):
        if self.messages[-1].role != "user":
            raise ValueError("The latest message must be from the user")
        return self


class CounterPayment(BaseModel):
    cash_received: int = Field(ge=0, le=100_000_000)


class MenuItemInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=60)
    price: int = Field(gt=0, le=1_000_000)
    cost_price: int | None = Field(default=None, ge=0, le=1_000_000)
    description: str = Field(default="", max_length=300)
    popular: bool = False
    image: str = Field(default="photo-1546833999-b9f581a1996d", max_length=120)
    ingredients_text: str = Field(default="", max_length=1000)
    allergens_text: str = Field(default="", max_length=500)
    dietary_tags: list[Literal["vegetarian", "non-vegetarian", "vegan", "gluten-free", "dairy-free"]] = Field(default_factory=list)
    dietary_verified: bool = False
    spice_level: int | None = Field(default=None, ge=0, le=5)
    calories: int | None = Field(default=None, ge=0, le=5000)


class OrderLineInput(BaseModel):
    item_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=999)


class CustomerOrderInput(BaseModel):
    items: list[OrderLineInput] = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=500)
    points_to_redeem: int = Field(default=0, ge=0, multiple_of=10)


class OrderCancellationInput(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class OrderInput(BaseModel):
    order_type: Literal["Dine in", "Takeaway", "Delivery"]
    table_name: str | None = Field(default=None, max_length=60)
    guest_name: str | None = Field(default=None, max_length=120)
    note: str = Field(default="", max_length=500)
    cash_received: int = Field(ge=0, le=100_000_000)
    items: list[OrderLineInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def require_table_for_dine_in(self):
        if self.order_type == "Dine in" and not (
            self.table_name and re.fullmatch(r"Table \d{1,3}", self.table_name.strip(), re.IGNORECASE)
        ):
            raise ValueError("Select a table number for dine-in orders")
        return self


class ReservationInput(BaseModel):
    guest_name: str = Field(min_length=1, max_length=120)
    contact_phone: str = Field(min_length=5, max_length=32)
    party_size: int = Field(ge=1, le=50)
    reservation_date: date
    reservation_time: str = Field(pattern=r"^\d{1,2}:\d{2}(\s*(AM|PM|am|pm))?$")
    table_number: str | None = Field(default=None, max_length=60)
    special_requests: str = Field(default="", max_length=500)


class ReservationStatusUpdate(BaseModel):
    status: Literal["confirmed", "seated", "completed", "cancelled"]
    table_number: str | None = Field(default=None, max_length=60)


def menu_item(row: dict, include_cost: bool = False) -> dict:
    dietary_tags = row.get("dietary_tags")
    if isinstance(dietary_tags, str):
        try:
            dietary_tags = json.loads(dietary_tags)
        except json.JSONDecodeError:
            dietary_tags = []
    item = {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "price": row["price"],
        "description": row["description"],
        "popular": bool(row["popular"]),
        "image": row["image"],
        "ingredients_text": row.get("ingredients_text") or "",
        "allergens_text": row.get("allergens_text") or "",
        "dietary_tags": dietary_tags or [],
        "dietary_verified": bool(row.get("dietary_verified", False)),
        "spice_level": row.get("spice_level"),
        "calories": row.get("calories"),
    }
    if include_cost:
        item["cost_price"] = row["cost_price"]
    return item


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue")
    token = authorization.removeprefix("Bearer ").strip()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with engine.connect() as connection:
        row = connection.execute(
            select(
                users.c.id,
                users.c.username,
                users.c.display_name,
                users.c.role,
                users.c.employee_type,
            )
            .select_from(sessions.join(users, users.c.id == sessions.c.user_id))
            .where(
                sessions.c.token_hash == token_hash,
                sessions.c.expires_at > int(time.time()),
                users.c.is_active.is_(True),
            )
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired; sign in again")
    return dict(row)


def get_customer_user(authorization: Annotated[str | None, Header()] = None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Customer sign-in required")
    token = authorization.removeprefix("Bearer ").strip()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with engine.connect() as connection:
        row = connection.execute(
            select(
                customers.c.id,
                customers.c.username,
                customers.c.display_name,
                customers.c.email,
                customers.c.loyalty_points,
            )
            .select_from(customer_sessions.join(customers, customers.c.id == customer_sessions.c.customer_id))
            .where(
                customer_sessions.c.token_hash == token_hash,
                customer_sessions.c.expires_at > int(time.time()),
                customers.c.is_active.is_(True),
            )
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Customer session expired; sign in again")
    return dict(row)


CustomerUser = Annotated[dict, Depends(get_customer_user)]


CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


AdminUser = Annotated[dict, Depends(require_admin)]


def require_front_desk(user: CurrentUser) -> dict:
    if user["role"] != "admin" and user["employee_type"] != "reception":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reception access required")
    return user


FrontDeskUser = Annotated[dict, Depends(require_front_desk)]


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/admin/chat")
async def admin_chat(payload: AdminChatRequest, user: AdminUser, request: Request):
    from backend.admin_chat import AdminChatError, answer_admin_question

    answer_task = asyncio.create_task(
        answer_admin_question([message.model_dump() for message in payload.messages])
    )
    try:
        while not answer_task.done():
            if await request.is_disconnected():
                answer_task.cancel()
                with suppress(asyncio.CancelledError):
                    await answer_task
                logger.info("Admin chat cancelled for admin_id=%s after client disconnect", user["id"])
                return Response(status_code=499)
            await asyncio.wait({answer_task}, timeout=0.1)
        result = await answer_task
    except AdminChatError as error:
        logger.warning("Admin chat unavailable for admin_id=%s: %s", user["id"], error)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    finally:
        if not answer_task.done():
            answer_task.cancel()
            with suppress(asyncio.CancelledError):
                await answer_task
    logger.info(
        "Admin chat answered for admin_id=%s using tools=%s",
        user["id"],
        ",".join(result["tools_used"]) or "none",
    )
    return result


@app.post("/api/auth/login")
def login(credentials: LoginRequest) -> dict:
    with engine.begin() as connection:
        user = connection.execute(
            select(users).where(users.c.username == credentials.username.strip())
        ).mappings().first()
        if (
            user is None
            or not verify_password(credentials.password, user["password_hash"])
            or (credentials.role is not None and credentials.role != user["role"])
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
        token = secrets.token_urlsafe(32)
        connection.execute(
            insert(sessions).values(
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                user_id=user["id"],
                expires_at=int(time.time()) + SESSION_TTL_SECONDS,
            )
        )
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "role": user["role"],
            "employee_type": user["employee_type"],
        },
    }


@app.get("/api/auth/me")
def current_user(user: CurrentUser) -> dict:
    return user


@app.post("/api/auth/logout")
def logout(authorization: Annotated[str | None, Header()] = None) -> dict:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        with engine.begin() as connection:
            connection.execute(delete(sessions).where(sessions.c.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    return {"status": "ok"}


def customer_session_response(connection, customer_id: int) -> dict:
    token = secrets.token_urlsafe(32)
    connection.execute(
        insert(customer_sessions).values(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            customer_id=customer_id,
            expires_at=int(time.time()) + SESSION_TTL_SECONDS,
        )
    )
    customer = connection.execute(
        select(
            customers.c.id,
            customers.c.username,
            customers.c.display_name,
            customers.c.email,
            customers.c.loyalty_points,
        ).where(customers.c.id == customer_id)
    ).mappings().one()
    return {
        "token": token,
        "user": {**dict(customer), "role": "customer"},
    }


@app.post("/api/customer/signup", status_code=status.HTTP_201_CREATED)
def customer_signup(payload: CustomerSignup) -> dict:
    try:
        with engine.begin() as connection:
            result = connection.execute(
                insert(customers).values(
                    username=payload.username.strip(),
                    display_name=payload.display_name.strip(),
                    email=payload.email.strip().lower() if payload.email else None,
                    password_hash=hash_password(payload.password),
                )
            )
            return customer_session_response(connection, result.inserted_primary_key[0])
    except IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email is already registered") from error


@app.post("/api/customer/login")
def customer_login(payload: CustomerLogin) -> dict:
    with engine.begin() as connection:
        customer = connection.execute(
            select(customers).where(customers.c.username == payload.username.strip())
        ).mappings().first()
        if customer is None or not customer["is_active"] or not verify_password(
            payload.password, customer["password_hash"]
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
        return customer_session_response(connection, customer["id"])


@app.get("/api/customer/me")
def customer_me(customer: CustomerUser) -> dict:
    with engine.connect() as connection:
        preferences = connection.execute(
            select(customer_preferences.c.dietary_preferences).where(
                customer_preferences.c.customer_id == customer["id"]
            )
        ).scalar_one_or_none()
        transactions = connection.execute(
            select(loyalty_transactions.c.points_delta, loyalty_transactions.c.reason, loyalty_transactions.c.created_at)
            .where(loyalty_transactions.c.customer_id == customer["id"])
            .order_by(loyalty_transactions.c.created_at.desc(), loyalty_transactions.c.id.desc())
            .limit(50)
        ).mappings().all()
    return {
        **customer,
        "role": "customer",
        "dietary_preferences": preferences or [],
        "loyalty_transactions": [dict(row) for row in transactions],
    }


@app.post("/api/customer/logout")
def customer_logout(authorization: Annotated[str | None, Header()] = None) -> dict:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        with engine.begin() as connection:
            connection.execute(
                delete(customer_sessions).where(
                    customer_sessions.c.token_hash == hashlib.sha256(token.encode()).hexdigest()
                )
            )
    return {"status": "ok"}


@app.put("/api/customer/preferences")
def update_customer_preferences(payload: CustomerPreferences, customer: CustomerUser) -> dict:
    with engine.begin() as connection:
        existing = connection.execute(
            select(customer_preferences.c.customer_id).where(
                customer_preferences.c.customer_id == customer["id"]
            )
        ).first()
        values = {
            "dietary_preferences": payload.dietary_preferences,
            "updated_at": datetime.now(),
        }
        if existing:
            connection.execute(
                update(customer_preferences)
                .where(customer_preferences.c.customer_id == customer["id"])
                .values(**values)
            )
        else:
            connection.execute(
                insert(customer_preferences).values(customer_id=customer["id"], **values)
            )
    return {"dietary_preferences": payload.dietary_preferences}


@app.get("/api/admin/employees")
def list_employees(_: AdminUser) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            select(
                users.c.id,
                users.c.username,
                users.c.display_name,
                users.c.employee_type,
                users.c.is_active,
            )
            .where(users.c.role == "staff")
            .order_by(users.c.username)
        ).mappings().all()
    return [dict(row) for row in rows]


@app.post("/api/admin/employees", status_code=status.HTTP_201_CREATED)
def create_employee(employee: EmployeeCreate, _: AdminUser) -> dict:
    try:
        with engine.begin() as connection:
            result = connection.execute(
                insert(users).values(
                    username=employee.username.strip(),
                    display_name=employee.display_name.strip(),
                    role="staff",
                    employee_type=employee.employee_type,
                    password_hash=hash_password(employee.password),
                    is_active=True,
                )
            )
            row = connection.execute(
                select(
                    users.c.id,
                    users.c.username,
                    users.c.display_name,
                    users.c.employee_type,
                    users.c.is_active,
                )
                .where(users.c.id == result.inserted_primary_key[0])
            ).mappings().one()
    except IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already in use") from error
    return dict(row)


@app.patch("/api/admin/employees/{employee_id}")
def update_employee_status(employee_id: int, payload: EmployeeStatusUpdate, _: AdminUser) -> dict:
    with engine.begin() as connection:
        result = connection.execute(
            update(users)
            .where(users.c.id == employee_id, users.c.role == "staff")
            .values(is_active=payload.is_active)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        row = connection.execute(
            select(
                users.c.id,
                users.c.username,
                users.c.display_name,
                users.c.employee_type,
                users.c.is_active,
            )
            .where(users.c.id == employee_id)
        ).mappings().one()
    return dict(row)


@app.put("/api/admin/employees/{employee_id}/password")
def reset_employee_password(employee_id: int, payload: EmployeePasswordUpdate, _: AdminUser) -> dict:
    with engine.begin() as connection:
        result = connection.execute(
            update(users)
            .where(users.c.id == employee_id, users.c.role == "staff")
            .values(password_hash=hash_password(payload.password))
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        connection.execute(delete(sessions).where(sessions.c.user_id == employee_id))
    return {"status": "ok"}


@app.get("/api/menu")
def get_menu(user: FrontDeskUser) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(select(menu_items).order_by(menu_items.c.category, menu_items.c.name)).mappings().all()
    return [menu_item(row, include_cost=user["role"] == "admin") for row in rows]


def visible_to_dietary_preferences(row: dict, preferences: list[str]) -> bool:
    if not preferences:
        return True
    if not row.get("dietary_verified"):
        return False
    tags = row.get("dietary_tags") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except json.JSONDecodeError:
            tags = []
    return all(preference in tags for preference in preferences)


@app.get("/api/public/menu")
def get_public_menu(
    dietary: list[str] | None = Query(default=None),
    category: str | None = Query(default=None, max_length=60),
) -> list[dict]:
    allowed_diets = {"vegetarian", "non-vegetarian", "vegan", "gluten-free", "dairy-free"}
    preferences = dietary or []
    if any(preference not in allowed_diets for preference in preferences):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported dietary filter")
    statement = select(menu_items)
    if category:
        statement = statement.where(menu_items.c.category == category)
    with engine.connect() as connection:
        rows = connection.execute(statement.order_by(menu_items.c.category, menu_items.c.name)).mappings().all()
    return [
        menu_item(row)
        for row in rows
        if visible_to_dietary_preferences(row, preferences)
    ]


@app.get("/api/customer/recommendations")
def get_customer_recommendations(customer: CustomerUser) -> dict:
    with engine.connect() as connection:
        preferences = connection.execute(
            select(customer_preferences.c.dietary_preferences).where(
                customer_preferences.c.customer_id == customer["id"]
            )
        ).scalar_one_or_none() or []
        purchased = connection.execute(
            select(
                order_items.c.item_name,
                func.sum(order_items.c.quantity).label("units"),
            )
            .select_from(order_items.join(orders, orders.c.id == order_items.c.order_id))
            .where(
                orders.c.customer_id == customer["id"],
                orders.c.payment_status == "paid",
                orders.c.order_status != "cancelled",
            )
            .group_by(order_items.c.item_name)
        ).mappings().all()
        item_sales = (
            select(
                order_items.c.menu_item_id.label("menu_item_id"),
                func.sum(order_items.c.quantity).label("sold_units"),
            )
            .select_from(order_items.join(orders, orders.c.id == order_items.c.order_id))
            .where(
                orders.c.payment_status == "paid",
                orders.c.order_status != "cancelled",
            )
            .group_by(order_items.c.menu_item_id)
            .subquery()
        )
        popular = connection.execute(
            select(
                menu_items,
                func.coalesce(item_sales.c.sold_units, 0).label("sold_units"),
            )
            .select_from(menu_items.outerjoin(item_sales, item_sales.c.menu_item_id == menu_items.c.id))
            .order_by(func.coalesce(item_sales.c.sold_units, 0).desc(), menu_items.c.popular.desc(), menu_items.c.name)
        ).mappings().all()
    purchased_units = {row["item_name"]: row["units"] for row in purchased}
    favorite_categories: dict[str, int] = {}
    for row in popular:
        if row["name"] in purchased_units:
            favorite_categories[row["category"]] = favorite_categories.get(row["category"], 0) + purchased_units[row["name"]]
    personalized = bool(purchased_units)
    candidates = []
    for row in popular:
        if not visible_to_dietary_preferences(row, preferences):
            continue
        if personalized and row["name"] in purchased_units:
            continue
        reason = (
            f"Popular in {row['category']}"
            if not personalized
            else "Pairs well with categories you order" if row["category"] in favorite_categories
            else "Popular with other guests"
        )
        candidates.append(
            {
                **menu_item(row),
                "sold_units": int(row["sold_units"] or 0),
                "reason": reason,
            }
        )
    return {
        "personalized": personalized,
        "dietary_preferences": preferences,
        "recommendations": candidates[:8],
        "disclaimer": "Dietary matches include only menu items whose classifications were verified by restaurant staff.",
    }


@app.post("/api/menu", status_code=status.HTTP_201_CREATED)
def create_menu_item(item: MenuItemInput, _: AdminUser) -> dict:
    with engine.begin() as connection:
        result = connection.execute(
            insert(menu_items).values(
                name=item.name.strip(),
                category=item.category,
                price=item.price,
                cost_price=item.cost_price,
                description=item.description.strip(),
                popular=int(item.popular),
                image=item.image,
                ingredients_text=item.ingredients_text,
                allergens_text=item.allergens_text,
                dietary_tags=item.dietary_tags,
                dietary_verified=item.dietary_verified,
                spice_level=item.spice_level,
                calories=item.calories,
            )
        )
        row = connection.execute(select(menu_items).where(menu_items.c.id == result.inserted_primary_key[0])).mappings().one()
    return menu_item(row, include_cost=True)


@app.put("/api/menu/{item_id}")
def update_menu_item(item_id: int, item: MenuItemInput, _: AdminUser) -> dict:
    with engine.begin() as connection:
        result = connection.execute(
            update(menu_items)
            .where(menu_items.c.id == item_id)
            .values(
                name=item.name.strip(),
                category=item.category,
                price=item.price,
                cost_price=item.cost_price,
                description=item.description.strip(),
                popular=int(item.popular),
                image=item.image,
                ingredients_text=item.ingredients_text,
                allergens_text=item.allergens_text,
                dietary_tags=item.dietary_tags,
                dietary_verified=item.dietary_verified,
                spice_level=item.spice_level,
                calories=item.calories,
            )
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        row = connection.execute(select(menu_items).where(menu_items.c.id == item_id)).mappings().one()
    return menu_item(row, include_cost=True)


@app.delete("/api/menu/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(item_id: int, _: AdminUser) -> None:
    with engine.begin() as connection:
        result = connection.execute(delete(menu_items).where(menu_items.c.id == item_id))
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")


@app.get("/api/admin/tables")
def list_restaurant_tables(_: AdminUser) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            select(
                restaurant_tables.c.id,
                restaurant_tables.c.table_number,
                restaurant_tables.c.is_active,
                restaurant_tables.c.created_at,
            ).order_by(restaurant_tables.c.table_number)
        ).mappings().all()
    return [dict(row) for row in rows]


@app.post("/api/admin/tables", status_code=status.HTTP_201_CREATED)
def create_restaurant_table(payload: TableCreate, _: AdminUser) -> dict:
    table_number = payload.table_number.strip()
    match = re.fullmatch(r"(?:Table\s*|T\s*)?(\d{1,3})", table_number, re.IGNORECASE)
    if not match:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Table number must look like 'Table 12'")
    table_number = f"Table {int(match.group(1)):02d}"
    token = secrets.token_urlsafe(32)
    try:
        with engine.begin() as connection:
            result = connection.execute(
                insert(restaurant_tables).values(
                    table_number=table_number,
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                )
            )
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That table already exists") from exc
    order_url = f"/order?table={urllib.parse.quote(table_number)}&token={urllib.parse.quote(token)}"
    return {
        "id": result.inserted_primary_key[0],
        "table_number": table_number,
        "is_active": True,
        "order_url": order_url,
    }


@app.post("/api/admin/tables/{table_id}/qr")
def rotate_restaurant_table_qr(table_id: int, _: AdminUser) -> dict:
    token = secrets.token_urlsafe(32)
    with engine.begin() as connection:
        table_row = connection.execute(
            select(restaurant_tables.c.table_number, restaurant_tables.c.is_active)
            .where(restaurant_tables.c.id == table_id)
        ).mappings().first()
        if table_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
        if not table_row["is_active"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Enable this table before issuing a QR code")
        connection.execute(
            update(restaurant_tables)
            .where(restaurant_tables.c.id == table_id)
            .values(token_hash=hashlib.sha256(token.encode()).hexdigest())
        )
    order_url = f"/order?table={urllib.parse.quote(table_row['table_number'])}&token={urllib.parse.quote(token)}"
    return {"id": table_id, "table_number": table_row["table_number"], "order_url": order_url}


@app.patch("/api/admin/tables/{table_id}")
def update_restaurant_table(table_id: int, payload: TableStatusUpdate, _: AdminUser) -> dict:
    with engine.begin() as connection:
        result = connection.execute(
            update(restaurant_tables)
            .where(restaurant_tables.c.id == table_id)
            .values(is_active=payload.is_active)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"id": table_id, "is_active": payload.is_active}


@app.get("/api/admin/inventory")
def list_inventory(_: AdminUser) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            select(ingredients).order_by(ingredients.c.name)
        ).mappings().all()
    today = date.today()
    return [
        {
            **dict(row),
            "low_stock": row["quantity"] <= row["minimum_quantity"],
            "expired": row["expires_at"] is not None and row["expires_at"] < today,
        }
        for row in rows
    ]


@app.post("/api/admin/inventory", status_code=status.HTTP_201_CREATED)
def create_ingredient(payload: IngredientInput, _: AdminUser) -> dict:
    try:
        with engine.begin() as connection:
            result = connection.execute(insert(ingredients).values(**payload.model_dump()))
            ingredient_id = result.inserted_primary_key[0]
            if payload.quantity:
                connection.execute(
                    insert(inventory_transactions).values(
                        ingredient_id=ingredient_id,
                        quantity_delta=payload.quantity,
                        reason="Initial stock",
                    )
                )
            row = connection.execute(
                select(ingredients).where(ingredients.c.id == ingredient_id)
            ).mappings().one()
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An ingredient with that name already exists") from exc
    return dict(row)


@app.post("/api/admin/inventory/{ingredient_id}/adjust")
def adjust_inventory(ingredient_id: int, payload: IngredientAdjustment, _: AdminUser) -> dict:
    with engine.begin() as connection:
        ingredient = connection.execute(
            select(ingredients).where(ingredients.c.id == ingredient_id).with_for_update()
        ).mappings().first()
        if ingredient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")
        if Decimal(ingredient["quantity"]) + payload.quantity_delta < 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Adjustment would make stock negative")
        connection.execute(
            update(ingredients)
            .where(ingredients.c.id == ingredient_id)
            .values(quantity=ingredients.c.quantity + payload.quantity_delta, updated_at=datetime.now())
        )
        connection.execute(
            insert(inventory_transactions).values(
                ingredient_id=ingredient_id,
                quantity_delta=payload.quantity_delta,
                reason=payload.reason.strip(),
            )
        )
        quantity = connection.execute(
            select(ingredients.c.quantity).where(ingredients.c.id == ingredient_id)
        ).scalar_one()
    return {"id": ingredient_id, "quantity": quantity}


@app.put("/api/admin/menu/{menu_item_id}/recipe")
def replace_recipe(menu_item_id: int, payload: RecipeInput, _: AdminUser) -> dict:
    ingredient_ids = {line.ingredient_id for line in payload.ingredients}
    if len(ingredient_ids) != len(payload.ingredients):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Each ingredient may appear only once")
    with engine.begin() as connection:
        if connection.execute(select(menu_items.c.id).where(menu_items.c.id == menu_item_id)).first() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        existing_ids = set(connection.execute(
            select(ingredients.c.id).where(ingredients.c.id.in_(ingredient_ids))
        ).scalars())
        if existing_ids != ingredient_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more ingredients were not found")
        connection.execute(delete(recipe_ingredients).where(recipe_ingredients.c.menu_item_id == menu_item_id))
        connection.execute(
            insert(recipe_ingredients),
            [
                {
                    "menu_item_id": menu_item_id,
                    "ingredient_id": line.ingredient_id,
                    "quantity_per_item": line.quantity_per_item,
                }
                for line in payload.ingredients
            ],
        )
    return {"menu_item_id": menu_item_id, "ingredient_count": len(payload.ingredients)}


@app.get("/api/admin/menu/{menu_item_id}/recipe")
def get_recipe(menu_item_id: int, _: AdminUser) -> dict:
    with engine.connect() as connection:
        if connection.execute(select(menu_items.c.id).where(menu_items.c.id == menu_item_id)).first() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        rows = connection.execute(
            select(
                inventory_transactions.c.ingredient_id,
                recipe_ingredients.c.quantity_per_item,
            )
            .where(recipe_ingredients.c.menu_item_id == menu_item_id)
            .order_by(recipe_ingredients.c.id)
        ).mappings().all()
    return {
        "menu_item_id": menu_item_id,
        "ingredients": [
            {
                "ingredient_id": row["ingredient_id"],
                "quantity_per_item": str(row["quantity_per_item"]),
            }
            for row in rows
        ],
    }


@app.get("/api/admin/inventory/transactions")
def list_inventory_transactions(_: AdminUser, limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            select(
                inventory_transactions,
                ingredients.c.name.label("ingredient_name"),
                ingredients.c.unit,
            )
            .select_from(inventory_transactions.join(ingredients, ingredients.c.id == inventory_transactions.c.ingredient_id))
            .order_by(inventory_transactions.c.created_at.desc(), inventory_transactions.c.id.desc())
            .limit(limit)
        ).mappings().all()
    return [dict(row) for row in rows]


def insert_order_record(
    connection,
    *,
    items: list[OrderLineInput],
    order_type: str,
    table_name: str | None,
    guest_name: str | None,
    note: str,
    cash_received: int,
    created_by: int | None,
    customer_id: int | None,
    payment_status: str,
    points_to_redeem: int = 0,
) -> dict:
    requested: dict[int, int] = {}
    for line in items:
        requested[line.item_id] = requested.get(line.item_id, 0) + line.quantity
    ids = list(requested)
    rows = connection.execute(select(menu_items).where(menu_items.c.id.in_(ids))).mappings().all()
    found = {row["id"]: row for row in rows}
    if len(found) != len(ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more menu items are no longer available")
    lines = [
        {
            "item_id": item_id,
            "name": found[item_id]["name"],
            "price": found[item_id]["price"],
            "cost": found[item_id]["cost_price"],
            "quantity": quantity,
        }
        for item_id, quantity in requested.items()
    ]
    gross_subtotal = sum(line["price"] * line["quantity"] for line in lines)
    discount_amount = points_to_redeem // 10
    if points_to_redeem:
        balance = connection.execute(
            select(customers.c.loyalty_points)
            .where(customers.c.id == customer_id)
            .with_for_update()
        ).scalar_one()
        if points_to_redeem > balance or discount_amount > gross_subtotal * 0.2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient points or redemption exceeds 20% of the food subtotal",
            )
    subtotal = gross_subtotal - discount_amount
    tax = (subtotal * 5 + 50) // 100
    total = subtotal + tax
    if payment_status == "paid" and cash_received < total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cash received is less than the order total")

    recipes = connection.execute(
        select(
            recipe_ingredients.c.menu_item_id,
            recipe_ingredients.c.ingredient_id,
            recipe_ingredients.c.quantity_per_item,
            ingredients.c.name,
            ingredients.c.unit,
            ingredients.c.quantity,
        )
        .select_from(recipe_ingredients.join(ingredients, ingredients.c.id == recipe_ingredients.c.ingredient_id))
        .where(recipe_ingredients.c.menu_item_id.in_(ids))
        .with_for_update()
    ).mappings().all()
    required: dict[int, Decimal] = {}
    ingredient_details = {}
    for recipe in recipes:
        menu_line = next(line for line in lines if line["item_id"] == recipe["menu_item_id"])
        ingredient_id = recipe["ingredient_id"]
        required[ingredient_id] = required.get(ingredient_id, Decimal("0")) + (
            Decimal(recipe["quantity_per_item"]) * menu_line["quantity"]
        )
        ingredient_details[ingredient_id] = recipe
    for ingredient_id, amount in required.items():
        available = Decimal(ingredient_details[ingredient_id]["quantity"])
        if amount > available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient stock for {ingredient_details[ingredient_id]['name']}",
            )

    order_result = connection.execute(
        insert(orders).values(
            order_type=order_type,
            table_name=table_name,
            guest_name=guest_name,
            note=note.strip(),
            subtotal=subtotal,
            tax=tax,
            total=total,
            cash_received=cash_received,
            change_due=max(0, cash_received - total),
            created_by=created_by,
            customer_id=customer_id,
            payment_status=payment_status,
            discount_amount=discount_amount,
        )
    )
    order_id = order_result.inserted_primary_key[0]
    order_item_ids = {}
    for line in lines:
        item_result = connection.execute(
            insert(order_items).values(
                order_id=order_id,
                menu_item_id=line["item_id"],
                item_name=line["name"],
                unit_price=line["price"],
                unit_cost=line["cost"],
                quantity=line["quantity"],
            )
        )
        order_item_ids[line["item_id"]] = item_result.inserted_primary_key[0]
    for ingredient_id, amount in required.items():
        connection.execute(
            update(ingredients)
            .where(ingredients.c.id == ingredient_id)
            .values(
                quantity=ingredients.c.quantity - amount,
                updated_at=datetime.now(),
            )
        )
    for recipe in recipes:
        menu_line = next(line for line in lines if line["item_id"] == recipe["menu_item_id"])
        consumed = Decimal(recipe["quantity_per_item"]) * menu_line["quantity"]
        connection.execute(
            insert(inventory_transactions).values(
                ingredient_id=recipe["ingredient_id"],
                order_id=order_id,
                order_item_id=order_item_ids[recipe["menu_item_id"]],
                quantity_delta=-consumed,
                reason="Order consumption",
            )
        )
    if points_to_redeem:
        connection.execute(
            update(customers)
            .where(customers.c.id == customer_id)
            .values(loyalty_points=customers.c.loyalty_points - points_to_redeem)
        )
        connection.execute(
            insert(loyalty_transactions).values(
                customer_id=customer_id,
                order_id=order_id,
                points_delta=-points_to_redeem,
                reason="Redeemed at QR checkout",
            )
        )
    return {
        "id": order_id,
        "order_type": order_type,
        "table_name": table_name,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "discount_amount": discount_amount,
        "payment_status": payment_status,
        "cash_received": cash_received,
        "change_due": max(0, cash_received - total),
        "items": [
            {
                "item_id": line["item_id"],
                "name": line["name"],
                "price": line["price"],
                "quantity": line["quantity"],
            }
            for line in lines
        ],
    }


@app.post("/api/customer/orders/qr", status_code=status.HTTP_201_CREATED)
async def create_qr_order(
    payload: CustomerOrderInput,
    customer: CustomerUser,
    table: str = Query(min_length=1, max_length=60),
    token: str = Query(min_length=32, max_length=128),
) -> dict:
    with engine.begin() as connection:
        qr_table = connection.execute(
            select(restaurant_tables)
            .where(
                restaurant_tables.c.table_number == table,
                restaurant_tables.c.token_hash == hashlib.sha256(token.encode()).hexdigest(),
                restaurant_tables.c.is_active.is_(True),
            )
        ).mappings().first()
        if qr_table is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This table QR code is invalid or inactive")
        result = insert_order_record(
            connection,
            items=payload.items,
            order_type="Dine in",
            table_name=qr_table["table_number"],
            guest_name=customer["display_name"],
            note=payload.note,
            cash_received=0,
            created_by=None,
            customer_id=customer["id"],
            payment_status="unpaid",
            points_to_redeem=payload.points_to_redeem,
        )
    await broadcast_kitchen_update({"type": "order.created", "order_id": result["id"]})
    return result


def customer_order_summary(connection, order_id: int, customer_id: int) -> dict | None:
    order = connection.execute(
        select(orders).where(
            orders.c.id == order_id,
            orders.c.customer_id == customer_id,
        )
    ).mappings().first()
    if order is None:
        return None
    lines = connection.execute(
        select(
            order_items.c.item_name.label("name"),
            order_items.c.quantity,
            order_items.c.prep_status,
        ).where(order_items.c.order_id == order_id).order_by(order_items.c.id)
    ).mappings().all()
    return {
        "id": order["id"],
        "table_name": order["table_name"],
        "guest_name": order["guest_name"],
        "note": order["note"],
        "subtotal": order["subtotal"],
        "tax": order["tax"],
        "total": order["total"],
        "discount_amount": order["discount_amount"],
        "payment_status": order["payment_status"],
        "order_status": order["order_status"],
        "cancellation_reason": order["cancellation_reason"],
        "created_at": order["created_at"],
        "items": [dict(line) for line in lines],
    }


@app.get("/api/customer/orders")
def list_customer_orders(customer: CustomerUser) -> list[dict]:
    with engine.connect() as connection:
        ids = connection.execute(
            select(orders.c.id)
            .where(orders.c.customer_id == customer["id"])
            .order_by(orders.c.created_at.desc(), orders.c.id.desc())
            .limit(50)
        ).scalars().all()
        return [customer_order_summary(connection, order_id, customer["id"]) for order_id in ids]


@app.get("/api/customer/orders/{order_id}")
def get_customer_order(order_id: int, customer: CustomerUser) -> dict:
    with engine.connect() as connection:
        order = customer_order_summary(connection, order_id, customer["id"])
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@app.post("/api/customer/orders/{order_id}/cancel")
def cancel_customer_order(
    order_id: int,
    payload: OrderCancellationInput,
    customer: CustomerUser,
) -> dict:
    reason = payload.reason.strip() if payload.reason else None
    with engine.begin() as connection:
        order = connection.execute(
            select(orders)
            .where(orders.c.id == order_id, orders.c.customer_id == customer["id"])
            .with_for_update()
        ).mappings().first()
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order["order_status"] == "cancelled":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order is already cancelled")

        lines = connection.execute(
            select(order_items.c.id, order_items.c.menu_item_id, order_items.c.quantity, order_items.c.prep_status)
            .where(order_items.c.order_id == order_id)
            .order_by(order_items.c.id)
            .with_for_update()
        ).mappings().all()
        if not lines or all(line["prep_status"] == "delivered" for line in lines):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed orders cannot be cancelled")

        stock_to_restore: dict[int, Decimal] = {}
        queued_item_ids = [
            line["id"] for line in lines if line["prep_status"] == "queued"
        ]
        if queued_item_ids:
            consumption_rows = connection.execute(
                select(
                    inventory_transactions.c.ingredient_id,
                    func.sum(-inventory_transactions.c.quantity_delta).label("quantity"),
                )
                .where(
                    inventory_transactions.c.order_id == order_id,
                    inventory_transactions.c.reason == "Order consumption",
                    inventory_transactions.c.order_item_id.in_(queued_item_ids),
                )
                .group_by(inventory_transactions.c.ingredient_id)
            ).mappings().all()
            stock_to_restore = {
                row["ingredient_id"]: Decimal(row["quantity"])
                for row in consumption_rows
            }
            if not consumption_rows and all(line["prep_status"] == "queued" for line in lines):
                legacy_consumption = connection.execute(
                    select(
                        inventory_transactions.c.ingredient_id,
                        func.sum(-inventory_transactions.c.quantity_delta).label("quantity"),
                    )
                    .where(
                        inventory_transactions.c.order_id == order_id,
                        inventory_transactions.c.reason == "Order consumption",
                        inventory_transactions.c.order_item_id.is_(None),
                    )
                    .group_by(inventory_transactions.c.ingredient_id)
                ).mappings().all()
                stock_to_restore = {
                    row["ingredient_id"]: Decimal(row["quantity"])
                    for row in legacy_consumption
                }

        for ingredient_id, amount in stock_to_restore.items():
            ingredient = connection.execute(
                select(ingredients.c.id)
                .where(ingredients.c.id == ingredient_id)
                .with_for_update()
            ).first()
            if ingredient is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Inventory stock records are unavailable; order cancellation was not completed",
                )
            connection.execute(
                update(ingredients)
                .where(ingredients.c.id == ingredient_id)
                .values(quantity=ingredients.c.quantity + amount, updated_at=datetime.now())
            )
            connection.execute(
                insert(inventory_transactions).values(
                    ingredient_id=ingredient_id,
                    order_id=order_id,
                    quantity_delta=amount,
                    reason="Cancelled queued order restoration",
                )
            )

        if order["discount_amount"] and order["customer_id"] is not None:
            restored_points = order["discount_amount"] * 10
            connection.execute(
                update(customers)
                .where(customers.c.id == order["customer_id"])
                .values(loyalty_points=customers.c.loyalty_points + restored_points)
            )
            connection.execute(
                insert(loyalty_transactions).values(
                    customer_id=order["customer_id"],
                    order_id=order_id,
                    points_delta=restored_points,
                    reason="Cancelled order points restored",
                )
            )

        connection.execute(
            update(orders)
            .where(orders.c.id == order_id, orders.c.order_status == "active")
            .values(order_status="cancelled", cancellation_reason=reason)
        )
        return customer_order_summary(connection, order_id, customer["id"])


@app.post("/api/orders/{order_id}/pay")
def pay_customer_order(order_id: int, payload: CounterPayment, _: FrontDeskUser) -> dict:
    with engine.begin() as connection:
        order = connection.execute(
            select(orders).where(orders.c.id == order_id).with_for_update()
        ).mappings().first()
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order["order_status"] == "cancelled":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancelled orders cannot be paid")
        if order["order_status"] != "cancelled" and order["payment_status"] == "paid":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order has already been paid")
        if payload.cash_received < order["total"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cash received is less than the order total")
        connection.execute(
            update(orders)
            .where(orders.c.id == order_id, orders.c.payment_status != "paid")
            .values(
                payment_status="paid",
                cash_received=payload.cash_received,
                change_due=payload.cash_received - order["total"],
            )
        )
        award_loyalty_if_complete(connection, order_id)
    return {
        "id": order_id,
        "payment_status": "paid",
        "cash_received": payload.cash_received,
        "change_due": payload.cash_received - order["total"],
    }


@app.post("/api/orders/{order_id}/confirm-payment")
async def confirm_order_payment(
    order_id: int,
    payload: PaymentConfirmation,
    _: FrontDeskUser,
) -> dict:
    if not payload.paid:
        return {"id": order_id, "payment_status": "unpaid"}
    with engine.begin() as connection:
        order = connection.execute(
            select(orders.c.total, orders.c.payment_status, orders.c.order_status)
            .where(orders.c.id == order_id)
            .with_for_update()
        ).mappings().first()
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order["order_status"] == "cancelled":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancelled orders cannot be paid")
        if order["payment_status"] == "paid":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order has already been paid")
        ready_item = connection.execute(
            select(order_items.c.id)
            .where(order_items.c.order_id == order_id, order_items.c.prep_status == "ready")
            .limit(1)
        ).first()
        if ready_item is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment can only be confirmed after the kitchen marks an item ready",
            )
        connection.execute(
            update(orders)
            .where(orders.c.id == order_id, orders.c.payment_status != "paid")
            .values(
                payment_status="paid",
                cash_received=order["total"],
                change_due=0,
            )
        )
        award_loyalty_if_complete(connection, order_id)
    await broadcast_kitchen_update(
        {"type": "payment.updated", "order_id": order_id, "payment_status": "paid"}
    )
    return {
        "id": order_id,
        "payment_status": "paid",
        "cash_received": order["total"],
        "change_due": 0,
    }


@app.post("/api/orders", status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderInput, user: CurrentUser) -> dict:
    if user["role"] != "admin" and user["employee_type"] != "reception":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reception access required")
    with engine.begin() as connection:
        result = insert_order_record(
            connection,
            items=order.items,
            order_type=order.order_type,
            table_name=order.table_name,
            guest_name=order.guest_name,
            note=order.note,
            cash_received=order.cash_received,
            created_by=user["id"],
            customer_id=None,
            payment_status="paid",
        )
    await broadcast_kitchen_update({"type": "order.created", "order_id": result["id"]})
    return result


active_kitchen_sockets: set[WebSocket] = set()


async def broadcast_kitchen_update(event: dict) -> None:
    for socket in list(active_kitchen_sockets):
        try:
            await socket.send_json(event)
        except WebSocketDisconnect:
            active_kitchen_sockets.discard(socket)


@app.websocket("/ws/kitchen")
async def kitchen_updates(websocket: WebSocket) -> None:
    protocols = websocket.scope.get("subprotocols", [])
    token = websocket.query_params.get("token", "")
    if not token and len(protocols) == 2 and protocols[0] == "restaurant-auth":
        token = protocols[1]
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with engine.connect() as connection:
        user = connection.execute(
            select(users.c.role, users.c.employee_type)
            .select_from(sessions.join(users, users.c.id == sessions.c.user_id))
            .where(
                sessions.c.token_hash == token_hash,
                sessions.c.expires_at > int(time.time()),
                users.c.is_active.is_(True),
            )
        ).mappings().first()
    if user is None:
        await websocket.close(code=4401)
        return
    if user["role"] != "admin" and user["employee_type"] not in {"kitchen", "reception"}:
        await websocket.close(code=4403)
        return
    await websocket.accept(subprotocol="restaurant-auth" if len(protocols) == 2 and protocols[0] == "restaurant-auth" else None)
    active_kitchen_sockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_kitchen_sockets.discard(websocket)


@app.get("/api/prep/orders")
def list_prep_orders(user: CurrentUser) -> list[dict]:
    if user["role"] != "admin" and user["employee_type"] not in {"kitchen", "reception"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kitchen tracking access required")
    start = datetime.combine(date.today(), datetime_time.min)
    end = start + timedelta(days=1)
    with engine.connect() as connection:
        order_rows = connection.execute(
            select(
                orders,
                func.coalesce(users.c.display_name, "QR customer").label("staff_name"),
            )
            .select_from(
                orders.outerjoin(users, users.c.id == orders.c.created_by)
            )
            .where(
                orders.c.created_at >= start,
                orders.c.created_at < end,
                orders.c.order_status != "cancelled",
            )
            .order_by(orders.c.created_at.desc(), orders.c.id.desc())
        ).mappings().all()
        result = []
        for order in order_rows:
            lines = connection.execute(
                select(
                    order_items.c.id,
                    order_items.c.item_name.label("name"),
                    order_items.c.quantity,
                    order_items.c.prep_status,
                )
                .where(
                    order_items.c.order_id == order["id"],
                    order_items.c.prep_status != "delivered",
                )
                .order_by(order_items.c.id)
            ).mappings().all()
            if not lines:
                continue
            result.append(
                {
                    "id": order["id"],
                    "total": order["total"],
                    "payment_status": order["payment_status"],
                    "order_type": order["order_type"],
                    "table_name": order["table_name"],
                    "guest_name": order["guest_name"],
                    "note": order["note"],
                    "staff_name": order["staff_name"],
                    "created_at": order["created_at"],
                    "items": [
                        {
                            **dict(line),
                            "order_id": order["id"],
                        }
                        for line in lines
                    ],
                }
            )
    return result


def award_loyalty_if_complete(connection, order_id: int) -> None:
    order = connection.execute(
        select(orders.c.customer_id, orders.c.total, orders.c.payment_status, orders.c.order_status)
        .where(orders.c.id == order_id)
        .with_for_update()
    ).mappings().one()
    if order["order_status"] == "cancelled" or order["customer_id"] is None or order["payment_status"] != "paid":
        return
    remaining = connection.execute(
        select(order_items.c.id)
        .where(order_items.c.order_id == order_id, order_items.c.prep_status != "delivered")
        .limit(1)
    ).first()
    if remaining is not None:
        return
    points = order["total"] // 100
    if points < 1:
        return
    already_earned = connection.execute(
        select(loyalty_transactions.c.id).where(
            loyalty_transactions.c.order_id == order_id,
            loyalty_transactions.c.reason == "Completed order reward",
        )
    ).first()
    if already_earned is not None:
        return
    connection.execute(
        update(customers)
        .where(customers.c.id == order["customer_id"])
        .values(loyalty_points=customers.c.loyalty_points + points)
    )
    connection.execute(
        insert(loyalty_transactions).values(
            customer_id=order["customer_id"],
            order_id=order_id,
            points_delta=points,
            reason="Completed order reward",
        )
    )


@app.patch("/api/prep/items/{item_id}")
async def update_prep_status(item_id: int, payload: PrepStatusUpdate, user: CurrentUser) -> dict:
    if user["role"] != "staff" or user["employee_type"] != "kitchen":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kitchen staff access required")
    today_start = datetime.combine(date.today(), datetime_time.min)
    with engine.begin() as connection:
        line = connection.execute(
            select(order_items.c.prep_status, order_items.c.order_id, orders.c.payment_status, orders.c.order_status)
            .select_from(order_items.join(orders, orders.c.id == order_items.c.order_id))
            .where(order_items.c.id == item_id, orders.c.created_at >= today_start)
            .with_for_update()
        ).mappings().first()
        if line is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Today's kitchen item not found")
        if line["order_status"] == "cancelled":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancelled orders cannot be prepared")
        allowed_transition = {
            "queued": "preparing",
            "preparing": "ready",
            "ready": "delivered",
        }.get(line["prep_status"])
        if payload.status != allowed_transition:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item is {line['prep_status']}; the next status must be {allowed_transition or 'none'}",
            )
        connection.execute(
            update(order_items)
            .where(order_items.c.id == item_id, order_items.c.prep_status == line["prep_status"])
            .values(prep_status=payload.status)
        )
        if payload.status == "delivered":
            award_loyalty_if_complete(connection, line["order_id"])
    await broadcast_kitchen_update(
        {
            "type": "prep.updated",
            "item_id": item_id,
            "status": payload.status,
            "payment_status": line["payment_status"],
        }
    )
    return {
        "id": item_id,
        "status": payload.status,
        "payment_status": line["payment_status"],
    }


@app.get("/api/reports/daily")
def get_daily_report(report_date: date, _: AdminUser) -> dict:
    start = datetime.combine(report_date, datetime_time.min)
    end = start + timedelta(days=1)
    with engine.connect() as connection:
        order_rows = connection.execute(
            select(
                orders,
                func.coalesce(users.c.display_name, "QR customer").label("staff_name"),
            )
            .select_from(
                orders.outerjoin(users, users.c.id == orders.c.created_by)
            )
            .where(orders.c.created_at >= start, orders.c.created_at < end)
            .order_by(orders.c.created_at.desc(), orders.c.id.desc())
        ).mappings().all()

        report_orders = []
        subtotal = 0
        tax = 0
        total_billed = 0
        cash_received = 0
        change_given = 0
        cost_of_goods = 0
        uncosted_quantity = 0
        unpaid_total = 0
        for order in order_rows:
            lines = connection.execute(
                select(
                    order_items.c.menu_item_id.label("item_id"),
                    order_items.c.item_name.label("name"),
                    order_items.c.unit_price.label("price"),
                    order_items.c.unit_cost.label("cost_price"),
                    order_items.c.quantity,
                ).where(order_items.c.order_id == order["id"])
            ).mappings().all()
            if order["order_status"] != "cancelled" and order["payment_status"] == "paid":
                for line in lines:
                    if line["cost_price"] is None:
                        uncosted_quantity += line["quantity"]
                    else:
                        cost_of_goods += line["cost_price"] * line["quantity"]
                subtotal += order["subtotal"]
                tax += order["tax"]
                total_billed += order["total"]
                cash_received += order["cash_received"]
                change_given += order["change_due"]
            elif order["order_status"] != "cancelled":
                unpaid_total += order["total"]
            report_orders.append(
                {
                    "id": order["id"],
                    "order_type": order["order_type"],
                    "table_name": order["table_name"],
                    "guest_name": order["guest_name"],
                    "subtotal": order["subtotal"],
                    "tax": order["tax"],
                    "total": order["total"],
                    "payment_status": order["payment_status"],
                    "order_status": order["order_status"],
                    "cancellation_reason": order["cancellation_reason"],
                    "cash_received": order["cash_received"],
                    "change_due": order["change_due"],
                    "staff_name": order["staff_name"],
                    "created_at": order["created_at"],
                    "note": order["note"],
                    "items": [dict(line) for line in lines],
                }
            )

    return {
        "date": report_date.isoformat(),
        "order_count": sum(1 for order in order_rows if order["order_status"] != "cancelled"),
        "sales_revenue": subtotal,
        "tax_collected": tax,
        "total_billed": total_billed,
        "unpaid_total": unpaid_total,
        "unpaid_order_count": sum(
            1 for order in order_rows
            if order["order_status"] != "cancelled" and order["payment_status"] != "paid"
        ),
        "cash_received": cash_received,
        "change_given": change_given,
        "cost_of_goods": cost_of_goods,
        "gross_profit": subtotal - cost_of_goods if uncosted_quantity == 0 else None,
        "profit_complete": uncosted_quantity == 0,
        "uncosted_quantity": uncosted_quantity,
        "orders": report_orders,
    }


@app.get("/api/reports/analytics")
def get_business_analytics(
    start_date: date,
    end_date: date,
    _: AdminUser,
) -> dict:
    if end_date < start_date or (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose a date range of at most 366 days",
        )
    start = datetime.combine(start_date, datetime_time.min)
    end = datetime.combine(end_date + timedelta(days=1), datetime_time.min)
    with engine.connect() as connection:
        order_rows = connection.execute(
            select(orders.c.created_at, orders.c.subtotal, orders.c.total, orders.c.payment_status)
            .where(
                orders.c.created_at >= start,
                orders.c.created_at < end,
                orders.c.order_status != "cancelled",
            )
            .order_by(orders.c.created_at)
        ).mappings().all()
        item_rows = connection.execute(
            select(
                order_items.c.item_name,
                menu_items.c.category,
                order_items.c.quantity,
                order_items.c.unit_price,
                orders.c.payment_status,
            )
            .select_from(
                order_items.join(orders, orders.c.id == order_items.c.order_id)
                .outerjoin(menu_items, menu_items.c.id == order_items.c.menu_item_id)
            )
            .where(
                orders.c.created_at >= start,
                orders.c.created_at < end,
                orders.c.order_status != "cancelled",
            )
        ).mappings().all()
    daily: dict[str, dict] = {}
    paid_revenue = 0
    unpaid_total = 0
    paid_orders = 0
    for row in order_rows:
        key = row["created_at"].date().isoformat()
        record = daily.setdefault(key, {"date": key, "sales": 0, "orders": 0})
        record["orders"] += 1
        if row["payment_status"] == "paid":
            record["sales"] += row["subtotal"]
            paid_revenue += row["subtotal"]
            paid_orders += 1
        else:
            unpaid_total += row["total"]
    item_sales: dict[str, dict] = {}
    category_sales: dict[str, int] = {}
    for row in item_rows:
        if row["payment_status"] != "paid":
            continue
        item = item_sales.setdefault(row["item_name"], {"name": row["item_name"], "units": 0, "revenue": 0})
        item["units"] += row["quantity"]
        item["revenue"] += row["quantity"] * row["unit_price"]
        category = row["category"] or "Other"
        category_sales[category] = category_sales.get(category, 0) + row["quantity"] * row["unit_price"]
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "paid_order_count": paid_orders,
        "order_count": len(order_rows),
        "sales_revenue": paid_revenue,
        "unpaid_total": unpaid_total,
        "daily_sales": list(daily.values()),
        "top_items": sorted(item_sales.values(), key=lambda item: (-item["units"], item["name"]))[:10],
        "category_sales": [
            {"category": category, "revenue": revenue}
            for category, revenue in sorted(category_sales.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


@app.get("/api/reports/export.csv")
def export_order_data(start_date: date, end_date: date, _: AdminUser) -> StreamingResponse:
    if end_date < start_date or (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose a date range of at most 366 days",
        )
    start = datetime.combine(start_date, datetime_time.min)
    end = datetime.combine(end_date + timedelta(days=1), datetime_time.min)
    with engine.connect() as connection:
        rows = connection.execute(
            select(
                orders.c.id,
                orders.c.created_at,
                orders.c.order_type,
                orders.c.table_name,
                orders.c.guest_name,
                orders.c.payment_status,
                orders.c.order_status,
                orders.c.cancellation_reason,
                orders.c.subtotal,
                orders.c.tax,
                orders.c.total,
                orders.c.note,
                order_items.c.item_name,
                order_items.c.quantity,
                order_items.c.unit_price,
            )
            .select_from(orders.outerjoin(order_items, order_items.c.order_id == orders.c.id))
            .where(orders.c.created_at >= start, orders.c.created_at < end)
            .order_by(orders.c.created_at, orders.c.id, order_items.c.id)
        ).mappings().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["order_id", "created_at", "order_type", "table", "guest", "payment_status", "order_status", "cancellation_reason", "subtotal", "tax", "total", "note", "item", "quantity", "unit_price"]
    )

    def safe_spreadsheet_text(value: str | None) -> str:
        text = value or ""
        if text.lstrip().startswith(("=", "+", "-", "@")):
            return f"'{text}"
        return text

    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["created_at"].isoformat(sep=" "),
                safe_spreadsheet_text(row["order_type"]),
                safe_spreadsheet_text(row["table_name"]),
                safe_spreadsheet_text(row["guest_name"]),
                row["payment_status"],
                row["order_status"],
                safe_spreadsheet_text(row["cancellation_reason"]),
                row["subtotal"],
                row["tax"],
                row["total"],
                safe_spreadsheet_text(row["note"]),
                safe_spreadsheet_text(row["item_name"]),
                row["quantity"] or 0,
                row["unit_price"] or 0,
            ]
        )
    filename = f"restaurant-orders-{start_date.isoformat()}-to-{end_date.isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/customer/chat")
def customer_chat(payload: ChatRequest, customer: CustomerUser) -> dict:
    question = payload.question.strip()
    normalized = question.casefold()
    with engine.connect() as connection:
        menu = connection.execute(select(menu_items).order_by(menu_items.c.name)).mappings().all()
        last_order = connection.execute(
            select(orders.c.id, orders.c.payment_status, orders.c.created_at)
            .where(orders.c.customer_id == customer["id"])
            .order_by(orders.c.created_at.desc(), orders.c.id.desc())
            .limit(1)
        ).mappings().first()
        preferences = connection.execute(
            select(customer_preferences.c.dietary_preferences)
            .where(customer_preferences.c.customer_id == customer["id"])
        ).scalar_one_or_none() or []
    matched = next((item for item in menu if item["name"].casefold() in normalized), None)
    if any(word in normalized for word in ("order", "status", "track")) and last_order:
        answer = (
            f"Your latest order is #{last_order['id']} and payment is {last_order['payment_status']}. "
            f"Open Order history to see the kitchen checklist."
        )
    elif matched and any(word in normalized for word in ("allergen", "ingredient", "diet", "spicy", "calorie")):
        if not matched["dietary_verified"]:
            answer = (
                f"I don't have verified dietary information for {matched['name']}. "
                "Please confirm ingredients and allergen safety directly with restaurant staff."
            )
        else:
            tags = matched["dietary_tags"] or []
            calories = f"{matched['calories']} calories" if matched["calories"] is not None else "calories not recorded"
            spice = f"spice level {matched['spice_level']} out of 5" if matched["spice_level"] is not None else "spice level not recorded"
            answer = (
                f"{matched['name']} is {matched['price']} rupees. Verified dietary tags: "
                f"{', '.join(tags) if tags else 'none recorded'}. "
                f"Listed allergens: {matched['allergens_text'] or 'none recorded'}; "
                f"ingredients: {matched['ingredients_text'] or 'not recorded'}; {calories}; {spice}."
            )
    elif matched:
        answer = f"{matched['name']} is {matched['price']} rupees. {matched['description']}"
    elif "recommend" in normalized or "suggest" in normalized:
        answer = (
            f"Your saved dietary preferences are {', '.join(preferences) if preferences else 'none'}. "
            "Open Recommendations to see popular dishes filtered by verified menu data."
        )
    else:
        answer = (
            "I can answer menu price and description questions, show your latest order status, "
            "and point you to recommendations. For allergy safety, please confirm with restaurant staff."
        )
    with engine.begin() as connection:
        connection.execute(
            insert(chat_messages).values(
                customer_id=customer["id"],
                question=question,
                answer=answer,
            )
        )
    return {"question": question, "answer": answer}


# --- Table Reservations Endpoints ---
@app.post("/api/customer/reservations", status_code=status.HTTP_201_CREATED)
def create_customer_reservation(payload: ReservationInput, customer: CustomerUser) -> dict:
    with engine.begin() as connection:
        result = connection.execute(
            insert(table_reservations).values(
                customer_id=customer["id"],
                guest_name=payload.guest_name.strip(),
                contact_phone=payload.contact_phone.strip(),
                party_size=payload.party_size,
                reservation_date=payload.reservation_date,
                reservation_time=payload.reservation_time.strip(),
                table_number=payload.table_number.strip() if payload.table_number else None,
                special_requests=payload.special_requests.strip(),
                status="confirmed",
            )
        )
        row = connection.execute(
            select(table_reservations).where(table_reservations.c.id == result.inserted_primary_key[0])
        ).mappings().one()
    return dict(row)


@app.get("/api/customer/reservations")
def list_customer_reservations(customer: CustomerUser) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            select(table_reservations)
            .where(table_reservations.c.customer_id == customer["id"])
            .order_by(table_reservations.c.reservation_date.desc(), table_reservations.c.reservation_time.desc())
        ).mappings().all()
    return [dict(row) for row in rows]


@app.delete("/api/customer/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_customer_reservation(reservation_id: int, customer: CustomerUser) -> None:
    with engine.begin() as connection:
        res = connection.execute(
            update(table_reservations)
            .where(table_reservations.c.id == reservation_id, table_reservations.c.customer_id == customer["id"])
            .values(status="cancelled")
        )
        if res.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")


@app.get("/api/reservations")
@app.get("/api/admin/reservations")
def list_admin_reservations(
    _: FrontDeskUser,
    reservation_date: date | None = Query(default=None),
    status_filter: str | None = Query(default=None),
) -> list[dict]:
    stmt = select(table_reservations)
    if reservation_date:
        stmt = stmt.where(table_reservations.c.reservation_date == reservation_date)
    if status_filter:
        stmt = stmt.where(table_reservations.c.status == status_filter)
    stmt = stmt.order_by(table_reservations.c.reservation_date, table_reservations.c.reservation_time)
    with engine.connect() as connection:
        rows = connection.execute(stmt).mappings().all()
    return [dict(row) for row in rows]


@app.post("/api/admin/reservations", status_code=status.HTTP_201_CREATED)
def create_admin_reservation(payload: ReservationInput, _: FrontDeskUser) -> dict:
    with engine.begin() as connection:
        result = connection.execute(
            insert(table_reservations).values(
                customer_id=None,
                guest_name=payload.guest_name.strip(),
                contact_phone=payload.contact_phone.strip(),
                party_size=payload.party_size,
                reservation_date=payload.reservation_date,
                reservation_time=payload.reservation_time.strip(),
                table_number=payload.table_number.strip() if payload.table_number else None,
                special_requests=payload.special_requests.strip(),
                status="confirmed",
            )
        )
        row = connection.execute(
            select(table_reservations).where(table_reservations.c.id == result.inserted_primary_key[0])
        ).mappings().one()
    return dict(row)


@app.patch("/api/admin/reservations/{reservation_id}")
def update_admin_reservation(reservation_id: int, payload: ReservationStatusUpdate, _: FrontDeskUser) -> dict:
    with engine.begin() as connection:
        values = {"status": payload.status}
        if payload.table_number is not None:
            values["table_number"] = payload.table_number.strip() or None
        res = connection.execute(
            update(table_reservations)
            .where(table_reservations.c.id == reservation_id)
            .values(**values)
        )
        if res.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        row = connection.execute(
            select(table_reservations).where(table_reservations.c.id == reservation_id)
        ).mappings().one()
    return dict(row)


# --- Operating Expenses Endpoints ---
class ExpenseInput(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    category: str = Field(min_length=1, max_length=60)
    amount: int = Field(gt=0, le=100_000_000)
    note: str = Field(default="", max_length=255)


@app.get("/api/reports/expenses")
def list_operating_expenses(_: AdminUser, month: str | None = Query(default=None)) -> list[dict]:
    stmt = select(operating_expenses)
    if month:
        stmt = stmt.where(operating_expenses.c.month == month)
    stmt = stmt.order_by(operating_expenses.c.month.desc(), operating_expenses.c.id.desc())
    with engine.connect() as connection:
        rows = connection.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


@app.post("/api/reports/expenses", status_code=status.HTTP_201_CREATED)
def create_operating_expense(payload: ExpenseInput, _: AdminUser) -> dict:
    with engine.begin() as connection:
        result = connection.execute(
            insert(operating_expenses).values(
                month=payload.month,
                category=payload.category.strip(),
                amount=payload.amount,
                note=payload.note.strip(),
            )
        )
        row = connection.execute(
            select(operating_expenses).where(operating_expenses.c.id == result.inserted_primary_key[0])
        ).mappings().one()
    return dict(row)


# --- Festival Calendar Endpoints ---
class FestivalInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    uplift_percentage: Decimal = Field(default=Decimal("20.00"), ge=0, le=200)
    expense_inflation_percentage: Decimal = Field(default=Decimal("10.00"), ge=0, le=200)
    description: str = Field(default="", max_length=300)


@app.get("/api/admin/festivals")
def list_festivals(_: AdminUser) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            select(festival_calendar).order_by(festival_calendar.c.start_date.desc())
        ).mappings().all()
    return [dict(r) for r in rows]


@app.post("/api/admin/festivals", status_code=status.HTTP_201_CREATED)
def create_festival(payload: FestivalInput, _: AdminUser) -> dict:
    with engine.begin() as connection:
        res = connection.execute(
            insert(festival_calendar).values(
                name=payload.name.strip(),
                start_date=payload.start_date,
                end_date=payload.end_date,
                uplift_percentage=payload.uplift_percentage,
                expense_inflation_percentage=payload.expense_inflation_percentage,
                description=payload.description.strip(),
            )
        )
        row = connection.execute(
            select(festival_calendar).where(festival_calendar.c.id == res.inserted_primary_key[0])
        ).mappings().one()
    return dict(row)


@app.delete("/api/admin/festivals/{festival_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_festival(festival_id: int, _: AdminUser) -> None:
    with engine.begin() as connection:
        connection.execute(delete(festival_calendar).where(festival_calendar.c.id == festival_id))


# --- Comprehensive Sales & Profit Forecasting Endpoints ---
@app.get("/api/reports/forecast")
def get_sales_forecast(
    _: AdminUser,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    festival_uplift: bool = Query(default=True),
) -> dict:
    from backend.forecasting import calculate_comprehensive_forecast
    today = date.today()
    if month is not None:
        try:
            date.fromisoformat(f"{month}-01")
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Forecast month must be a valid YYYY-MM date",
            ) from exc
    else:
        month = (today.replace(day=28) + timedelta(days=4)).strftime("%Y-%m")

    with engine.connect() as connection:
        forecast_res = calculate_comprehensive_forecast(
            connection,
            orders,
            order_items,
            operating_expenses,
            festival_calendar,
            target_month_str=month,
            festival_uplift_enabled=festival_uplift,
            today=today,
        )

    # Persist forecast and model metrics to database if tables exist
    try:
        with engine.begin() as connection:
            if forecast_res.get("target_forecast"):
                connection.execute(
                    insert(sales_forecasts).values(
                        target_month=forecast_res["target_month"],
                        model_name=forecast_res["selected_best_model"],
                        predicted_revenue=forecast_res["target_forecast"]["forecast_revenue"],
                        predicted_profit=forecast_res["target_forecast"]["forecast_profit"],
                        confidence_min_revenue=forecast_res["target_forecast"]["confidence"]["revenue_min"],
                        confidence_max_revenue=forecast_res["target_forecast"]["confidence"]["revenue_max"],
                        confidence_min_profit=forecast_res["target_forecast"]["confidence"]["profit_min"],
                        confidence_max_profit=forecast_res["target_forecast"]["confidence"]["profit_max"],
                        actual_revenue=forecast_res["kpis"]["actual_revenue_this_month"] if forecast_res["is_current_month"] else None,
                        actual_profit=forecast_res["kpis"]["actual_profit_this_month"] if forecast_res["is_current_month"] else None,
                        is_current_month=forecast_res["is_current_month"],
                    )
                )
                best_m = forecast_res["selected_best_model"]
                best_stats = forecast_res.get("model_evaluation", {}).get("models", {}).get(best_m, {})
                if best_stats:
                    connection.execute(
                        insert(forecasting_model_metrics).values(
                            model_name=best_m,
                            mae=Decimal(str(best_stats.get("mae", 0))),
                            rmse=Decimal(str(best_stats.get("rmse", 0))),
                            mape=Decimal(str(best_stats.get("mape", 0))),
                            selected_as_best=True,
                            details=forecast_res.get("model_evaluation", {}).get("models"),
                        )
                    )
    except Exception:
        pass

    legacy_history = []
    for item in forecast_res.get("timeline", []):
        legacy_history.append({
            "month": item["month"],
            "sales": item["net_revenue"],
            "kind": item["kind"],
        })
    if legacy_history:
        forecast_res["history"] = legacy_history

    return forecast_res


@app.get("/api/reports/forecast/monthly")
def get_monthly_sales_forecast(
    _: AdminUser,
    festival_uplift: bool = Query(default=True),
) -> dict:
    from backend.forecasting import (
        calculate_comprehensive_forecast,
        get_festival_for_month,
        get_monthly_historical_aggregates,
    )

    today = date.today()
    months = ["2026-11", "2026-12", "2027-01", "2027-02", "2027-03"]
    current_month = today.strftime("%Y-%m")
    forecast_start = datetime(2026, 11, 1)
    forecast_end = datetime(2027, 4, 1)
    trend_multiplier = 1.0
    with engine.connect() as connection:
        monthly_history, _, _ = get_monthly_historical_aggregates(
            connection, orders, order_items, operating_expenses
        )
        recorded_expenses = {
            row["month"]: int(row["amount"] or 0)
            for row in connection.execute(
                select(operating_expenses.c.month, func.sum(operating_expenses.c.amount).label("amount"))
                .where(operating_expenses.c.month.in_(months))
                .group_by(operating_expenses.c.month)
            ).mappings()
        }
        missing_cost_months = {
            row["created_at"].strftime("%Y-%m")
            for row in connection.execute(
                select(orders.c.created_at)
                .select_from(order_items.join(orders, orders.c.id == order_items.c.order_id))
                .where(
                    orders.c.payment_status == "paid",
                    orders.c.order_status != "cancelled",
                    orders.c.created_at >= forecast_start,
                    orders.c.created_at < forecast_end,
                    order_items.c.unit_cost.is_(None),
                )
            ).mappings()
        }
        forecast_context = None
        forecast_target = next((month for month in months if month >= current_month), None)
        if forecast_target is not None:
            forecast_context = calculate_comprehensive_forecast(
                connection,
                orders,
                order_items,
                operating_expenses,
                festival_calendar,
                target_month_str=forecast_target,
                festival_uplift_enabled=festival_uplift,
                today=today,
            )

            completed_history = [
                row for month, row in sorted(monthly_history.items())
                if month <= current_month and month < current_month
            ]
            if not completed_history:
                completed_history = [
                    row for month, row in sorted(monthly_history.items())
                    if month <= current_month
                ]
            recent_history = completed_history[-3:]
            if recent_history:
                recent_revenue = sum(row["net_revenue"] for row in recent_history)
                food_cost_ratio = sum(row["food_cost"] for row in recent_history) / max(1, recent_revenue)
                average_operating_expenses = sum(
                    row["operating_expenses"] for row in recent_history
                ) / len(recent_history)
            else:
                food_cost_ratio = 0.32
                average_operating_expenses = 105000

            trend_multiplier = forecast_context.get("target_forecast", {}).get("trend_multiplier", 1.0)
            day_patterns = {
                row["day_index"]: row["avg_daily_revenue"]
                for row in forecast_context.get("day_of_week_patterns", [])
            }
            future_estimates = {}
            for month in months:
                if month <= current_month:
                    continue
                target_year, target_month_num = map(int, month.split("-"))
                days_in_month = calendar.monthrange(target_year, target_month_num)[1]
                festivals = get_festival_for_month(
                    connection, festival_calendar, target_year, target_month_num
                )
                uplift = (
                    20.0 if target_month_num in (3, 9, 10, 11, 12)
                    else max((float(row.get("uplift_percentage", 0)) for row in festivals), default=0.0)
                )
                if not festival_uplift:
                    uplift = 0.0
                baseline_revenue = sum(
                    day_patterns.get(date(target_year, target_month_num, day).weekday(), 0)
                    for day in range(1, days_in_month + 1)
                )
                forecast_revenue = round(baseline_revenue * (1 + uplift / 100) * trend_multiplier)
                forecast_expenses = (
                    round(forecast_revenue * food_cost_ratio)
                    + round(average_operating_expenses * (1.1 if festivals else 1.0))
                )
                if not forecast_context.get("historical_orders"):
                    forecast_revenue = 0
                    forecast_expenses = 0
                future_estimates[month] = {
                    "forecast_revenue": forecast_revenue,
                    "forecast_expenses": forecast_expenses,
                    "forecast_profit": forecast_revenue - forecast_expenses,
                    "festivals": [row["name"] for row in festivals],
                }
        else:
            future_estimates = {}

    result_months = []
    for month in months:
        history = monthly_history.get(month, {})
        if month < current_month:
            actual_revenue = int(history.get("net_revenue", 0))
            actual_expenses = int(history.get("food_cost", 0)) + recorded_expenses.get(month, 0)
            profit_complete = month in recorded_expenses and month not in missing_cost_months
            actual_profit = actual_revenue - actual_expenses if profit_complete else None
            result_months.append({
                "month": month,
                "status": "actual",
                "actual_revenue": actual_revenue,
                "predicted_revenue": None,
                "projected_revenue": actual_revenue,
                "actual_expenses": actual_expenses,
                "predicted_expenses": None,
                "projected_expenses": actual_expenses,
                "actual_net_profit": actual_profit,
                "predicted_net_profit": None,
                "projected_net_profit": actual_profit,
                "festivals": [],
                "profit_complete": profit_complete,
                "expense_note": "Historical item costs or operating expenses are missing" if not profit_complete else "Food costs and recorded operating expenses",
            })
            continue

        forecast_result = forecast_context or {}
        if month == current_month:
            breakdown = forecast_result.get("current_month_breakdown", {})
            result_months.append({
                "month": month,
                "status": "current",
                "actual_revenue": breakdown.get("actual_revenue_mtd", 0),
                "predicted_revenue": breakdown.get("predicted_remaining_revenue", 0),
                "projected_revenue": breakdown.get("forecast_full_month_revenue", 0),
                "actual_expenses": None,
                "predicted_expenses": breakdown.get("forecast_full_month_expenses", 0),
                "projected_expenses": breakdown.get("forecast_full_month_expenses", 0),
                "actual_net_profit": None,
                "predicted_net_profit": breakdown.get("forecast_full_month_profit", 0),
                "projected_net_profit": breakdown.get("forecast_full_month_profit", 0),
                "festivals": forecast_result.get("target_forecast", {}).get("festivals", []),
                "profit_complete": False,
                "expense_note": "Full-month expense estimate based on historical costs",
            })
            continue

        estimate = future_estimates.get(month, {
            "forecast_revenue": 0,
            "forecast_expenses": 0,
            "forecast_profit": 0,
            "festivals": [],
        })
        result_months.append({
            "month": month,
            "status": "forecast",
            "actual_revenue": None,
            "predicted_revenue": estimate["forecast_revenue"],
            "projected_revenue": estimate["forecast_revenue"],
            "actual_expenses": None,
            "predicted_expenses": estimate["forecast_expenses"],
            "projected_expenses": estimate["forecast_expenses"],
            "actual_net_profit": None,
            "predicted_net_profit": estimate["forecast_profit"],
            "projected_net_profit": estimate["forecast_profit"],
            "festivals": estimate["festivals"],
            "profit_complete": True,
            "expense_note": "Estimated from historical food costs and operating expenses",
        })

    return {
        "start_month": months[0],
        "end_month": months[-1],
        "generated_at": datetime.now().isoformat(),
        "trend_adjustment_percent": round((trend_multiplier - 1) * 100, 1),
        "demo_order_count": sum(row["demo_count"] for row in monthly_history.values()),
        "forecast_factors": ["historical paid sales", "recent sales trend", "weekday and weekend demand", "Indian festival calendar", "historical expenses"],
        "months": result_months,
    }


@app.post("/api/reports/forecast/refresh")
def refresh_sales_forecast(
    _: AdminUser,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    festival_uplift: bool = Query(default=True),
) -> dict:
    return get_sales_forecast(_=_, month=month, festival_uplift=festival_uplift)


@app.get("/api/orders")
def list_orders(_: AdminUser) -> list[dict]:
    with engine.connect() as connection:
        order_rows = connection.execute(select(orders).order_by(orders.c.id.desc()).limit(100)).mappings().all()
        result = []
        for order in order_rows:
            lines = connection.execute(
                select(
                    order_items.c.menu_item_id.label("item_id"),
                    order_items.c.item_name.label("name"),
                    order_items.c.unit_price.label("price"),
                    order_items.c.quantity,
                ).where(order_items.c.order_id == order["id"])
            ).mappings().all()
            result.append({**dict(order), "items": [dict(line) for line in lines]})
    return result


@app.get("/api/orders/unpaid")
def list_unpaid_orders(_: FrontDeskUser) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            select(orders, customers.c.display_name.label("customer_name"))
            .select_from(orders.outerjoin(customers, customers.c.id == orders.c.customer_id))
            .where(orders.c.payment_status == "unpaid", orders.c.order_status != "cancelled")
            .order_by(orders.c.created_at, orders.c.id)
            .limit(100)
        ).mappings().all()
        result = []
        for order in rows:
            lines = connection.execute(
                select(order_items.c.item_name.label("name"), order_items.c.quantity)
                .where(order_items.c.order_id == order["id"])
                .order_by(order_items.c.id)
            ).mappings().all()
            result.append(
                {
                    "id": order["id"],
                    "table_name": order["table_name"],
                    "customer_name": order["customer_name"],
                    "created_at": order["created_at"],
                    "total": order["total"],
                    "items": [dict(line) for line in lines],
                }
            )
    return result
