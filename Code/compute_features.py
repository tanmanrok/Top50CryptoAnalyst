"""
Phase 2: Automated Feature Engineering Pipeline
Compute 28 technical indicators from live price data to match training features
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Compute technical indicators matching training data"""
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with price data
        
        Args:
            df: DataFrame with columns [timestamp, open, high, low, close, volume]
        """
        self.df = df.copy()
        self.df.columns = [col.lower() for col in self.df.columns]
        
        # Ensure proper data types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        logger.info(f"Initialized TechnicalIndicators with {len(self.df)} rows")
    
    def sma(self, periods: List[int] = None) -> pd.DataFrame:
        """Simple Moving Average"""
        if periods is None:
            periods = [5, 10, 20, 50]
        
        for period in periods:
            self.df[f'SMA_{period}'] = self.df['close'].rolling(window=period).mean()
        
        logger.info(f"✓ Computed SMA for periods: {periods}")
        return self.df
    
    def ema(self, periods: List[int] = None) -> pd.DataFrame:
        """Exponential Moving Average"""
        if periods is None:
            periods = [12, 26]
        
        for period in periods:
            self.df[f'EMA_{period}'] = self.df['close'].ewm(span=period, adjust=False).mean()
        
        logger.info(f"✓ Computed EMA for periods: {periods}")
        return self.df
    
    def macd(self) -> pd.DataFrame:
        """MACD (Moving Average Convergence Divergence)"""
        ema_12 = self.df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = self.df['close'].ewm(span=26, adjust=False).mean()
        
        self.df['MACD'] = ema_12 - ema_26
        self.df['MACD_Signal'] = self.df['MACD'].ewm(span=9, adjust=False).mean()
        self.df['MACD_Diff'] = self.df['MACD'] - self.df['MACD_Signal']
        
        logger.info("✓ Computed MACD")
        return self.df
    
    def rsi(self, period: int = 14) -> pd.DataFrame:
        """Relative Strength Index"""
        delta = self.df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        self.df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
        
        logger.info(f"✓ Computed RSI({period})")
        return self.df
    
    def bollinger_bands(self, period: int = 20, std_dev: float = 2) -> pd.DataFrame:
        """Bollinger Bands"""
        sma = self.df['close'].rolling(window=period).mean()
        std = self.df['close'].rolling(window=period).std()
        
        self.df[f'BB_Upper_{period}'] = sma + (std * std_dev)
        self.df[f'BB_Middle_{period}'] = sma
        self.df[f'BB_Lower_{period}'] = sma - (std * std_dev)
        self.df[f'BB_Width_{period}'] = self.df[f'BB_Upper_{period}'] - self.df[f'BB_Lower_{period}']
        self.df[f'BB_Position_{period}'] = (self.df['close'] - self.df[f'BB_Lower_{period}']) / self.df[f'BB_Width_{period}']
        
        logger.info(f"✓ Computed Bollinger Bands({period})")
        return self.df
    
    def roc(self, period: int = 12) -> pd.DataFrame:
        """Rate of Change"""
        self.df[f'ROC_{period}'] = ((self.df['close'] - self.df['close'].shift(period)) / 
                                     self.df['close'].shift(period) * 100)
        
        logger.info(f"✓ Computed ROC({period})")
        return self.df
    
    def momentum(self, period: int = 10) -> pd.DataFrame:
        """Momentum"""
        self.df[f'Momentum_{period}'] = self.df['close'] - self.df['close'].shift(period)
        
        logger.info(f"✓ Computed Momentum({period})")
        return self.df
    
    def atr(self, period: int = 14) -> pd.DataFrame:
        """Average True Range"""
        high_low = self.df['high'] - self.df['low']
        high_close = np.abs(self.df['high'] - self.df['close'].shift())
        low_close = np.abs(self.df['low'] - self.df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.df[f'ATR_{period}'] = tr.rolling(window=period).mean()
        
        logger.info(f"✓ Computed ATR({period})")
        return self.df
    
    def compute_all(self) -> pd.DataFrame:
        """Compute all indicators"""
        try:
            self.sma()
            self.ema()
            self.macd()
            self.rsi()
            self.bollinger_bands()
            self.roc()
            self.momentum()
            self.atr()
            
            logger.info("✓ All technical indicators computed successfully")
            return self.df
        except Exception as e:
            logger.error(f"✗ Error computing indicators: {e}")
            raise


class TemporalFeatures:
    """Compute temporal and trend features"""
    
    def __init__(self, df: pd.DataFrame):
        """Initialize with price data"""
        self.df = df.copy()
        if 'timestamp' in self.df.columns:
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        elif 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'])
            self.df['timestamp'] = self.df['date']
        
        logger.info("Initialized TemporalFeatures")
    
    def add_temporal_features(self) -> pd.DataFrame:
        """Add time-based features"""
        if 'timestamp' not in self.df.columns:
            raise ValueError("timestamp column required")
        
        self.df['Day_of_Week'] = self.df['timestamp'].dt.dayofweek
        self.df['Month'] = self.df['timestamp'].dt.month
        self.df['DayOfMonth'] = self.df['timestamp'].dt.day
        self.df['Quarter'] = self.df['timestamp'].dt.quarter
        self.df['Hour'] = self.df['timestamp'].dt.hour
        
        logger.info("✓ Added temporal features")
        return self.df
    
    def add_trend_encoding(self) -> pd.DataFrame:
        """Encode price trend (Up/Down relative to SMA_20)"""
        if 'close' not in self.df.columns:
            raise ValueError("close column required")
        
        # Simple trend: Up if Close > SMA_20, else Down
        if 'SMA_20' in self.df.columns:
            self.df['Trend'] = np.where(self.df['close'] > self.df['SMA_20'], 'Up', 'Down')
        else:
            # Fallback: use simple moving average
            sma_20 = self.df['close'].rolling(window=20).mean()
            self.df['Trend'] = np.where(self.df['close'] > sma_20, 'Up', 'Down')
        
        # One-hot encode
        self.df = pd.get_dummies(self.df, columns=['Trend'], drop_first=True)
        
        logger.info("✓ Added trend encoding")
        return self.df
    
    def add_returns(self) -> pd.DataFrame:
        """Add daily returns"""
        if 'close' not in self.df.columns:
            raise ValueError("close column required")
        
        self.df['Daily_Return'] = self.df['close'].pct_change()
        self.df['Weekly_Return'] = self.df['close'].pct_change(periods=7)
        self.df['Monthly_Return'] = self.df['close'].pct_change(periods=30)
        
        logger.info("✓ Added returns")
        return self.df
    
    def add_volatility(self) -> pd.DataFrame:
        """Add volatility measures"""
        if 'Daily_Return' not in self.df.columns:
            self.add_returns()
        
        self.df['Volatility_7'] = self.df['Daily_Return'].rolling(window=7).std()
        self.df['Volatility_30'] = self.df['Daily_Return'].rolling(window=30).std()
        
        logger.info("✓ Added volatility")
        return self.df
    
    def add_all(self) -> pd.DataFrame:
        """Add all temporal features"""
        try:
            self.add_temporal_features()
            self.add_trend_encoding()
            self.add_returns()
            self.add_volatility()
            
            logger.info("✓ All temporal features added")
            return self.df
        except Exception as e:
            logger.error(f"✗ Error adding temporal features: {e}")
            raise


class FeatureComputor:
    """Master class to compute all features"""
    
    # Training features (28 total)
    TRAINING_FEATURES = [
        'Open', 'High', 'Low', 'Close', 'Volume',
        'SMA_5', 'SMA_10', 'SMA_20', 'SMA_50',
        'EMA_12', 'EMA_26',
        'MACD', 'MACD_Signal', 'MACD_Diff',
        'RSI_14',
        'BB_Upper_20', 'BB_Middle_20', 'BB_Lower_20',
        'ROC_12', 'Momentum_10', 'ATR_14',
        'Daily_Return', 'Weekly_Return', 'Monthly_Return',
        'Volatility_7', 'Volatility_30',
        'Day_of_Week', 'Month', 'Trend_Up'
    ]
    
    def __init__(self, required_features: Optional[List[str]] = None):
        """
        Initialize feature computor
        
        Args:
            required_features: List of features to compute (default: TRAINING_FEATURES)
        """
        self.required_features = required_features or self.TRAINING_FEATURES
        logger.info(f"Initialized FeatureComputor with {len(self.required_features)} required features")
    
    def compute(self, df: pd.DataFrame, drop_na: bool = True) -> pd.DataFrame:
        """
        Compute all features from price data
        
        Args:
            df: DataFrame with columns [timestamp, open, high, low, close, volume]
            drop_na: Remove rows with NaN values (default: True)
        
        Returns:
            DataFrame with computed features
        """
        logger.info(f"Computing features for {len(df)} rows...")
        
        # Preserve timestamp for later use
        if 'timestamp' in df.columns:
            timestamp = df['timestamp'].copy()
        else:
            timestamp = None
        
        # Compute technical indicators
        ti = TechnicalIndicators(df)
        df = ti.compute_all()
        
        # Compute temporal features
        tf = TemporalFeatures(df)
        df = tf.add_all()
        
        # Standardize column names (uppercase)
        df.columns = [col.upper() if col.upper() != col else col for col in df.columns]
        
        # Select only required features
        available_features = [f for f in self.required_features if f.upper() in df.columns]
        available_features = [f.upper() for f in available_features]
        
        missing_features = set([f.upper() for f in self.required_features]) - set(available_features)
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")
        
        df = df[available_features]
        
        # Add timestamp back
        if timestamp is not None:
            df.insert(0, 'TIMESTAMP', timestamp)
        
        # Handle NaN values
        initial_rows = len(df)
        if drop_na:
            df = df.dropna()
            dropped = initial_rows - len(df)
            if dropped > 0:
                logger.info(f"Dropped {dropped} rows with NaN values")
        
        # Reset index after potentially dropping rows
        df = df.reset_index(drop=True)
        
        logger.info(f"✓ Feature computation complete: {len(df)} rows, {len(df.columns)} features")
        return df
    
    def validate_features(self, df: pd.DataFrame) -> bool:
        """
        Validate computed features match training schema
        
        Args:
            df: DataFrame with computed features
        
        Returns:
            True if valid, raises error otherwise
        """
        # Check required features (exclude timestamp which is metadata)
        df_cols = set([c.upper() for c in df.columns if c.upper() != 'TIMESTAMP'])
        required_cols = set([f.upper() for f in self.required_features])
        missing = required_cols - df_cols
        
        if missing:
            raise ValueError(f"Missing required features: {missing}")
        
        # Check for NaN in feature columns (not timestamp)
        feature_df = df[[c for c in df.columns if c.upper() != 'TIMESTAMP']]
        if feature_df.isnull().any().any():
            nan_cols = feature_df.columns[feature_df.isnull().any()].tolist()
            raise ValueError(f"Features contain NaN values: {nan_cols}")
        
        # Check for infinite values
        if np.isinf(feature_df.select_dtypes(include=[np.number])).any().any():
            raise ValueError("Features contain infinite values")
        
        # Check for zero variance (except categorical)
        numeric_cols = feature_df.select_dtypes(include=[np.number]).columns
        zero_var = [col for col in numeric_cols if feature_df[col].std() == 0]
        if zero_var:
            logger.warning(f"Features with zero variance: {zero_var}")
        
        logger.info("✓ Features validation passed")
        return True


def compute_features_from_db(engine, cryptocurrency: str, lookback_days: int = 60) -> pd.DataFrame:
    """
    Fetch recent prices from database and compute features
    
    Args:
        engine: SQLAlchemy database engine
        cryptocurrency: Cryptocurrency name (e.g., 'Bitcoin')
        lookback_days: Number of days to fetch (default: 60)
    
    Returns:
        DataFrame with computed features
    """
    from sqlalchemy import text
    
    logger.info(f"Fetching {lookback_days} days of price data for {cryptocurrency}...")
    
    query = text("""
        SELECT timestamp, open, high, low, close, volume
        FROM prices
        WHERE cryptocurrency = :crypto
        AND timestamp >= NOW() - INTERVAL ':days days'
        ORDER BY timestamp ASC
    """)
    
    with engine.begin() as conn:
        df = pd.read_sql(
            query.bindparams(crypto=cryptocurrency, days=lookback_days),
            conn
        )
    
    if len(df) == 0:
        raise ValueError(f"No price data found for {cryptocurrency}")
    
    logger.info(f"Fetched {len(df)} price records")
    
    # Compute features
    computor = FeatureComputor()
    df_features = computor.compute(df)
    
    return df_features


if __name__ == "__main__":
    # Example usage
    logger.info("=" * 60)
    logger.info("Feature Engineering Pipeline Example")
    logger.info("=" * 60)
    
    # Create sample data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000000, 5000000, 100)
    })
    
    # Compute features
    computor = FeatureComputor()
    features_df = computor.compute(sample_data)
    
    print("\n" + "=" * 60)
    print("Feature Computation Results")
    print("=" * 60)
    print(f"Input rows: {len(sample_data)}")
    print(f"Output rows: {len(features_df)}")
    print(f"Features: {len(features_df.columns)}")
    print(f"\nFeature columns:\n{features_df.columns.tolist()}")
    print(f"\nSample (last row):\n{features_df.iloc[-1]}")
    
    # Validate
    computor.validate_features(features_df)
    print("\n✓ All validations passed!")
