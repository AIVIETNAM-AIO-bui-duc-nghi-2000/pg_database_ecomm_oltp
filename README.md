# E-Commerce OLTP Synthetic Data Pipeline

## Project Overview
This repository contains an end-to-end, high-performance Data Engineering pipeline designed to generate, process, and ingest relational synthetic data into an E-commerce PostgreSQL database. 

Built on industry standards, the architecture entirely bypasses legacy processing frameworks like Pandas. It leverages Polars for multi-threaded, in-memory data generation and ADBC (Arrow Database Connectivity) for high-speed, zero-copy binary ingestion into the OLTP system. 

The generated data strictly mirrors real-world e-commerce behaviors, including Google Merchant Center product naming conventions and Southeast Asian shopping traffic patterns.

## Business Value & Use Case
In the hyper-competitive global E-commerce market—especially during high-traffic events like Black Friday globally or Mega Flash Sales in Vietnam (e.g., Shopee, TikTok Shop)—a single data anomaly can cost a business billions. 

This pipeline serves as a **production-grade sandbox**. It provides a highly realistic, relational dataset tailored for:
1.  **Stress-Testing Backend APIs:** Generating millions of rows to test system load limits.
2.  **Prototyping ML Models:** Feeding clean, structured data into recommendation engines.
3.  **BI Dashboard Development:** Building financial and operational reports without exposing sensitive production PII (Personally Identifiable Information).

## Project Workflow
The pipeline strictly follows a 4-stage execution flow to guarantee data integrity and idempotency:

1.  **Define the Schema:** The database architecture and table constraints are initialized automatically via Docker using standard DDL scripts.
2.  **Generate Data:** Realistic mock data is synthesized in memory using Python `Faker` and `Polars` DataFrames across 8 normalized tables. This includes generating globally unique identifiers (UUID v4) for transactions and simulating realistic human shopping times (e.g., Mega Sales, paydays, and nighttime traffic spikes).
3.  **Convert Data Types:** Explicit type casting is applied in-memory (e.g., keeping specific IDs as 10-digit Strings, and casting floating-point financial values to String, then to `DECIMAL(15,2)`). This ensures strict compliance with the target database schema and prevents precision loss during binary transfer.
4.  **Insert Data:** Data is ingested directly into PostgreSQL using the ADBC driver, utilizing `TRUNCATE CASCADE` beforehand to ensure idempotent runs without data duplication.

## Architecture & Tech Stack
* **Infrastructure:** Docker & Docker Compose (Containerized PostgreSQL 16+).
* **Environment Management:** Python 3.12+, Poetry (Strict dependency locking).
* **Data Generation:** Faker.
* **In-Memory Engine:** Polars.
* **Database Ingestion:** ADBC Driver, SQLAlchemy (for connection URI management only).
* **Automated Testing:** Pytest.

## Enterprise Testing Strategy
To ensure the pipeline is robust and CI/CD-ready, it employs a two-layer testing architecture:

* **Layer 1: Unit Testing (In-Memory Data Contracts):** Validates the data generated in RAM before it hits the database. It ensures columns have the correct data types, no negative prices exist, and strings meet length requirements.
* **Layer 2: Integration Testing (Physical Database):** Verifies the actual physical structure and business logic inside PostgreSQL. It tests for:
    * **Financial Logic:** Ensures no product has a `discount_price` greater than its regular `price` (preventing negative margins).
    * **Referential Integrity:** Ensures no orphan records exist (e.g., a product cannot link to a non-existent brand).
    * **Idempotency:** Proves the database handles multiple runs without duplicating `product_id`s.
* **Automated Logging:** Driven by `pytest.ini`, all test executions automatically generate human-readable `.log` files and CI/CD-compatible `.xml` reports in the `logs/` directory.

## Database Schema & Data Dictionary
The pipeline populates a normalized relational model consisting of 8 tables. Below is the core data dictionary:

* **brands:** `brand_id` (PK), `brand_name`, `country`, `created_at`
* **categories:** `category_id` (PK), `category_name`, `parent_category_id`, `level`, `created_at`
* **sellers:** `seller_id` (VARCHAR(10) PK), `seller_name`, `join_date`, `seller_type`, `rating`, `country`
* **products:** `product_id` (VARCHAR(10) PK), `product_name` (Google Merchant Center Standard), `category_id` (FK), `brand_id` (FK), `seller_id` (FK), `price` (Decimal), `discount_price` (Decimal), `stock_qty`, `rating`, `created_at`, `is_active`
* **promotions:** `promotion_id` (PK), `promotion_name`, `promotion_type`, `discount_type`, `discount_value` (Decimal), `start_date`, `end_date`
* **promotion_products:** `promo_product_id` (PK), `promotion_id` (FK), `product_id` (FK), `created_at`
* **orders:** `order_id` (UUID v4 PK), `order_date`, `seller_id` (FK), `status`, `total_amount` (Decimal), `created_at` (Simulated Human Behavior Timestamp)
* **order_items:** `order_item_id` (UUID v4 PK), `order_id` (FK), `product_id` (FK), `order_date`, `quantity`, `unit_price` (Decimal), `subtotal` (Decimal), `created_at`

## Quick Start Guide

### 1. Prerequisites
Ensure the following tools are installed on your local environment (WSL2/Linux recommended):
* Docker & Docker Compose
* Python 3.12+
* Poetry

### 2. Environment Setup
Clone the repository and set up your local configuration:
```bash
cp .env.example .env
```
Install all locked dependencies:
```bash
poetry install
```

### 3. Environment Configuration
The pipeline relies on the following environment variables. Define these in your `.env` file:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `POSTGRES_HOST` | Database server address | `localhost` or `127.0.0.1` |
| `POSTGRES_PORT` | Port for the database connection | `5433` |
| `POSTGRES_USER` | Admin username for PostgreSQL | `ecomm_admin` |
| `POSTGRES_PASSWORD`| Admin password | *Must be set securely* |
| `POSTGRES_DB` | Name of the target database | `ecomm_oltp` |

### 4. Start Infrastructure
Provision the PostgreSQL container. The initialization script (`init_scripts/01_init_schema.sql`) will automatically execute on the first volume creation to build the schema.
```bash
docker-compose up -d
```

### 5. Execute Pipeline
Run the main orchestrator to trigger the generation and ingestion workflow.
```bash
poetry run python main.py
```

### 6. Run Automated Tests
Before deploying, validate data contracts, business logic, and database integrity:
```bash
poetry run pytest
```
*Note: Thanks to `pytest.ini`, you do not need to add logging flags. Test results will automatically be saved to `logs/integration_test.log` and `logs/test_report.xml`.*

## Repository Structure
```text
PG_DATABASE_ECOMM_OLTP/
├── .github/workflows/
│   └── ci.yml                      # Automated CI/CD pipeline configuration
├── configs/
│   └── settings.py                 # Environment variables loader
├── init_scripts/
│   └── 01_init_schema.sql          # Automated DDL script for Docker Postgres
├── logs/
│   └── .gitkeep                    # Ensures directory tracking in version control
├── src/
│   ├── generator.py                # Faker data synthesis logic
│   ├── logger.py                   # Custom logging configuration
│   └── postgres_loader.py          # ADBC ingestion logic
├── tests/
│   ├── integration/
│   │   └── test_db_integration.py  # DB integrity and business logic tests
│   └── unit/
│   │   └── test_data_contracts.py  # In-memory schema validation
├── .env.example                    # Template for environment variables
├── .gitignore                      # Standardized version control exclusions
├── docker-compose.yml              # Infrastructure state definition
├── LICENSE                         # MIT License for open-source distribution
├── main.py                         # The pipeline orchestrator
├── poetry.lock                     # Locked dependency tree
├── pyproject.toml                  # Project metadata and requirements
├── pytest.ini                      # Automated test logging configuration
└── README.md                       # Project documentation and setup guide
```