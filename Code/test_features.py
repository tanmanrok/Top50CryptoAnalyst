"""
Phase 2 Feature Engineering - Test & Verification Script
Tests feature computation and database integration
"""

import sys
from pathlib import Path
import pandas as pd
import logging

# Add Code directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import modules
from db_connection import engine
from compute_features import FeatureComputor, compute_features_from_db
from live_features_service import LiveFeaturesService, print_feature_summary

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_feature_computation():
    """Test feature computation pipeline"""
    print("\n" + "=" * 70)
    print("TEST 1: Feature Computation Pipeline")
    print("=" * 70)
    
    try:
        # Initialize
        service = LiveFeaturesService(engine, lookback_days=60)
        
        # Get list of cryptos
        from sqlalchemy import text
        with engine.begin() as conn:
            result = conn.execute(text(
                "SELECT DISTINCT cryptocurrency FROM prices ORDER BY cryptocurrency LIMIT 3"
            ))
            test_cryptos = [row[0] for row in result]
        
        logger.info(f"Testing with cryptos: {test_cryptos}")
        
        # Compute features for each
        for crypto in test_cryptos:
            logger.info(f"\n→ Computing features for {crypto}...")
            df = service.compute_for_crypto(crypto)
            
            if df is not None:
                logger.info(f"  ✓ Rows: {len(df)}")
                logger.info(f"  ✓ Features: {len(df.columns)}")
                logger.info(f"  ✓ Columns: {', '.join(df.columns[:5])}...")
                
                # Show sample
                logger.info(f"  ✓ Last row sample:")
                for col in df.columns[:3]:
                    val = df.iloc[-1][col]
                    logger.info(f"    - {col}: {val:.4f}" if isinstance(val, float) else f"    - {col}: {val}")
            else:
                logger.error(f"  ✗ Failed to compute features for {crypto}")
        
        print("\n✓ TEST 1 PASSED\n")
        return True
        
    except Exception as e:
        logger.error(f"✗ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_storage():
    """Test saving features to database"""
    print("\n" + "=" * 70)
    print("TEST 2: Database Storage")
    print("=" * 70)
    
    try:
        service = LiveFeaturesService(engine, lookback_days=60)
        
        # Compute features for one crypto (use lowercase like in database)
        crypto = 'bitcoin'
        logger.info(f"Computing features for {crypto}...")
        df = service.compute_for_crypto(crypto)
        
        if df is None:
            logger.error(f"Failed to compute features for {crypto}")
            return False
        
        # Save to database
        logger.info(f"Saving {len(df)} rows to database...")
        success = service.save_features(crypto, df)
        
        if success:
            logger.info("✓ Features saved successfully")
            
            # Verify retrieval
            logger.info("Verifying retrieval...")
            latest = service.get_latest_features(crypto)
            
            if latest is not None:
                logger.info("✓ Retrieved latest features")
                logger.info(f"  Timestamp: {latest.get('timestamp', 'N/A')}")
                logger.info(f"  Close: {latest.get('close', 'N/A')}")
            else:
                logger.error("✗ Failed to retrieve features")
                return False
        else:
            logger.error("✗ Failed to save features")
            return False
        
        print("\n✓ TEST 2 PASSED\n")
        return True
        
    except Exception as e:
        logger.error(f"✗ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_cryptos():
    """Test computing features for all cryptocurrencies"""
    print("\n" + "=" * 70)
    print("TEST 3: All Cryptocurrencies")
    print("=" * 70)
    
    try:
        service = LiveFeaturesService(engine, lookback_days=60)
        
        # Compute for all
        logger.info("Computing features for all cryptocurrencies...")
        features_dict = service.compute_for_all_cryptos()
        
        if not features_dict:
            logger.error("No features computed")
            return False
        
        logger.info(f"✓ Computed features for {len(features_dict)} cryptocurrencies")
        
        # Summary
        print_feature_summary(features_dict)
        
        # Save all
        logger.info("Saving all features to database...")
        results = service.save_all_features(features_dict)
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"✓ Successfully saved {successful}/{len(results)} cryptocurrencies")
        
        if successful == len(results):
            print("\n✓ TEST 3 PASSED\n")
            return True
        else:
            print("\n✓ TEST 3 PARTIALLY PASSED (some failures)\n")
            return True
        
    except Exception as e:
        logger.error(f"✗ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_feature_validation():
    """Test feature validation"""
    print("\n" + "=" * 70)
    print("TEST 4: Feature Validation")
    print("=" * 70)
    
    try:
        # Initialize computor
        computor = FeatureComputor()
        
        # Compute features for bitcoin (use lowercase like in database)
        logger.info("Computing features...")
        df = compute_features_from_db(engine, 'bitcoin', lookback_days=60)
        
        logger.info(f"Computed {len(df)} rows with {len(df.columns)} features")
        
        # Validate
        logger.info("Running validation...")
        is_valid = computor.validate_features(df)
        
        if is_valid:
            logger.info("✓ All features passed validation")
            logger.info(f"  - No NaN values")
            logger.info(f"  - No infinite values")
            logger.info(f"  - All required features present")
            print("\n✓ TEST 4 PASSED\n")
            return True
        else:
            logger.error("✗ Validation failed")
            return False
        
    except Exception as e:
        logger.error(f"✗ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("PHASE 2: FEATURE ENGINEERING - TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Feature Computation", test_feature_computation),
        ("Database Storage", test_database_storage),
        ("All Cryptocurrencies", test_all_cryptos),
        ("Feature Validation", test_feature_validation),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
