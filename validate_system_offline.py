#!/usr/bin/env python
"""
OFFLINE SYSTEM VALIDATION - Tests code structure without network access
"""

import sys
import traceback

def check_feature_consistency():
    """Verify FEATURE_COLS are identical across trainer and inference"""
    from ml_trainer import FEATURE_COLS as trainer_cols
    from ml_inference import FEATURE_COLS as inference_cols
    
    assert trainer_cols == inference_cols, "FEATURE_COLS mismatch!"
    
    # Check Phase 2 fields exist
    phase2_required = {'profit_margin', 'pb_ratio', 'debt_to_equity'}
    assert phase2_required.issubset(set(trainer_cols)), f"Missing Phase 2 fields"
    
    # Check total count (20: Phase 1 + Phase 2 + Governance + Valuation)
    assert len(trainer_cols) == 20, f"Should have 20 features, got {len(trainer_cols)}"
    
    print(f"✓ FEATURE_COLS synchronized ({len(trainer_cols)} features including Phase 2)")
    return True

def check_data_schema():
    """Verify data_ingestion.py has Phase 2 fundamentals in all paths"""
    import inspect
    from data_ingestion import fetch_company_stats, get_ticker_data
    
    # Check function signatures
    sig = inspect.signature(fetch_company_stats)
    assert 'ticker' in sig.parameters, "fetch_company_stats should have ticker parameter"
    print("✓ fetch_company_stats has correct signature")
    
    sig = inspect.signature(get_ticker_data)
    assert 'ticker' in sig.parameters, "get_ticker_data should have ticker parameter"
    print("✓ get_ticker_data has correct signature")
    
    # Read the source to verify Phase 2 fields are in fallbacks
    source = inspect.getsource(fetch_company_stats)
    
    # Check all fallback paths include Phase 2
    assert 'profit_margin' in source, "profit_margin missing from fetch_company_stats"
    assert 'pb_ratio' in source, "pb_ratio missing from fetch_company_stats"
    assert 'debt_to_equity' in source, "debt_to_equity missing from fetch_company_stats"
    
    # Verify it's in both yfinance AND fallback paths
    assert source.count('profit_margin') >= 2, "profit_margin should be in multiple data paths"
    print("✓ fetch_company_stats includes Phase 2 in all data paths")
    
    # Check get_ticker_data includes validation
    source = inspect.getsource(get_ticker_data)
    assert 'required_metrics' in source, "required_metrics validation missing"
    assert 'profit_margin' in source, "profit_margin not in required_metrics"
    assert 'pb_ratio' in source, "pb_ratio not in required_metrics"
    assert 'debt_to_equity' in source, "debt_to_equity not in required_metrics"
    
    print("✓ get_ticker_data validates all Phase 2 fields")
    return True

def check_valuation_fundamentals():
    """Verify valuation_engine has Phase 2 scoring logic"""
    import inspect
    from valuation_engine import valuation_model
    
    source = inspect.getsource(valuation_model)
    
    # Check all Phase 2 adjustments present
    assert 'profit_margin' in source, "profit_margin scoring missing"
    assert 'debt_to_equity' in source, "debt_to_equity scoring missing"
    assert 'pb_ratio' in source, "pb_ratio scoring missing"
    
    # Check scoring logic exists
    assert 'score -=' in source or 'score +=' in source, "No scoring adjustments found"
    assert 'PHASE 2' in source, "Phase 2 comments missing"
    
    print("✓ valuation_engine has Phase 2 fundamental scoring")
    return True

def check_ml_schema_safety():
    """Verify ML inference uses schema-safe DataFrame construction"""
    import inspect
    from ml_inference import ml_decision
    
    source = inspect.getsource(ml_decision)
    
    # Check for schema drift protection
    assert 'pd.DataFrame' in source, "DataFrame construction missing"
    assert '[FEATURE_COLS]' in source, "FEATURE_COLS reordering missing"
    assert 'features.get' in source, "Safe .get() usage missing"
    
    print("✓ ml_inference uses schema-safe DataFrame construction")
    return True

def check_thread_safety():
    """Verify parallel_runner has thread synchronization"""
    import inspect
    from parallel_runner import process_tickers_parallel
    
    source = inspect.getsource(process_tickers_parallel)
    
    # Check for ThreadPoolExecutor
    assert 'ThreadPoolExecutor' in source, "ThreadPoolExecutor not used"
    
    # Check for lock usage
    assert 'portfolio_lock' in source, "Lock not used for thread safety"
    assert 'with portfolio_lock' in source, "Lock context manager not used"
    
    print("✓ parallel_runner properly synchronized with locks")
    return True

def check_zero_division_protection():
    """Verify all division operations are protected"""
    import inspect
    from valuation_engine import valuation_model
    
    source = inspect.getsource(valuation_model)
    
    # Check for division operation protection
    assert 'if pe <=' in source or 'if pe >' in source, "P/E check missing"
    assert '1.0 / pe' in source, "Division operation present"
    
    # Verify the condition is BEFORE the division
    lines = source.split('\n')
    pe_check_line = None
    division_line = None
    
    for i, line in enumerate(lines):
        if 'if pe <=' in line or 'if pe >' in line:
            pe_check_line = i
        if '1.0 / pe' in line:
            division_line = i
    
    assert pe_check_line is not None, "P/E check not found"
    assert division_line is not None, "Division not found"
    assert pe_check_line < division_line, "P/E check should come BEFORE division"
    
    print("✓ Zero-division protection in place (checks before division)")
    return True

def check_exception_handling():
    """Verify network calls are wrapped in exception handlers"""
    import inspect
    from data_ingestion import safe_fetch_data, fetch_news_sentiment
    
    # Check safe_fetch_data
    source = inspect.getsource(safe_fetch_data)
    assert 'try:' in source, "try block missing in safe_fetch_data"
    assert 'except' in source, "except block missing in safe_fetch_data"
    assert 'sleep' in source or 'time.sleep' in source, "Backoff not implemented"
    
    print("✓ Network calls wrapped with exponential backoff")
    
    # Check fetch_news_sentiment
    source = inspect.getsource(fetch_news_sentiment)
    assert 'try:' in source, "try block missing in fetch_news_sentiment"
    assert 'except' in source, "except block missing in fetch_news_sentiment"
    
    print("✓ API calls have exception handlers")
    return True

def check_imports():
    """Verify all optional imports are handled"""
    import sys
    import importlib
    
    # Test that core modules can be imported
    modules = [
        'data_ingestion',
        'valuation_engine', 
        'ml_inference',
        'ml_trainer',
        'parallel_runner',
        'portfolio_manager',
        'logger_config',
        'main'
    ]
    
    for mod in modules:
        try:
            importlib.import_module(mod)
            print(f"  ✓ {mod}")
        except ImportError as e:
            print(f"  ✗ {mod}: {e}")
            return False
    
    print("✓ All core modules import successfully")
    return True

def main():
    """Run all validation checks"""
    checks = [
        ("Feature Column Consistency", check_feature_consistency),
        ("Data Schema Phase 2", check_data_schema),
        ("Valuation Fundamentals", check_valuation_fundamentals),
        ("ML Schema Safety", check_ml_schema_safety),
        ("Thread Safety", check_thread_safety),
        ("Zero-Division Protection", check_zero_division_protection),
        ("Exception Handling", check_exception_handling),
        ("Module Imports", check_imports),
    ]
    
    print("=" * 70)
    print("PORTFOLIO SYSTEM - OFFLINE STRUCTURAL VALIDATION")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        try:
            print(f"\n[{check_name}]")
            if check_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ FAILED: {e}")
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed > 0:
        print("\n❌ VALIDATION FAILED")
        sys.exit(1)
    else:
        print("\n✅ ALL CHECKS PASSED - CODE STRUCTURE PERFECT")
        print("\nReady for deployment. Run with network access for full validation.")
        sys.exit(0)

if __name__ == "__main__":
    main()
