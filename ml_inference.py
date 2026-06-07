# ml_inference.py
import logging
from valuation_engine import load_config

try:
    import joblib
except ModuleNotFoundError:
    joblib = None

try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

ml_model = None
if joblib is not None:
    try:
        ml_model = joblib.load("ml_model_v1.pkl")
    except FileNotFoundError:
        logging.warning("ml_model_v1.pkl missing. Activating basic fallback rule logic.")
    except Exception as e:
        logging.warning(f"Failed to load ML model artifact: {e}. Activating fallback rule logic.")

FEATURE_COLS = [
    # === PHASE 1: TECHNICAL MOMENTUM BASELINE ===
    'sentiment_score', 'sentiment_confidence', 'news_volume', 'news_trend',
    'pe_ratio', 'market_cap',
    
    # === PHASE 2: FUNDAMENTAL OVERLAY (STRUCTURAL VALUE) ===
    # Business Profitability & Cash Generation
    'earnings', 'costs', 'cash_flow', 'profit_margin',
    
    # Growth & Health Indicators
    'revenue_growth', 'debt_ratio', 'debt_to_equity', 'pb_ratio',
    
    # Governance & Management Strength (Phase 2 expansion)
    'board_size', 'ceo_tenure', 'governance_score', 
    'employee_count', 'management_cred_score',
    
    # Composite Valuation Score
    'valuation_score'
]

def ml_decision(features: dict, valuation_score: float, threshold: float = 0.5) -> bool:
    """Enforces strict pandas column ordering to prevent feature alignment drift errors."""
    if ml_model is None:
        config = load_config()
        fallback = config.get("ml", {}).get("fallback_valuation_threshold", 0.0)
        return valuation_score > fallback

    if pd is None:
        logging.error("Pandas unavailable; falling back to valuation-only decision logic.")
        config = load_config()
        fallback = config.get("ml", {}).get("fallback_valuation_threshold", 0.0)
        return valuation_score > fallback

    # SCHEMA DRIFT CORRECTED: Construct dictionary and map into an ordered DataFrame row
    row = {k: [features.get(k, 0.0)] for k in FEATURE_COLS if k != 'valuation_score'}
    row['valuation_score'] = [valuation_score]
    
    # Enforces feature index mapping to exactly align with model expectations
    df_vector = pd.DataFrame(row)[FEATURE_COLS]
    
    probability = ml_model.predict_proba(df_vector)[0][1]
    logging.info(f"Target Selection: ML Score Prediction Probability={probability:.4f} against Threshold={threshold}")
    return bool(probability > threshold)