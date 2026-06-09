import os
from typing import Any, Dict, List
from pathlib import Path
from dotenv import load_dotenv

# ==========================================
# SYSTEM ENVIRONMENT SETUP
# ==========================================
# We use Path to find exactly where this project is located on your computer.
# This makes sure the code can always find the '.env' file, even if you run 
# the program from a different folder.
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'

# Load secret settings (like database passwords) from the .env file.
load_dotenv(dotenv_path=env_path)

# ==========================================
# 1. DATA VOLUME SETTINGS (SIZE OF THE STORE)
# ==========================================
# These numbers decide how many items we create for our fake shop.
# We need enough sellers and products so the data looks like a real business.
DATA_VOLUMES: Dict[str, int] = {
    "brand": 50,
    "category": 20,
    "seller": 500,        # We use many sellers to simulate a big marketplace.
    "product": 5000,
    "promotion": 50,      # Many sales campaigns make reports more interesting.
    "promotion_product": 1500,
}

# The number of orders we want to generate.
# We read this from the .env file. 
# If .env is empty, it uses 1000 and 2000. This is "Safe Mode" for your computer.
# On a powerful server, we will set this to 3,000,000 in the .env file.
ORDER_MIN_VOLUME = int(os.getenv("ORDER_MIN_VOLUME", 1000))
ORDER_MAX_VOLUME = int(os.getenv("ORDER_MAX_VOLUME", 2000))

# ==========================================
# 2. BUSINESS RULES (HOW CUSTOMERS SHOP)
# ==========================================
# All orders will be created between these two dates (3 months of data).
ORDER_START_DATE = "2025-08-01"
ORDER_END_DATE = "2025-10-31"

# How many different products a customer usually puts in their shopping cart.
ITEMS_PER_ORDER_MIN = 3
ITEMS_PER_ORDER_MAX = 4

# Maximum quantity allowed for one single product in one order.
# This prevents a fake customer from buying 1000 iPhones at once.
MAX_QTY_PER_ORDER_ITEM = 5

# This describes how often an order is successful or cancelled.
# For example, 70% of orders are "DELIVERED" (successful).
ORDER_STATUS_DISTRIBUTION = {
    "PLACED": 0.05,
    "PAID": 0.04,
    "DELIVERED": 0.70,
    "SHIPPED": 0.11,
    "CANCELLED": 0.07,
    "RETURNED": 0.03
}

# ==========================================
# 3. SYSTEM PERFORMANCE (SPEED AND SAFETY)
# ==========================================
# BATCH_SIZE is the number of records the computer handles at one time.
# Processing 100,000 rows at once is fast, but it uses RAM. 
# If your computer is slow, make this number smaller.
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100000))

# RANDOM_SEED makes sure the fake data is exactly the same every time you run it.
# This is very helpful when you want to find and fix errors (debugging).
_seed_env = os.getenv("RANDOM_SEED", "42")
RANDOM_SEED = int(_seed_env) if _seed_env.lower() != "none" else None

# LOG_LEVEL decide how much information the program prints on your screen.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ==========================================
# 4. LOCATION AND TIME SETTINGS
# ==========================================
DEFAULT_CURRENCY = "VND"
DEFAULT_COUNTRY_CODE = "VN"
# Using the Vietnam timezone (Asia/Ho_Chi_Minh) ensures that sales 
# are recorded on the correct day for local business reports.
SYSTEM_TIMEZONE = "Asia/Ho_Chi_Minh" 

# ==========================================
# 5. DATABASE CONNECTION (POSTGRESQL)
# ==========================================
# We get these login details from the .env file for security.
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "ecomm_db")

# This is the final link used by Python to talk to the database.
DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ==========================================
# 6. PRODUCT CATEGORIES (GOOGLE STANDARD)
# ==========================================
# We follow the "Google Product Taxonomy". This is a world-wide standard.
# It makes it easy to connect our data with Google Ads or Facebook Catalog later.
CATEGORIES_HIERARCHY: List[Dict[str, Any]] = [
    {"id": 1, "name": "Apparel & Accessories", "parent": None, "level": 1},
    {"id": 2, "name": "Electronics", "parent": None, "level": 1},
    {"id": 3, "name": "Home & Garden", "parent": None, "level": 1},
    {"id": 4, "name": "Clothing", "parent": 1, "level": 2},
    {"id": 5, "name": "Shoes", "parent": 1, "level": 2},
    {"id": 6, "name": "Computers", "parent": 2, "level": 2},
    {"id": 7, "name": "Communications", "parent": 2, "level": 2},
    {"id": 8, "name": "Audio", "parent": 2, "level": 2},
    {"id": 9, "name": "Kitchen & Dining", "parent": 3, "level": 2},
    {"id": 10, "name": "Furniture", "parent": 3, "level": 2},
]