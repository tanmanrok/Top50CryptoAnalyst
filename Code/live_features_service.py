"""
Live Features Service - Phase 2 Integration
Computes features from live price data and stores in database
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from sqlalchemy import text, inspect
import json
from pathlib import Path

# Import feature computation
from compute_features import FeatureComputor, compute_features_from_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveFeaturesService:
    """Compute and store features from live price data"""
    
    def __init__(self, db_engine, lookback_days: int = 60):
        """
        Initialize live features service
        
        Args:
            db_engine: SQLAlchemy database engine
            lookback_days: Number of days of historical data to use (default: 60)
        """
        self.db_engine = db_engine
        self.lookback_days = lookback_days
        self.feature_computor = FeatureComputor()
        
        # Create features table if not exists
        self._create_features_table()
        
        logger.info(f"✓ LiveFeaturesService initialized (lookback: {lookback_days} days)")
    
    def _create_features_table(self):
        """Create features table in database if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS computed_features (
            id SERIAL PRIMARY KEY,
            cryptocurrency VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            
            -- OHLCV
            open FLOAT,
            high FLOAT,
            low FLOAT,
            close FLOAT,
            volume FLOAT,
            
            -- Moving Averages
            sma_5 FLOAT, sma_10 FLOAT, sma_20 FLOAT, sma_50 FLOAT,
            ema_12 FLOAT, ema_26 FLOAT,
            
            -- MACD
            macd FLOAT, macd_signal FLOAT, macd_diff FLOAT,
            
            -- RSI
            rsi_14 FLOAT,
            
            -- Bollinger Bands
            bb_upper_20 FLOAT, bb_middle_20 FLOAT, bb_lower_20 FLOAT,
            
            -- Other indicators
            roc_12 FLOAT,
            momentum_10 FLOAT,
            atr_14 FLOAT,
            
            -- Returns & Volatility
            daily_return FLOAT,
            weekly_return FLOAT,
            monthly_return FLOAT,
            volatility_7 FLOAT,
            volatility_30 FLOAT,
            
            -- Temporal
            day_of_week INT,
            month INT,
            trend_up BOOLEAN,
            
            -- Metadata
            computed_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(cryptocurrency, timestamp)
        );
        """
        
        try:
            with self.db_engine.begin() as conn:
                conn.execute(text(create_table_sql))
            logger.info("✓ Features table ready")
        except Exception as e:
            logger.warning(f"Features table creation: {e}")
    
    def compute_for_crypto(self, cryptocurrency: str) -> Optional[pd.DataFrame]:
        """
        Compute features for a single cryptocurrency
        
        Args:
            cryptocurrency: Cryptocurrency name (e.g., 'Bitcoin', 'bitcoin', 'Bitcoin')
        
        Returns:
            DataFrame with computed features, or None if error
        """
        try:
            logger.info(f"Computing features for {cryptocurrency}...")
            # Normalize cryptocurrency name to lowercase for database query
            crypto_lower = cryptocurrency.lower().replace(' ', '_')
            df_features = compute_features_from_db(
                self.db_engine,
                crypto_lower,
                self.lookback_days
            )
            
            logger.info(f"✓ Computed {len(df_features)} rows of features for {cryptocurrency}")
            return df_features
            
        except Exception as e:
            logger.error(f"✗ Error computing features for {cryptocurrency}: {e}")
            return None
    
    def compute_for_all_cryptos(self, cryptos: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """
        Compute features for all cryptocurrencies
        
        Args:
            cryptos: List of cryptocurrency names (default: fetch from database)
        
        Returns:
            Dictionary of {crypto: features_dataframe}
        """
        if cryptos is None:
            # Fetch list of cryptos from database
            try:
                with self.db_engine.begin() as conn:
                    result = conn.execute(text(
                        "SELECT DISTINCT cryptocurrency FROM prices ORDER BY cryptocurrency"
                    ))
                    cryptos = [row[0] for row in result]
                logger.info(f"Found {len(cryptos)} cryptocurrencies in database")
            except Exception as e:
                logger.error(f"Error fetching cryptocurrency list: {e}")
                return {}
        
        results = {}
        for crypto in cryptos:
            df = self.compute_for_crypto(crypto)
            if df is not None:
                results[crypto] = df
        
        logger.info(f"✓ Computed features for {len(results)}/{len(cryptos)} cryptocurrencies")
        return results
    
    def save_features(self, cryptocurrency: str, df_features: pd.DataFrame) -> bool:
        """
        Save computed features to database
        
        Args:
            cryptocurrency: Cryptocurrency name
            df_features: DataFrame with computed features
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare data for insertion
            df_insert = df_features.copy()
            # Normalize cryptocurrency name to lowercase
            crypto_lower = cryptocurrency.lower().replace(' ', '_')
            df_insert['cryptocurrency'] = crypto_lower
            df_insert['computed_at'] = datetime.utcnow()
            
            # Standardize column names for database
            df_insert.columns = [col.lower().replace(' ', '_') for col in df_insert.columns]
            
            # Insert into database
            with self.db_engine.begin() as conn:
                # Use ON CONFLICT to skip duplicates
                for _, row in df_insert.iterrows():
                    values_dict = row.to_dict()
                    
                    # Ensure timestamp is present and properly named
                    if 'timestamp' not in values_dict and 'timestamp' in df_insert.columns:
                        values_dict['timestamp'] = row['timestamp']
                    elif 'timestamp' not in values_dict:
                        # If no timestamp, skip this row
                        logger.warning(f"Skipping row without timestamp for {cryptocurrency}")
                        continue
                    
                    # Build SQL insert
                    cols = ', '.join(values_dict.keys())
                    vals = ', '.join([f":{k}" for k in values_dict.keys()])
                    sql = f"""
                    INSERT INTO computed_features ({cols})
                    VALUES ({vals})
                    ON CONFLICT (cryptocurrency, timestamp) DO NOTHING
                    """
                    
                    conn.execute(text(sql), values_dict)
            
            logger.info(f"✓ Saved {len(df_insert)} feature rows for {cryptocurrency}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error saving features for {cryptocurrency}: {e}")
            return False
    
    def save_all_features(self, features_dict: Dict[str, pd.DataFrame]) -> Dict[str, bool]:
        """
        Save features for all cryptocurrencies
        
        Args:
            features_dict: Dictionary of {crypto: features_dataframe}
        
        Returns:
            Dictionary of {crypto: success_bool}
        """
        results = {}
        for crypto, df in features_dict.items():
            success = self.save_features(crypto, df)
            results[crypto] = success
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"✓ Saved features for {successful}/{len(results)} cryptocurrencies")
        return results
    
    def get_latest_features(self, cryptocurrency: str) -> Optional[pd.Series]:
        """
        Get the most recent computed features for a cryptocurrency
        
        Args:
            cryptocurrency: Cryptocurrency name
        
        Returns:
            Series with latest features, or None if not found
        """
        try:
            query = text("""
            SELECT * FROM computed_features
            WHERE cryptocurrency = :crypto
            ORDER BY timestamp DESC
            LIMIT 1
            """)
            
            with self.db_engine.begin() as conn:
                result = pd.read_sql(query, conn, params={'crypto': cryptocurrency})
            
            if len(result) > 0:
                logger.info(f"✓ Retrieved latest features for {cryptocurrency}")
                return result.iloc[0]
            else:
                logger.warning(f"No features found for {cryptocurrency}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving features for {cryptocurrency}: {e}")
            return None
    
    def get_features_for_prediction(self, cryptocurrency: str) -> Optional[Dict]:
        """
        Get features ready for model prediction
        
        Args:
            cryptocurrency: Cryptocurrency name
        
        Returns:
            Dictionary of features matching model input schema
        """
        features = self.get_latest_features(cryptocurrency)
        if features is None:
            return None
        
        # Extract only model features (exclude metadata)
        model_features = FeatureComputor.TRAINING_FEATURES
        feature_dict = {}
        
        for feat in model_features:
            feat_col = feat.lower().replace(' ', '_')
            if feat_col in features.index:
                feature_dict[feat] = features[feat_col]
        
        return feature_dict if feature_dict else None
    
    def run_continuous(self, interval_seconds: int = 86400, cryptos: Optional[List[str]] = None):
        """
        Run continuous feature computation loop
        
        Args:
            interval_seconds: Time between feature updates (default: 86400 = 1 day)
            cryptos: List of cryptos to compute (default: all)
        """
        logger.info(f"Starting continuous feature computation loop (interval: {interval_seconds}s)")
        
        import time
        
        try:
            while True:
                logger.info(f"[{datetime.utcnow()}] Computing features...")
                
                # Compute for all cryptos
                features_dict = self.compute_for_all_cryptos(cryptos)
                
                # Save to database
                self.save_all_features(features_dict)
                
                # Wait for next interval
                logger.info(f"Next update in {interval_seconds} seconds...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Feature computation loop stopped by user")
        except Exception as e:
            logger.error(f"Error in feature computation loop: {e}")


def print_feature_summary(features_dict: Dict[str, pd.DataFrame]):
    """Print summary of computed features"""
    print("\n" + "=" * 70)
    print("FEATURE COMPUTATION SUMMARY")
    print("=" * 70)
    
    for crypto, df in features_dict.items():
        print(f"\n{crypto}:")
        print(f"  - Rows: {len(df)}")
        print(f"  - Columns: {len(df.columns)}")
        print(f"  - NaN values: {df.isnull().sum().sum()}")
        print(f"  - Date range: {df.index.min()} to {df.index.max()}" if hasattr(df.index, 'min') else "")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Example usage
    from Code.db_connection import engine
    
    logger.info("=" * 70)
    logger.info("Live Features Service - Example")
    logger.info("=" * 70)
    
    # Initialize service
    service = LiveFeaturesService(engine, lookback_days=60)
    
    # Compute features for Bitcoin
    print("\nComputing features for Bitcoin...")
    features_df = service.compute_for_crypto('Bitcoin')
    
    if features_df is not None:
        print(f"✓ Computed {len(features_df)} rows of features")
        print(f"✓ {len(features_df.columns)} features")
        print(f"\nFeatures:\n{features_df.columns.tolist()}")
        print(f"\nLast row:\n{features_df.iloc[-1]}")
