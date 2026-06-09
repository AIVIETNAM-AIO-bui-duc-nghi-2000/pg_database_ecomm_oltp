import logging
import pytest
import sqlalchemy
from src.postgres_loader import get_db_uri

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def db_engine():
    logger.info("Setting up database engine for integration tests...")
    db_uri = get_db_uri()
    engine = sqlalchemy.create_engine(db_uri)
    yield engine
    logger.info("Tearing down database engine. Tests complete.")
    engine.dispose()

def test_database_connection(db_engine):
    logger.info("Executing test_database_connection...")
    try:
        with db_engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT 1"))
            assert result.scalar() == 1
            logger.info("SUCCESS: Database connection established.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        pytest.fail(f"Database connection failed: {e}")

def test_tables_have_data(db_engine):
    logger.info("Executing test_tables_have_data...")
    # SỬA TẠI ĐÂY: Đã đưa orders và order_items vào tầm ngắm kiểm tra dữ liệu thực tế
    expected_tables = [
        "brands", "categories", "sellers", "products", 
        "promotions", "promotion_products", "orders", "order_items"
    ]
    
    with db_engine.connect() as conn:
        for table in expected_tables:
            result = conn.execute(sqlalchemy.text(f"SELECT COUNT(*) FROM {table}"))
            row_count = result.scalar()
            
            logger.info(f"Table '{table}' row count: {row_count}")
            assert row_count > 0, f"Integration Error: The '{table}' table is completely empty!"

def test_financial_logic_validity(db_engine):
    logger.info("Executing test_financial_logic_validity...")
    query = sqlalchemy.text("""
        SELECT COUNT(*) 
        FROM products 
        WHERE discount_price > price;
    """)
    with db_engine.connect() as conn:
        invalid_rows = conn.execute(query).scalar()
        if invalid_rows > 0:
            logger.error(f"Found {invalid_rows} products violating financial constraints.")
        assert invalid_rows == 0, f"Critical Error: Found {invalid_rows} products with discount_price > price!"
        logger.info("SUCCESS: All financial constraints are valid.")

def test_referential_integrity_products(db_engine):
    logger.info("Executing test_referential_integrity_products...")
    query = sqlalchemy.text("""
        SELECT COUNT(*) 
        FROM products p
        LEFT JOIN brands b ON p.brand_id = b.brand_id
        WHERE b.brand_id IS NULL;
    """)
    with db_engine.connect() as conn:
        orphan_rows = conn.execute(query).scalar()
        if orphan_rows > 0:
            logger.error(f"Found {orphan_rows} orphan products.")
        assert orphan_rows == 0, f"Data Integrity Error: Found {orphan_rows} orphan products missing valid foreign keys!"
        logger.info("SUCCESS: No orphan records found in products table.")

def test_no_duplicate_records(db_engine):
    logger.info("Executing test_no_duplicate_records...")
    query = sqlalchemy.text("""
        SELECT COUNT(*) 
        FROM (
            SELECT product_id 
            FROM products 
            GROUP BY product_id 
            HAVING COUNT(*) > 1
        ) as duplicates;
    """)
    with db_engine.connect() as conn:
        duplicate_rows = conn.execute(query).scalar()
        if duplicate_rows > 0:
            logger.error(f"Found {duplicate_rows} duplicated product IDs.")
        assert duplicate_rows == 0, f"Idempotency Error: Found {duplicate_rows} duplicate product_ids!"
        logger.info("SUCCESS: Idempotency confirmed. No duplicates found.")

def test_schema_data_types(db_engine):
    logger.info("Executing test_schema_data_types...")
    query = sqlalchemy.text("""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'price';
    """)
    with db_engine.connect() as conn:
        result = conn.execute(query).scalar()
        logger.info(f"Physical data type for 'products.price' is: {result}")
        assert result.upper() == "NUMERIC", f"Schema Error: 'price' column should be NUMERIC, but found {result}."
        logger.info("SUCCESS: Physical database schema aligns with Data Contracts.")