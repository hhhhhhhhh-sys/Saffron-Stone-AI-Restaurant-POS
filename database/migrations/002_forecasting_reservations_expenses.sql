-- Migration 002: Table Reservations, Festival Calendar, Operating Expenses, Sales Forecasts, and Delivery Order Type
-- Run once against an existing restaurant_db database to enable advanced forecasting and reservations.

USE restaurant_db;

-- 1. Update orders table check constraint to support 'Delivery'
ALTER TABLE orders DROP CONSTRAINT ck_orders_type;
ALTER TABLE orders ADD CONSTRAINT ck_orders_type CHECK (order_type IN ('Dine in', 'Takeaway', 'Delivery'));

-- Add is_synthetic column if not present
SET @col_exists = (SELECT count(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'orders' AND column_name = 'is_synthetic');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE orders ADD COLUMN is_synthetic BOOLEAN NOT NULL DEFAULT FALSE, ADD INDEX ix_orders_synthetic (is_synthetic)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Mark existing demo orders as synthetic
UPDATE orders SET is_synthetic = TRUE WHERE note LIKE '[DEMO%';

-- 2. Table Reservations
CREATE TABLE IF NOT EXISTS table_reservations (
  id INT NOT NULL AUTO_INCREMENT,
  customer_id INT NULL,
  guest_name VARCHAR(120) NOT NULL,
  contact_phone VARCHAR(32) NOT NULL,
  party_size INT NOT NULL,
  reservation_date DATE NOT NULL,
  reservation_time TIME NOT NULL,
  table_number VARCHAR(60) NULL,
  special_requests VARCHAR(500) NOT NULL DEFAULT '',
  status VARCHAR(20) NOT NULL DEFAULT 'confirmed',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_reservations_date (reservation_date),
  CONSTRAINT ck_reservation_status CHECK (status IN ('confirmed', 'seated', 'completed', 'cancelled')),
  CONSTRAINT fk_reservations_customer FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Festival Calendar
CREATE TABLE IF NOT EXISTS festival_calendar (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  uplift_percentage DECIMAL(5,2) NOT NULL DEFAULT 20.00,
  expense_inflation_percentage DECIMAL(5,2) NOT NULL DEFAULT 10.00,
  description VARCHAR(300) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  KEY ix_festival_dates (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Operating Expenses
CREATE TABLE IF NOT EXISTS operating_expenses (
  id INT NOT NULL AUTO_INCREMENT,
  month VARCHAR(7) NOT NULL,
  category VARCHAR(60) NOT NULL,
  amount INT NOT NULL,
  note VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_operating_expenses_month (month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Sales Forecasts
CREATE TABLE IF NOT EXISTS sales_forecasts (
  id INT NOT NULL AUTO_INCREMENT,
  target_month VARCHAR(7) NOT NULL,
  generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  model_name VARCHAR(60) NOT NULL,
  predicted_revenue INT NOT NULL,
  predicted_profit INT NOT NULL,
  confidence_min_revenue INT NOT NULL,
  confidence_max_revenue INT NOT NULL,
  confidence_min_profit INT NOT NULL,
  confidence_max_profit INT NOT NULL,
  actual_revenue INT NULL,
  actual_profit INT NULL,
  is_current_month BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (id),
  KEY ix_sales_forecasts_month (target_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Forecasting Model Metrics
CREATE TABLE IF NOT EXISTS forecasting_model_metrics (
  id INT NOT NULL AUTO_INCREMENT,
  model_name VARCHAR(60) NOT NULL,
  evaluation_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  mae DECIMAL(12,2) NOT NULL,
  rmse DECIMAL(12,2) NOT NULL,
  mape DECIMAL(6,2) NOT NULL,
  selected_as_best BOOLEAN NOT NULL DEFAULT FALSE,
  details JSON NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
