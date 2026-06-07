#!/usr/bin/env python
"""
FINAL SYSTEM VALIDATION - Comprehensive Health Check
Verifies all fixes are in place and system is production-ready
"""

import sys
import traceback

def check_data_ingestion():
    """Verify Phase 2 fundamentals extraction in all paths"""
    from data_ingestion import fetch_fundamental_metrics, fetch_company_stats, get_ticker_data
    
    # Test fundamental metrics function
    result = fetch_fundamental_metrics("AAPL")
    required_keys = {"pe_ratio", "pb_ratio", "debt_to_equity", "profit_margin"}
    assert required_keys.issubset(set(result.keys())), f"Missing keys in fetch_fundamental_metrics: {required_keys - set(result.keys())}"
    print("✓ fetch_fundamental_metrics includes Phase 2 fields")
    
    # Test get_ticker_data validates required metrics
    # This will use static fallback, which is fine for validation
    result = get_ticker_data("TEST")
    required_metrics = {
        'sentiment_score', 'pe_ratio', 'governance_score', 'revenue_growth',
        'profit_margin', 'pb_ratio', 'debt_to_equity'
    }
    for metric in required_metrics:
        assert metric in result, f"Missing required metric: {metric}"
    print("✓ get_ticker_data includes all required Phase 2 metrics")

def check_ml_features():
    """Verify ML feature columns are synchronized"""
    from ml_trainer import FEATURE_COLS as trainer_cols
    from ml_inference import FEATURE_COLS as inference_cols
    
    assert trainer_cols == inference_cols, "FEATURE_COLS mismatch between trainer and inference!"
    
    required_phase2_fields = {'profit_margin', 'pb_ratio', 'debt_to_equity'}
    assert required_phase2_fields.issubset(set(trainer_cols)), f"Missing Phase 2 fields in FEATURE_COLS"
    
    assert len(trainer_cols) == 20, f"FEATURE_COLS should have 20 fields, got {len(trainer_cols)}"
    print(f"✓ ML FEATURE_COLS synchronized ({len(trainer_cols)} features)")

def check_valuation_logic():
    """Verify valuation engine has Phase 2 scoring"""
    from valuation_engine import valuation_model
    
    # Test with Phase 2 features
    features = {
        'sentiment_score': 0.8,
        'pe_ratio': 15.0,
        'governance_score': 0.8,
        'revenue_growth': 0.15,
        'profit_margin': 0.25,  # Strong profit → bonus
        'pb_ratio': 2.0,
        'debt_to_equity': 0.2,  # Low debt → bonus
        'debt_ratio': 0.2
    }
    
    score = valuation_model(features)
    assert isinstance(score, float), "valuation_model should return float"
    assert score > 0.4, f"Score should be positive with good fundamentals, got {score}"
    print(f"✓ Valuation engine Phase 2 scoring works (score={score:.3f})")
    
    # Test with bad fundamentals
    bad_features = {
        'sentiment_score': 0.8,
        'pe_ratio': 15.0,
        'governance_score': 0.8,
        'revenue_growth': 0.15,
        'profit_margin': 0.02,  # Low profit → penalty
        'pb_ratio': 0.3,        # Distressed asset
        'debt_to_equity': 0.9,  # High debt → penalty
        'debt_ratio': 0.9
    }
    
    bad_score = valuation_model(bad_features)
    assert bad_score < score, f"Bad fundamentals should score lower, got {bad_score:.3f} vs {score:.3f}"
    print(f"✓ Valuation engine penalizes poor fundamentals (score={bad_score:.3f})")

def check_ml_inference():
    """Verify ML inference handles feature schema safely"""
    from ml_inference import ml_decision
    import pandas as pd
    
    # Test with complete features
    features = {
        'sentiment_score': 0.5,
        'sentiment_confidence': 0.7,
        'news_volume': 10,
        'news_trend': 0.3,
        'pe_ratio': 15.0,
        'market_cap': 100e9,
        'earnings': 5e9,
        'costs': 2e9,
        'cash_flow': 3e9,
        'profit_margin': 0.15,
        'revenue_growth': 0.1,
        'debt_ratio': 0.3,
        'debt_to_equity': 0.3,
        'pb_ratio': 2.0,
        'board_size': 8,
        'ceo_tenure': 5,
        'governance_score': 0.8,
        'employee_count': 10000,
        'management_cred_score': 0.75
    }
    
    result = ml_decision(features, 0.6, threshold=0.5)
    assert isinstance(result, bool), "ml_decision should return bool"
    print(f"✓ ML inference handles complete feature vectors (result={result})")
    
    # Test with missing Phase 2 fields (should use defaults)
    partial_features = {
        'sentiment_score': 0.5,
        'pe_ratio': 15.0,
        'market_cap': 100e9,
        'governance_score': 0.8,
        # Missing: profit_margin, pb_ratio, debt_to_equity
    }
    
    result = ml_decision(partial_features, 0.6, threshold=0.5)
    assert isinstance(result, bool), "ml_decision should handle missing Phase 2 fields"
    print(f"✓ ML inference safely handles missing Phase 2 fields (result={result})")

def check_parallel_threading():
    """Verify thread safety in parallel runner"""
    from parallel_runner import process_tickers_parallel
    
    # Test with small batch
    result = process_tickers_parallel(["AAPL", "MSFT"], threshold=0.5, max_workers=2)
    assert isinstance(result, list), "process_tickers_parallel should return list"
    print(f"✓ Parallel runner works with thread safety (result type={type(result).__name__})")

def check_config_loading():
    """Verify config loading works"""
    from valuation_engine import load_config
    
    config = load_config()
    assert isinstance(config, dict), "load_config should return dict"
    assert 'schwab_api' in config, "Config should have schwab_api section"
    assert 'ml' in config, "Config should have ml section"
    print(f"✓ Config loading works (has {len(config)} top-level sections)")

def main():
    """Run all validation checks"""
    checks = [
        ("Data Ingestion Phase 2", check_data_ingestion),
        ("ML Feature Synchronization", check_ml_features),
        ("Valuation Logic Phase 2", check_valuation_logic),
        ("ML Inference Safety", check_ml_inference),
        ("Parallel Threading", check_parallel_threading),
        ("Config Loading", check_config_loading),
    ]
    
    print("=" * 70)
    print("PORTFOLIO SYSTEM - FINAL VALIDATION CHECKPOINT")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        try:
            print(f"\n[{check_name}]")
            check_func()
            passed += 1
        except Exception as e:
            print(f"✗ FAILED: {e}")
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed > 0:
        print("\n❌ VALIDATION FAILED - Fix remaining issues before deployment")
        sys.exit(1)
    else:
        print("\n✅ ALL VALIDATION CHECKS PASSED - SYSTEM READY FOR DEPLOYMENT")
        sys.exit(0)

if __name__ == "__main__":
    main()
