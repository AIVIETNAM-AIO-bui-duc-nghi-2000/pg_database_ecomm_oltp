import polars as pl
import sqlalchemy
from src.logger import get_logger
from src.generator import (
    generate_brands,
    generate_categories,
    generate_sellers,
    generate_products,
    generate_promotions,
    generate_promotion_products,
    generate_transactional_data
)
from src.postgres_loader import load_data_to_postgres, get_db_uri

logger = get_logger("data_pipeline")


def reset_database():
    """Delete all existing data from the database tables.

    This function clears out old records so that running the pipeline
    multiple times does not cause duplicate data.
    """
    db_uri = get_db_uri()
    engine = sqlalchemy.create_engine(db_uri)
    try:
        with engine.begin() as conn:
            logger.info("Clearing old data from tables (TRUNCATE CASCADE)...")
            # We use CASCADE to automatically delete linked data in child tables.
            conn.execute(sqlalchemy.text("""
                TRUNCATE TABLE order_items, orders, 
                promotion_products, promotions, products, sellers, 
                categories, brands CASCADE;
            """))
    except Exception as e:
        logger.warning(f"Could not clear tables. Details: {e}")
    finally:
        engine.dispose()


def main():
    try:
        logger.info("Starting the End-to-End E-commerce Data Pipeline...")

        # -----------------------------------------------------------------
        # Stage 0: Clean the Database
        # -----------------------------------------------------------------
        # We clear the database first. This ensures we start with a fresh
        # system and avoids errors from old data.
        reset_database()

        # -----------------------------------------------------------------
        # Stage 1: Process Independent Tables
        # -----------------------------------------------------------------
        # We create and load tables that do not need data from other tables.
        # These are basic building blocks: brands, categories, and sellers.
        logger.info("--- Stage 1: Processing Independent Tables ---")

        # Create and load brand data. Extract the IDs to link with products.
        df_brand = generate_brands()
        load_data_to_postgres(df_brand, "brands")
        brand_ids = df_brand["brand_id"].to_list()
        del df_brand  # Delete from memory immediately to save RAM

        # Create and load category data. Extract the IDs for later use.
        df_category = generate_categories()
        load_data_to_postgres(df_category, "categories")
        category_ids = df_category["category_id"].to_list()
        del df_category

        # Create and load seller data. Extract the IDs for later use.
        # We do not delete df_seller yet because Stage 4 needs it.
        df_seller = generate_sellers()
        load_data_to_postgres(df_seller, "sellers")
        seller_ids = df_seller["seller_id"].to_list()

        # -----------------------------------------------------------------
        # Stage 2: Process Dependent Table (Products)
        # -----------------------------------------------------------------
        # We create products. Products cannot exist without a valid brand,
        # category, and seller, so we pass the ID lists into the generator.
        logger.info("--- Stage 2: Processing Dependent Table (Products) ---")
        df_product = generate_products(brand_ids, category_ids, seller_ids)

        # We change price types from float to string, and then to decimal.
        # This step is critical to prevent small rounding errors in money.
        df_product = df_product.with_columns([
            pl.col("price").cast(pl.String).cast(pl.Decimal(scale=2)),
            pl.col("discount_price").cast(pl.String).cast(pl.Decimal(scale=2))
        ])

        # Load product data into the database and extract product IDs.
        # We do not delete df_product yet because Stage 4 needs it.
        load_data_to_postgres(df_product, "products")
        product_ids = df_product["product_id"].to_list()

        # Clean up temporary ID lists that are no longer needed.
        del brand_ids, category_ids, seller_ids

        # -----------------------------------------------------------------
        # Stage 3: Process Promotions and Mappings
        # -----------------------------------------------------------------
        # We create discount campaigns (promotions) and connect them to the
        # products we generated in Stage 2.
        logger.info("--- Stage 3: Processing Promotions & Mapping ---")
        df_promotion = generate_promotions()

        # Change discount values to decimal to keep financial data exact.
        df_promotion = df_promotion.with_columns(
            pl.col("discount_value").cast(pl.String).cast(pl.Decimal(scale=2))
        )

        # Load promotions into the database and get their IDs.
        load_data_to_postgres(df_promotion, "promotions")
        promotion_ids = df_promotion["promotion_id"].to_list()
        del df_promotion

        # Connect promotions to products and load the mapping table.
        df_promo_product = generate_promotion_products(promotion_ids, product_ids)
        load_data_to_postgres(df_promo_product, "promotion_products")

        # Clean up variables to free up memory before the heavy stage.
        del df_promo_product, promotion_ids, product_ids

        # -----------------------------------------------------------------
        # Stage 4: Process Transactional Data (Orders & Items)
        # -----------------------------------------------------------------
        # We create customer orders and the specific items inside those orders.
        # This data can be millions of rows, so we use a loop to process it
        # in small groups (batches). This prevents the computer from freezing.
        logger.info("--- Stage 4: Processing Transactional Data ---")

        batch_counter = 1
        # The generator yields one small group of orders and items at a time.
        for batch_orders, batch_items in generate_transactional_data(df_seller, df_product):
            logger.info(f"Ingesting transactional batch #{batch_counter}...")

            # Convert ID columns to string format.
            # Convert financial columns to Decimal to avoid ADBC binary mismatch.
            batch_orders = batch_orders.with_columns([
                pl.col("order_id").cast(pl.String),
                pl.col("total_amount").cast(pl.String).cast(pl.Decimal(scale=2))
            ])
            
            batch_items = batch_items.with_columns([
                pl.col("order_item_id").cast(pl.String),
                pl.col("order_id").cast(pl.String),
                pl.col("unit_price").cast(pl.String).cast(pl.Decimal(scale=2)),
                pl.col("subtotal").cast(pl.String).cast(pl.Decimal(scale=2))
            ])

            # Load the current small group directly into the database tables.
            load_data_to_postgres(batch_orders, "orders")
            load_data_to_postgres(batch_items, "order_items")

            batch_counter += 1
            # Delete the current batch variables immediately. This forces the
            # system to clean memory and prevents RAM usage from growing.
            del batch_orders, batch_items

        # Clean up the large reference datasets after the loop is complete.
        del df_seller, df_product

        logger.info("SUCCESS: All data successfully loaded to PostgreSQL.")

    except Exception as e:
        logger.error(f"Pipeline crashed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()