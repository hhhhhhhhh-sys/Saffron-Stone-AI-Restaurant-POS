CREATE DATABASE IF NOT EXISTS restaurant_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE restaurant_db;

CREATE TABLE IF NOT EXISTS users (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(80) NOT NULL,
  display_name VARCHAR(120) NOT NULL,
  role VARCHAR(16) NOT NULL,
  employee_type VARCHAR(16) NOT NULL DEFAULT 'reception',
  password_hash VARCHAR(256) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  CONSTRAINT ck_users_role CHECK (role IN ('admin', 'staff'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sessions (
  token_hash VARCHAR(64) NOT NULL,
  user_id INT NOT NULL,
  expires_at INT NOT NULL,
  PRIMARY KEY (token_hash),
  KEY ix_sessions_expires_at (expires_at),
  CONSTRAINT fk_sessions_user
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS menu_items (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  category VARCHAR(60) NOT NULL,
  price INT NOT NULL,
  cost_price INT NULL,
  description VARCHAR(300) NOT NULL DEFAULT '',
  popular TINYINT(1) NOT NULL DEFAULT 0,
  image VARCHAR(120) NOT NULL DEFAULT 'photo-1546833999-b9f581a1996d',
  ingredients_text TEXT NOT NULL,
  allergens_text TEXT NOT NULL,
  dietary_tags JSON NULL,
  dietary_verified BOOLEAN NOT NULL DEFAULT FALSE,
  spice_level INTEGER NULL,
  calories INTEGER NULL,
  PRIMARY KEY (id),
  CONSTRAINT ck_menu_items_price_positive CHECK (price > 0),
  CONSTRAINT ck_menu_items_cost_nonnegative CHECK (cost_price IS NULL OR cost_price >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS customers (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(80) NOT NULL,
  display_name VARCHAR(120) NOT NULL,
  email VARCHAR(254) NULL,
  password_hash VARCHAR(256) NOT NULL,
  loyalty_points INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (id),
  UNIQUE KEY uq_customers_username (username),
  UNIQUE KEY uq_customers_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS orders (
  id INT NOT NULL AUTO_INCREMENT,
  order_type VARCHAR(16) NOT NULL,
  table_name VARCHAR(60) NULL,
  guest_name VARCHAR(120) NULL,
  note VARCHAR(500) NOT NULL DEFAULT '',
  subtotal INT NOT NULL,
  tax INT NOT NULL,
  total INT NOT NULL,
  cash_received INT NOT NULL,
  change_due INT NOT NULL,
  created_by INT NULL,
  customer_id INT NULL,
  payment_status VARCHAR(16) NOT NULL DEFAULT 'paid',
  discount_amount INT NOT NULL DEFAULT 0,
  order_status VARCHAR(16) NOT NULL DEFAULT 'active',
  cancellation_reason VARCHAR(500) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_orders_created_at (created_at),
  CONSTRAINT ck_orders_type CHECK (order_type IN ('Dine in', 'Takeaway')),
  CONSTRAINT fk_orders_user FOREIGN KEY (created_by) REFERENCES users (id),
  CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS order_items (
  id INT NOT NULL AUTO_INCREMENT,
  order_id INT NOT NULL,
  menu_item_id INT NULL,
  item_name VARCHAR(120) NOT NULL,
  unit_price INT NOT NULL,
  unit_cost INT NULL,
  quantity INT NOT NULL,
  prep_status VARCHAR(16) NOT NULL DEFAULT 'queued',
  PRIMARY KEY (id),
  KEY ix_order_items_order_id (order_id),
  CONSTRAINT ck_order_items_quantity_positive CHECK (quantity > 0),
  CONSTRAINT ck_order_items_cost_nonnegative CHECK (unit_cost IS NULL OR unit_cost >= 0),
  CONSTRAINT fk_order_items_order
    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
  CONSTRAINT fk_order_items_menu_item
    FOREIGN KEY (menu_item_id) REFERENCES menu_items (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS customer_sessions (
  token_hash VARCHAR(64) NOT NULL,
  customer_id INT NOT NULL,
  expires_at INT NOT NULL,
  PRIMARY KEY (token_hash),
  KEY ix_customer_sessions_expires_at (expires_at),
  CONSTRAINT fk_customer_sessions_customer
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS customer_preferences (
  customer_id INT NOT NULL,
  dietary_preferences JSON NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (customer_id),
  CONSTRAINT fk_customer_preferences_customer
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS restaurant_tables (
  id INT NOT NULL AUTO_INCREMENT,
  table_number VARCHAR(60) NOT NULL,
  token_hash VARCHAR(64) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_restaurant_tables_number (table_number),
  UNIQUE KEY uq_restaurant_tables_token (token_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ingredients (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  unit VARCHAR(24) NOT NULL,
  quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
  minimum_quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
  expires_at DATE NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_ingredients_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recipe_ingredients (
  id INT NOT NULL AUTO_INCREMENT,
  menu_item_id INT NOT NULL,
  ingredient_id INT NOT NULL,
  quantity_per_item DECIMAL(12,3) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_recipe_menu_ingredient (menu_item_id, ingredient_id),
  CONSTRAINT fk_recipe_menu_item
    FOREIGN KEY (menu_item_id) REFERENCES menu_items (id) ON DELETE CASCADE,
  CONSTRAINT fk_recipe_ingredient
    FOREIGN KEY (ingredient_id) REFERENCES ingredients (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS inventory_transactions (
  id INT NOT NULL AUTO_INCREMENT,
  ingredient_id INT NOT NULL,
  order_id INT NULL,
  order_item_id INT NULL,
  quantity_delta DECIMAL(12,3) NOT NULL,
  reason VARCHAR(160) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_inventory_transactions_created_at (created_at),
  KEY ix_inventory_transactions_order_item (order_item_id),
  CONSTRAINT fk_inventory_transaction_ingredient
    FOREIGN KEY (ingredient_id) REFERENCES ingredients (id),
  CONSTRAINT fk_inventory_transaction_order
    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE SET NULL,
  CONSTRAINT fk_inventory_transaction_order_item
    FOREIGN KEY (order_item_id) REFERENCES order_items (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS loyalty_transactions (
  id INT NOT NULL AUTO_INCREMENT,
  customer_id INT NOT NULL,
  order_id INT NULL,
  points_delta INT NOT NULL,
  reason VARCHAR(80) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_loyalty_order_reason (order_id, reason),
  KEY ix_loyalty_customer_created (customer_id, created_at),
  CONSTRAINT fk_loyalty_customer
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
  CONSTRAINT fk_loyalty_order
    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_messages (
  id INT NOT NULL AUTO_INCREMENT,
  customer_id INT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_chat_messages_customer_created (customer_id, created_at),
  CONSTRAINT fk_chat_customer
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
