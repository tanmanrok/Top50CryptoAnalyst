"""
Backfill Features for Historical Price Data
============================================
Computes technical and temporal features for ALL historical price data in the database.
Uses minimal lookback window (5 days) to generate features even for early data points.
"""

import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import text
from db_connection import engine
from compute_features import FeatureComputor
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_all_cryptos_from_db():
    """Get list of all cryptocurrencies in the prices table."""
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT cryptocurrency 
                FROM prices 
                ORDER BY cryptocurrency
            """))
            cryptos = [row[0] for row in result]
            logger.info(f"Found {len(cryptos)} cryptocurrencies in database")
            return cryptos
    except Exception as e:
        logger.error(f"Error fetching cryptocurrencies: {e}")
        return []


def get_price_data_for_crypto(cryptocurrency, min_lookback=5):
    """
    Fetch all price data for a cryptocurrency.
    
    Args:
        cryptocurrency: Cryptocurrency name (e.g., 'bitcoin')
        min_lookback: Minimum lookback days (default 5 for early data points)
    
    Returns:
        DataFrame with OHLCV data or None if insufficient data
    """
    try:
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM prices
            WHERE LOWER(cryptocurrency) = LOWER(%(crypto)s)
            ORDER BY timestamp ASC
        """
        
        df = pd.read_sql(query, engine, params={'crypto': cryptocurrency})
        
        if len(df) < min_lookback:
            logger.warning(f"{cryptocurrency}: Only {len(df)} rows (need {min_lookback})")
            return None
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        logger.info(f"{cryptocurrency}: Fetched {len(df)} price rows")
        return df
    
    except Exception as e:
        logger.error(f"Error fetching price data for {cryptocurrency}: {e}")
        return None


def compute_and_save_features(cryptocurrency):
    """
    Compute features for all historical data and save to database.
    
    Args:
        cryptocurrency: Cryptocurrency name
    
    Returns:
        Number of feature rows saved, or 0 if failed
    """
    try:
        # Get all historical price data
        df_prices = get_price_data_for_crypto(cryptocurrency, min_lookback=5)
        if df_prices is None or len(df_prices) == 0:
            logger.warning(f"Skipping {cryptocurrency}: No price data")
            return 0
        
        # Compute features
        logger.info(f"Computing features for {cryptocurrency} ({len(df_prices)} rows)...")
        computor = FeatureComputor()
        df_features = computor.compute(df_prices, drop_na=False)  # Keep all rows, even with NaN
        
        if df_features is None or len(df_features) == 0:
            logger.warning(f"No features computed for {cryptocurrency}")
            return 0
        
        # Add cryptocurrency column
        df_features['cryptocurrency'] = cryptocurrency.lower().replace(' ', '_')
        
        # Add computed_at timestamp
        df_features['computed_at'] = datetime.utcnow()
        
        # Save to database
        rows_saved = save_features_to_db(cryptocurrency, df_features)
        logger.info(f"✓ {cryptocurrency}: Saved {rows_saved} feature rows")
        return rows_saved
    
    except Exception as e:
        logger.error(f"Error processing {cryptocurrency}: {e}")
        return 0


def save_features_to_db(cryptocurrency, df_features):
    """
    Save feature DataFrame to computed_features table.
    Uses ON CONFLICT to handle duplicates.
    
    Args:
        cryptocurrency: Cryptocurrency name
        df_features: DataFrame with features
    
    Returns:
        Number of rows saved
    """
    try:
        # Debug: Print actual columns in DataFrame
        logger.info(f"DataFrame columns: {df_features.columns.tolist()}")
        
        # Ensure timestamp column exists and is in proper format
        if 'TIMESTAMP' not in df_features.columns and 'timestamp' not in df_features.columns:
            logger.error(f"{cryptocurrency}: No timestamp column found. Available: {df_features.columns.tolist()}")
            return 0
        
        # Create a working copy and standardize column names
        df_db = df_features.copy()
        
        # Rename TIMESTAMP to timestamp if needed
        if 'TIMESTAMP' in df_db.columns:
            df_db = df_db.rename(columns={'TIMESTAMP': 'timestamp'})
        
        # Ensure all required columns exist, fill missing ones with None
        required_cols = [
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'sma_5', 'sma_10', 'sma_20', 'sma_50', 'ema_12', 'ema_26',
            'macd', 'macd_signal', 'macd_diff', 'rsi_14',
            'bb_upper_20', 'bb_middle_20', 'bb_lower_20',
            'roc_12', 'momentum_10', 'atr_14',
            'daily_return', 'weekly_return', 'monthly_return',
            'volatility_7', 'volatility_30',
            'day_of_week', 'month', 'trend_up'
        ]
        
        # Only select columns that exist
        available_cols = [col for col in required_cols if col in df_db.columns]
        missing_cols = [col for col in required_cols if col not in df_db.columns]
        
        if missing_cols:
            logger.warning(f"{cryptocurrency}: Missing columns: {missing_cols}")
        
        df_db = df_db[available_cols].copy()
        
        # Add cryptocurrency and computed_at
        df_db['cryptocurrency'] = cryptocurrency.lower().replace(' ', '_')
        df_db['computed_at'] = datetime.utcnow()
        
        # Convert NaN to None for database
        df_db = df_db.where(pd.notna(df_db), None)
        
        # Save to database
        with engine.begin() as conn:
            rows_before = conn.execute(
                text("SELECT COUNT(*) FROM computed_features WHERE cryptocurrency = :crypto"),
                {'crypto': cryptocurrency.lower().replace(' ', '_')}
            ).scalar()
            
            # Use SQLAlchemy to_sql for efficient bulk insert
            df_db.to_sql(
                'computed_features',
                conn,
                if_exists='append',
                index=False,
                method='multi'
            )
            
            rows_after = conn.execute(
                text("SELECT COUNT(*) FROM computed_features WHERE cryptocurrency = :crypto"),
                {'crypto': cryptocurrency.lower().replace(' ', '_')}
            ).scalar()
            
            rows_saved = rows_after - rows_before
            return max(0, rows_saved)
    
    except Exception as e:
        logger.error(f"Error saving features for {cryptocurrency}: {e}", exc_info=True)
        return 0


def clear_existing_features():
    """Clear existing computed_features to avoid duplicates."""
    try:
        with engine.begin() as conn:
            count_before = conn.execute(
                text("SELECT COUNT(*) FROM computed_features")
            ).scalar()
            
            conn.execute(text("DELETE FROM computed_features"))
            logger.info(f"Cleared {count_before} existing feature rows")
    
    except Exception as e:
        logger.error(f"Error clearing features: {e}")


def run_backfill():
    """Run full backfill of features for all cryptocurrencies."""
    logger.info("=" * 60)
    logger.info("Starting Historical Feature Backfill")
    logger.info("=" * 60)
    
    # Clear existing features
    clear_existing_features()
    
    # Get all cryptocurrencies
    cryptos = get_all_cryptos_from_db()
    if not cryptos:
        logger.error("No cryptocurrencies found in database")
        return
    
    # Process each cryptocurrency
    total_rows = 0
    successful = 0
    
    for crypto in cryptos:
        rows = compute_and_save_features(crypto)
        total_rows += rows
        if rows > 0:
            successful += 1
    
    logger.info("=" * 60)
    logger.info(f"Backfill Complete: {total_rows} total features for {successful}/{len(cryptos)} cryptos")
    logger.info("=" * 60)


if __name__ == '__main__':
    try:
        run_backfill()
    except KeyboardInterrupt:
        logger.info("Backfill cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
