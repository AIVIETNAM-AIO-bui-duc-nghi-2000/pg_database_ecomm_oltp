import pytest
import polars as pl

# Import settings and generator functions
from configs import settings
from src.generator import (
    generate_brands,
    generate_categories,
    generate_sellers,
    generate_products
)

# --- SETUP ---

@pytest.fixture(scope="module")
def sample_data():
    """Make all fake data one time only.
    
    We share this data with all tests below to save time.
    """
    brands = generate_brands()
    categories = generate_categories()
    sellers = generate_sellers()
    
    products = generate_products(
        brand_ids=brands["brand_id"].to_list(),
        category_ids=categories["category_id"].to_list(),
        seller_ids=sellers["seller_id"].to_list()
    )
    
    return {
        "brands": brands,
        "categories": categories,
        "sellers": sellers,
        "products": products
    }

# --- TEST 1: ROW COUNTS ---

def test_row_counts(sample_data):
    """Check if the number of rows is exactly what we want."""
    assert sample_data["brands"].height == settings.DATA_VOLUMES["brand"]
    assert sample_data["products"].height == settings.DATA_VOLUMES["product"]
    assert sample_data["sellers"].height == settings.DATA_VOLUMES["seller"]

# --- TEST 2: DATA TYPES ---

def test_data_types(sample_data):
    """Check if columns have the correct data type for the database."""
    df_product = sample_data["products"]
    schema = df_product.schema
    
    # Check basic types
    assert schema["product_id"] == pl.Int32
    assert schema["price"] == pl.Float64
    assert schema["is_active"] == pl.Boolean
    
    # SỬA TẠI ĐÂY: Đồng bộ dùng settings.SYSTEM_TIMEZONE thay vì "UTC" để khớp main.py
    assert schema["created_at"] == pl.Datetime("us", settings.SYSTEM_TIMEZONE)

# --- TEST 3: BUSINESS RULES ---

def test_discount_price(sample_data):
    """Check: Discount price must be equal or lower than the normal price."""
    df_product = sample_data["products"]
    
    # Find bad rows where discount > normal price
    bad_rows = df_product.filter(pl.col("discount_price") > pl.col("price"))
    
    # The number of bad rows must be zero
    assert bad_rows.height == 0, "Error: Discount is higher than price."

def test_rating_range(sample_data):
    """Check: Rating must be from 3.0 to 5.0."""
    df_product = sample_data["products"]
    
    # Find bad rows where rating is < 3.0 or > 5.0
    bad_rows = df_product.filter(
        (pl.col("rating") < 3.0) | (pl.col("rating") > 5.0)
    )
    
    assert bad_rows.height == 0, "Error: Rating is not between 3.0 and 5.0."

# --- TEST 4: FOREIGN KEYS (LINKS) ---

def test_category_links(sample_data):
    """Check: Every product must belong to a real category."""
    df_product = sample_data["products"]
    df_category = sample_data["categories"]
    
    # Get the unique category IDs
    used_ids = df_product["category_id"].unique()
    real_ids = df_category["category_id"].unique()
    
    # Check if all used IDs exist in the real IDs list
    is_safe = used_ids.is_in(real_ids.to_list()).all()
    
    assert is_safe, "Error: A product uses a fake category ID."