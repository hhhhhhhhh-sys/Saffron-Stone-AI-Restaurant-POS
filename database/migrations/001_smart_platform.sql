-- Run once against an existing restaurant_db database before deploying the smart platform.
-- Back up the database first; this migration preserves existing orders and menu items.

ALTER TABLE menu_items
  ADD COLUMN ingredients_text TEXT NULL,
  ADD COLUMN allergens_text TEXT NULL,
  ADD COLUMN dietary_tags JSON NULL,
  ADD COLUMN dietary_verified BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN spice_level INTEGER NULL,
  ADD COLUMN calories INTEGER NULL;

UPDATE menu_items SET ingredients_text = '' WHERE ingredients_text IS NULL;
UPDATE menu_items SET allergens_text = '' WHERE allergens_text IS NULL;

ALTER TABLE menu_items
  MODIFY COLUMN ingredients_text TEXT NOT NULL,
  MODIFY COLUMN allergens_text TEXT NOT NULL;

CREATE TABLE customers (
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

ALTER TABLE orders
  ADD COLUMN customer_id INT NULL,
  ADD COLUMN payment_status VARCHAR(16) NOT NULL DEFAULT 'paid',
  ADD COLUMN discount_amount INT NOT NULL DEFAULT 0,
  ADD COLUMN order_status VARCHAR(16) NOT NULL DEFAULT 'active',
  ADD COLUMN cancellation_reason VARCHAR(500) NULL,
  MODIFY COLUMN created_by INT NULL,
  ADD CONSTRAINT fk_orders_customer
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE SET NULL;

CREATE TABLE customer_sessions (
  token_hash VARCHAR(64) NOT NULL,
  customer_id INT NOT NULL,
  expires_at INT NOT NULL,
  PRIMARY KEY (token_hash),
  KEY ix_customer_sessions_expires_at (expires_at),
  CONSTRAINT fk_customer_sessions_customer
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE customer_preferences (
  customer_id INT NOT NULL,
  dietary_preferences JSON NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (customer_id),
  CONSTRAINT fk_customer_preferences_customer
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE restaurant_tables (
  id INT NOT NULL AUTO_INCREMENT,
  table_number VARCHAR(60) NOT NULL,
  token_hash VARCHAR(64) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_restaurant_tables_number (table_number),
  UNIQUE KEY uq_restaurant_tables_token (token_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE ingredients (
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

CREATE TABLE recipe_ingredients (
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

CREATE TABLE inventory_transactions (
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

CREATE TABLE loyalty_transactions (
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

CREATE TABLE chat_messages (
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
