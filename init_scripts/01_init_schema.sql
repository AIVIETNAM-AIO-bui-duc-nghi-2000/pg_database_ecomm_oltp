-- 01_init_schema.sql
-- This script creates all tables for the E-commerce system.
-- ====================================================================
-- STEP 0: CLEAN UP
-- Delete old tables if they exist to start fresh.
-- ====================================================================
DROP TABLE IF EXISTS promotion_products CASCADE;
DROP TABLE IF EXISTS promotions CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS sellers CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS brands CASCADE;
-- ====================================================================
-- STEP 1: CORE TABLES
-- ====================================================================
-- Create the brands table to store company names and countries.
-- We use TIMESTAMPTZ to save the timezone. This helps when
-- people use the system from different countries.
CREATE TABLE IF NOT EXISTS brands (
    brand_id INTEGER PRIMARY KEY,
    brand_name VARCHAR(255) NOT NULL,
    country VARCHAR(10) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
-- Create the categories table for product groups.
-- It connects to itself to allow sub-categories.
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL,
    parent_category_id INTEGER REFERENCES categories(category_id),
    level INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
-- Create the sellers table to store shop information.
-- SỬA: Đổi seller_id từ INTEGER thành VARCHAR(10)
CREATE TABLE IF NOT EXISTS sellers (
    seller_id VARCHAR(10) PRIMARY KEY,
    seller_name VARCHAR(255) NOT NULL,
    join_date DATE NOT NULL,
    seller_type VARCHAR(50),
    rating REAL,
    country VARCHAR(10) NOT NULL
);
-- ====================================================================
-- STEP 2: PRODUCT TABLES
-- ====================================================================
-- Create the products table with prices, stock, and links to sellers.
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(10) PRIMARY KEY,
    product_name VARCHAR(500) NOT NULL,
    category_id INTEGER REFERENCES categories(category_id),
    brand_id INTEGER REFERENCES brands(brand_id),
    seller_id VARCHAR(10) REFERENCES sellers(seller_id),
    price DECIMAL(15, 2) NOT NULL,
    discount_price DECIMAL(15, 2),
    stock_qty INTEGER DEFAULT 0,
    rating REAL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
-- ====================================================================
-- STEP 3: PROMOTION TABLES
-- ====================================================================
-- Create the promotions table to store discount rules and dates.
CREATE TABLE IF NOT EXISTS promotions (
    promotion_id INTEGER PRIMARY KEY,
    promotion_name VARCHAR(255) NOT NULL,
    promotion_type VARCHAR(50) NOT NULL,
    discount_type VARCHAR(50) NOT NULL,
    discount_value DECIMAL(15, 2) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);
-- Create a link table to connect products with promotions.
-- SỬA: Đổi product_id từ INTEGER thành VARCHAR(10)
CREATE TABLE IF NOT EXISTS promotion_products (
    promo_product_id INTEGER PRIMARY KEY,
    promotion_id INTEGER REFERENCES promotions(promotion_id),
    product_id VARCHAR(10) REFERENCES products(product_id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
-- ====================================================================
-- STEP 4: ORDER TABLES (HIGH-SCALE ARCHITECTURE WITH FOREIGN KEYS)
-- ====================================================================
-- Create the main orders table.
CREATE TABLE orders (
    order_id VARCHAR(36) PRIMARY KEY,
    order_date TIMESTAMPTZ NOT NULL,
    seller_id VARCHAR(10) NOT NULL REFERENCES sellers(seller_id),
    status VARCHAR(20) NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
-- Create the order_items table to store products inside each order.
CREATE TABLE order_items (
    order_item_id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL REFERENCES orders(order_id) ON DELETE RESTRICT,
    product_id VARCHAR(10) NOT NULL REFERENCES products(product_id),
    order_date TIMESTAMPTZ NOT NULL,
    quantity INT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
-- ====================================================================
-- STEP 5: PERFORMANCE OPTIMIZATION
-- ====================================================================
-- Create indexes to make data searching and table joining faster.
-- This helps the database run quickly when the data grows very large.
CREATE INDEX idx_orders_seller ON orders(seller_id);
CREATE INDEX idx_order_item_orders ON order_items(order_id);
CREATE INDEX idx_order_item_product ON order_items(product_id);