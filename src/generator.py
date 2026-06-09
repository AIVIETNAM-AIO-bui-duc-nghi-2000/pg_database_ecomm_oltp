import random
import uuid
from typing import List, Dict, Tuple, Iterator
from datetime import datetime, timedelta
import polars as pl
from faker import Faker

# Load settings from the configuration file.
from configs import settings

# Set up the tool to create fake data.
fake = Faker()
if settings.RANDOM_SEED is not None:
    Faker.seed(settings.RANDOM_SEED)
    random.seed(settings.RANDOM_SEED)

SYSTEM_START_DATE = datetime.strptime(settings.ORDER_START_DATE, "%Y-%m-%d")
SYSTEM_END_DATE = datetime.strptime(settings.ORDER_END_DATE, "%Y-%m-%d")


def generate_seller_name() -> str:
    """
    Generate realistic e-commerce seller names targeting the Vietnamese market.
    Mixes unaccented Vietnamese, English, and French terms to simulate real shop names.
    Only uses basic Latin characters.
    """
    vn_prefixes = ["Thanh", "Binh", "Hanh", "Phuc", "Phat", "Tai", "Loc", "Gia", "Bao", "Ngoc", "Hoang", "Kim", "Xuan", "Thu"]
    vn_suffixes = ["Phat", "Dat", "Vuong", "Sinh", "An", "Minh", "Khang"]
    en_words = ["Store", "Shop", "Mart", "Trading", "Global", "Tech", "Fashion", "Beauty", "Official"]
    fr_words = ["Maison", "Boutique", "Atelier", "Chateau", "Paris", "Lumiere"]

    chance = random.random()
    if chance < 0.4:
        name = f"{random.choice(vn_prefixes)} {random.choice(vn_suffixes)} {random.choice(['Store', 'Shop', ''])}"
    elif chance < 0.7:
        name = f"{random.choice(vn_prefixes)} {random.choice(en_words)}"
    elif chance < 0.9:
        name = f"{fake.word().capitalize()} {random.choice(en_words)}"
    else:
        name = f"{random.choice(fr_words)} {random.choice(vn_prefixes + fr_words)}"
        
    return name.strip()


def generate_brands() -> pl.DataFrame:
    num_rows = settings.DATA_VOLUMES["brand"]
    data = [
        {
            "brand_id": i,
            "brand_name": fake.company(),
            "country": settings.DEFAULT_COUNTRY_CODE,
            # Brands must exist before the system starts taking orders.
            "created_at": fake.date_time_between(start_date="-5y", end_date=SYSTEM_START_DATE),
        }
        for i in range(1, num_rows + 1)
    ]

    return pl.DataFrame(data).with_columns([
        pl.col("brand_id").cast(pl.Int32),
        pl.col("brand_name").cast(pl.String),
        pl.col("country").cast(pl.String),
        pl.col("created_at").cast(pl.Datetime("us", settings.SYSTEM_TIMEZONE)),
    ])


def generate_categories() -> pl.DataFrame:
    """Load the category list from the settings.
    
    Master data like categories are imported at the very beginning of the 
    system build. So, they all share the exact same old date (e.g., Jan 1, 2020).
    """
    df = pl.DataFrame(settings.CATEGORIES_HIERARCHY)
    
    # System initialization date for master data
    system_init_date = datetime(2020, 1, 1, 8, 0, 0)

    return df.with_columns([
        pl.col("id").cast(pl.Int32).alias("category_id"),
        pl.col("name").cast(pl.String).alias("category_name"),
        pl.col("parent").cast(pl.Int32).alias("parent_category_id"),
        pl.col("level").cast(pl.Int32),
        pl.lit(system_init_date).alias("created_at").cast(pl.Datetime("us", settings.SYSTEM_TIMEZONE)),
    ]).select(["category_id", "category_name", "parent_category_id", "level", "created_at"])


def generate_sellers() -> pl.DataFrame:
    num_rows = settings.DATA_VOLUMES["seller"]
    seller_types = ["Official", "Marketplace"]

    # Generate unique random 10-digit IDs for sellers
    unique_seller_ids = []
    seen_ids = set()
    while len(unique_seller_ids) < num_rows:
        new_id = f"{random.randint(0, 9999999999):010d}"
        if new_id not in seen_ids:
            seen_ids.add(new_id)
            unique_seller_ids.append(new_id)

    data = [
        {
            "seller_id": unique_seller_ids[i],
            "seller_name": generate_seller_name(),
            "join_date": fake.date_between(start_date="-3y", end_date=SYSTEM_START_DATE.date()),
            "seller_type": random.choice(seller_types),
            "rating": round(random.uniform(3, 5), 1),
            "country": settings.DEFAULT_COUNTRY_CODE,
        }
        for i in range(num_rows)
    ]

    return pl.DataFrame(data).with_columns([
        pl.col("seller_id").cast(pl.String),
        pl.col("seller_name").cast(pl.String),
        pl.col("join_date").cast(pl.Date),
        pl.col("seller_type").cast(pl.String),
        pl.col("rating").cast(pl.Float32),
        pl.col("country").cast(pl.String),
    ])


def generate_products(brand_ids: list, category_ids: list, seller_ids: list) -> pl.DataFrame:
    """
    Create product records.
    Naming Standard: Google Merchant Center Guidelines.
    Formula: [Brand] + [Model Code] + [Core Item] + [Attributes: Color, Size]
    """
    num_rows = settings.DATA_VOLUMES["product"]
    data = []

    # Generate unique random 10-digit IDs for products
    unique_product_ids = []
    seen_ids = set()
    while len(unique_product_ids) < num_rows:
        new_id = f"{random.randint(0, 9999999999):010d}"
        if new_id not in seen_ids:
            seen_ids.add(new_id)
            unique_product_ids.append(new_id)

    CATEGORY_PRODUCT_MAP = {
        1: {"items": ["Hat", "Scarf", "Sunglasses", "Watch", "Handbag"], "min_price": 100_000, "max_price": 5_000_000}, 
        2: {"items": ["Charger", "Cable", "Battery", "Power Bank", "Adapter"], "min_price": 50_000, "max_price": 800_000}, 
        3: {"items": ["Plant Pot", "Garden Hose", "Shovel", "Watering Can"], "min_price": 20_000, "max_price": 300_000}, 
        4: {"items": ["T-Shirt", "Jeans", "Jacket", "Sweater", "Coat"], "min_price": 150_000, "max_price": 2_500_000},
        5: {"items": ["Sneakers", "Boots", "Running Shoes", "Sandals"], "min_price": 300_000, "max_price": 4_000_000},
        6: {"items": ["Laptop", "Monitor", "Keyboard", "Mouse", "Webcam"], "min_price": 500_000, "max_price": 60_000_000},
        7: {"items": ["Smartphone", "Walkie-Talkie", "Landline Phone"], "min_price": 2_000_000, "max_price": 35_000_000},
        8: {"items": ["Wireless Earbuds", "Speaker", "Headphones", "Microphone"], "min_price": 200_000, "max_price": 8_000_000},
        9: {"items": ["Coffee Maker", "Blender", "Frying Pan", "Plate", "Knife Set"], "min_price": 50_000, "max_price": 3_000_000},
        10: {"items": ["Sofa", "Office Chair", "Dining Table", "Bed Frame", "Bookshelf"], "min_price": 1_000_000, "max_price": 25_000_000},
        "default": {"items": ["Premium Item", "Basic Accessory", "Pro Tool"], "min_price": 50_000, "max_price": 1_000_000}
    }

    COLORS = ["Black", "White", "Silver", "Navy Blue", "Space Gray", "Rose Gold", "Red"]
    SIZES = ["S", "M", "L", "XL", "13-inch", "15-inch", "128GB", "256GB", "Free Size"]

    for i in range(num_rows):
        cat_id = random.choice(category_ids)
        cat_data = CATEGORY_PRODUCT_MAP.get(cat_id, CATEGORY_PRODUCT_MAP["default"])
        
        # Realistic VND pricing: round to nearest thousand (e.g., 550,000 instead of 550,123.45)
        raw_price = random.uniform(cat_data["min_price"], cat_data["max_price"])
        price = float(round(raw_price / 1000) * 1000)
        
        raw_discount = price * random.uniform(0.7, 1.0)
        discount_price = float(round(raw_discount / 1000) * 1000)

        brand_name = fake.company().split()[0]
        model_code = fake.lexify(text='?-##', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        core_item = random.choice(cat_data["items"])
        color = random.choice(COLORS)
        size = random.choice(SIZES)
        
        product_name = f"{brand_name} {model_code} {core_item} - {color}, {size}"

        data.append({
            "product_id": unique_product_ids[i],
            "product_name": product_name,
            "category_id": cat_id,
            "brand_id": random.choice(brand_ids),
            "seller_id": random.choice(seller_ids),
            "price": price,
            "discount_price": discount_price,
            "stock_qty": random.randint(0, 500),
            "rating": round(random.uniform(3, 5), 1),
            "created_at": fake.date_time_between(start_date="-3y", end_date=SYSTEM_START_DATE),
            "is_active": fake.boolean(),
        })

    return pl.DataFrame(data).with_columns([
        pl.col("product_id").cast(pl.String),
        pl.col("product_name").cast(pl.String),
        pl.col("category_id").cast(pl.Int32),
        pl.col("brand_id").cast(pl.Int32),
        pl.col("seller_id").cast(pl.String),
        pl.col("price").cast(pl.Float64),
        pl.col("discount_price").cast(pl.Float64),
        pl.col("stock_qty").cast(pl.Int32),
        pl.col("rating").cast(pl.Float32),
        pl.col("created_at").cast(pl.Datetime("us", settings.SYSTEM_TIMEZONE)),
        pl.col("is_active").cast(pl.Boolean),
    ])


def generate_promotions() -> pl.DataFrame:
    num_rows = settings.DATA_VOLUMES["promotion"]
    promo_types = ["product", "category", "seller", "flash_sale"]
    discount_types = ["percentage", "fixed_amount"]
    data = []

    for i in range(1, num_rows + 1):
        discount_type = random.choice(discount_types)
        if discount_type == "percentage":
            discount_val = round(random.uniform(5.0, 50.0), 2)
        else:
            discount_val = round(random.uniform(10000, 500000), 2)

        start_dt = fake.date_between(start_date="-1y", end_date="+1y")
        end_dt = start_dt + timedelta(days=random.randint(30, 50))

        data.append({
            "promotion_id": i,
            "promotion_name": f"{fake.word().capitalize()} Mega Sale",
            "promotion_type": random.choice(promo_types),
            "discount_type": discount_type,
            "discount_value": discount_val,
            "start_date": start_dt,
            "end_date": end_dt,
        })

    return pl.DataFrame(data).with_columns([
        pl.col("promotion_id").cast(pl.Int32),
        pl.col("promotion_name").cast(pl.String),
        pl.col("promotion_type").cast(pl.String),
        pl.col("discount_type").cast(pl.String),
        pl.col("discount_value").cast(pl.Float64),
        pl.col("start_date").cast(pl.Date),
        pl.col("end_date").cast(pl.Date),
    ])


def generate_promotion_products(promotion_ids: list, product_ids: list) -> pl.DataFrame:
    num_rows = settings.DATA_VOLUMES["promotion_product"]
    unique_pairs = set()

    max_possible_pairs = len(promotion_ids) * len(product_ids)
    if num_rows > max_possible_pairs:
        raise ValueError(f"Cannot create {num_rows} unique pairs from only {max_possible_pairs} combinations.")

    while len(unique_pairs) < num_rows:
        unique_pairs.add((random.choice(promotion_ids), random.choice(product_ids)))

    data = [
        {
            "promo_product_id": i,
            "promotion_id": promo_id,
            "product_id": prod_id,
            "created_at": fake.date_time_between(start_date="-2y", end_date=SYSTEM_START_DATE),
        }
        for i, (promo_id, prod_id) in enumerate(unique_pairs, start=1)
    ]

    return pl.DataFrame(data).with_columns([
        pl.col("promo_product_id").cast(pl.Int32),
        pl.col("promotion_id").cast(pl.Int32),
        pl.col("product_id").cast(pl.String),
        pl.col("created_at").cast(pl.Datetime("us", settings.SYSTEM_TIMEZONE)),
    ])


def generate_realistic_order_timestamp() -> datetime:
    """
    Create a realistic shopping time (created_at).
    Behaviors included:
    1. Mega Sales (8/8, 9/9, 10/10) bring huge traffic.
    2. Payday (1st-5th) means people have more money to spend.
    3. Weekends have more traffic than normal weekdays.
    4. Time of day: High traffic at lunch (12 PM) and before bed (8 PM - 11 PM).
    """
    days_range = (SYSTEM_END_DATE - SYSTEM_START_DATE).days
    
    mega_sale_dates = [
        datetime(2025, 8, 8).date(), 
        datetime(2025, 9, 2).date(),
        datetime(2025, 9, 9).date(),
        datetime(2025, 10, 10).date(),
        datetime(2025, 10, 20).date()
    ]

    roll = random.random()
    if roll < 0.25:
        chosen_date = random.choice(mega_sale_dates)
    elif roll < 0.45:
        target_month = random.choice([8, 9, 10])
        target_day = random.randint(1, 5)
        chosen_date = datetime(2025, target_month, target_day).date()
    else:
        random_days = random.randint(0, days_range)
        temp_date = (SYSTEM_START_DATE + timedelta(days=random_days)).date()
        
        if temp_date.weekday() < 5 and random.random() < 0.4:
            days_to_weekend = 5 - temp_date.weekday()
            temp_date += timedelta(days=days_to_weekend)
            if temp_date > SYSTEM_END_DATE.date():
                temp_date -= timedelta(days=7)
        
        chosen_date = temp_date

    hour_weights = [
        12, 4, 1, 1, 1, 3,
        5, 8, 10, 12, 14, 15,
        20, 18, 12, 10, 10, 12,
        15, 18, 25, 28, 22, 18
    ]
    
    hour = random.choices(range(24), weights=hour_weights, k=1)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return datetime.combine(chosen_date, datetime.min.time()).replace(hour=hour, minute=minute, second=second)


def generate_transactional_data(sellers_df: pl.DataFrame, products_df: pl.DataFrame) -> Iterator[Tuple[pl.DataFrame, pl.DataFrame]]:
    sellers = sellers_df.to_dicts()
    products = products_df.to_dicts()

    seller_to_products = {}
    for p in products:
        if p["is_active"] and p["stock_qty"] > 0:
            s_id = p["seller_id"]
            if s_id not in seller_to_products:
                seller_to_products[s_id] = []
            seller_to_products[s_id].append(p)

    valid_sellers = [s for s in sellers if s["seller_id"] in seller_to_products]
    if not valid_sellers:
        raise ValueError("No sellers have active products in stock.")

    seller_weights = [random.random() ** 3 for _ in valid_sellers]

    total_orders_needed = random.randint(settings.ORDER_MIN_VOLUME, settings.ORDER_MAX_VOLUME)
    statuses = list(settings.ORDER_STATUS_DISTRIBUTION.keys())
    status_weights = list(settings.ORDER_STATUS_DISTRIBUTION.values())
    
    orders_generated = 0

    while orders_generated < total_orders_needed:
        current_batch_size = min(settings.BATCH_SIZE, total_orders_needed - orders_generated)
        
        batch_orders = {
            "order_id": [], "order_date": [], "seller_id": [], "status": [], 
            "total_amount": [], "created_at": []
        }
        batch_items = {
            "order_item_id": [], "order_id": [], "product_id": [], "order_date": [], 
            "quantity": [], "unit_price": [], "subtotal": [], "created_at": []
        }

        for _ in range(current_batch_size):
            orders_generated += 1
            
            # Use UUID for robust transaction tracking
            order_id = str(uuid.uuid4())

            seller = random.choices(valid_sellers, weights=seller_weights, k=1)[0]
            seller_id = seller["seller_id"]
            available_products = seller_to_products[seller_id]
            
            product_weights = [random.random() ** 2 for _ in available_products]

            exact_created_at = generate_realistic_order_timestamp()
            order_date = exact_created_at.replace(hour=0, minute=0, second=0, microsecond=0)
            
            status = random.choices(statuses, weights=status_weights, k=1)[0]
            
            num_items = random.randint(settings.ITEMS_PER_ORDER_MIN, settings.ITEMS_PER_ORDER_MAX)
            num_items = min(num_items, len(available_products)) 
            
            chosen_products = random.choices(available_products, weights=product_weights, k=num_items)
            chosen_products = list({p["product_id"]: p for p in chosen_products}.values())
            
            total_amount = 0.0

            for prod in chosen_products:
                max_buyable = min(settings.MAX_QTY_PER_ORDER_ITEM, prod["stock_qty"])
                quantity = random.randint(1, max_buyable) 
                
                # unit_price comes from product generation, which is already rounded to thousands
                unit_price = float(prod["discount_price"])
                subtotal = quantity * unit_price
                total_amount += subtotal

                batch_items["order_item_id"].append(str(uuid.uuid4()))
                batch_items["order_id"].append(order_id)
                batch_items["product_id"].append(prod["product_id"])
                batch_items["order_date"].append(order_date)
                batch_items["quantity"].append(quantity)
                batch_items["unit_price"].append(unit_price)
                batch_items["subtotal"].append(subtotal)
                batch_items["created_at"].append(exact_created_at)

            # Round total amount to ensure .00 decimal tracking is clean
            total_amount = float(round(total_amount / 1000) * 1000)

            batch_orders["order_id"].append(order_id)
            batch_orders["order_date"].append(order_date)
            batch_orders["seller_id"].append(seller_id)
            batch_orders["status"].append(status)
            batch_orders["total_amount"].append(total_amount)
            batch_orders["created_at"].append(exact_created_at)

        df_orders = pl.DataFrame(batch_orders).with_columns([
            pl.col("order_id").cast(pl.String),
            pl.col("order_date").cast(pl.Datetime("us", settings.SYSTEM_TIMEZONE)),
            pl.col("seller_id").cast(pl.String),
            pl.col("status").cast(pl.String),
            pl.col("total_amount").cast(pl.Float64),
            pl.col("created_at").cast(pl.Datetime("us", settings.SYSTEM_TIMEZONE)),
        ])

        df_items = pl.DataFrame(batch_items).with_columns([
            pl.col("order_item_id").cast(pl.String),
            pl.col("order_id").cast(pl.String),
            pl.col("product_id").cast(pl.String),
            pl.col("order_date").cast(pl.Datetime("us", settings.SYSTEM_TIMEZONE)),
            pl.col("quantity").cast(pl.Int32),
            pl.col("unit_price").cast(pl.Float64),
            pl.col("subtotal").cast(pl.Float64),
            pl.col("created_at").cast(pl.Datetime("us", settings.SYSTEM_TIMEZONE)),
        ])

        yield df_orders, df_items