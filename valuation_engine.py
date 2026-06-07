# valuation_engine.py
import logging

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


def load_config():
    if yaml is None:
        raise ImportError("PyYAML is required to load config.yaml. Install it with 'pip install pyyaml'.")

    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def valuation_model(features: dict) -> float:
    """Generates composite valuation scoring bounds with Phase 2 Fundamental Overlay (Brief Sec. 4).
    
    PHASE 2 ENHANCEMENT: Fundamental metrics now directly influence valuation score:
    - Profit margin: Validates earnings quality (high sentiment only trusted if profitable)
    - Debt-to-equity: Filters balance sheet risk (prevents cheap leverage traps)
    - Price-to-book: Asset valuation anchor (prevents distressed company false positives)
    """
    config = load_config()
    weights = config.get("valuation_weights", {})
    
    pe = features.get("pe_ratio", 1.0)
    
    # MATH ERROR CORRECTED: Explicitly handle negative or zero P/E values to prevent ZeroDivisionError
    if pe <= 0:
        logging.debug(f"Negative or zero earnings valuation flagged ({pe}). Assigning a value score of 0.0.")
        value_score = 0.0
    else:
        value_score = 1.0 / pe

    # Base valuation score
    score = (
        weights.get("sentiment", 0.40) * features.get("sentiment_score", 0.0) +
        weights.get("value", 0.30) * value_score +
        weights.get("growth", 0.20) * features.get("revenue_growth", 0.0) +
        weights.get("governance", 0.10) * features.get("governance_score", 0.0)
    )
    
    # === PHASE 2 FUNDAMENTAL OVERLAY ADJUSTMENTS ===
    
    # PROFIT MARGIN CHECK: High sentiment only trusted if company is actually profitable
    profit_margin = features.get("profit_margin", 0.0)
    if profit_margin < 0.05:
        # Low profitability: apply skepticism discount to sentiment boost
        logging.debug(f"Low profit margin ({profit_margin:.2%}). Applying fundamental skepticism (-0.15).")
        score -= 0.15
    elif profit_margin > 0.20:
        # Strong profitability: reward with fundamental quality bonus
        logging.debug(f"Strong profit margin ({profit_margin:.2%}). Applying quality bonus (+0.10).")
        score += 0.10
    
    # DEBT-TO-EQUITY CHECK: High leverage undermines any technical upside
    debt_to_equity = features.get("debt_to_equity", features.get("debt_ratio", 0.0))
    if debt_to_equity > 0.75:
        # High leverage: significant risk penalty
        logging.debug(f"High debt-to-equity ({debt_to_equity:.2f}). Applying risk penalty (-0.20).")
        score -= 0.20
    elif debt_to_equity < 0.30:
        # Low leverage: conservative balance sheet bonus
        logging.debug(f"Conservative debt-to-equity ({debt_to_equity:.2f}). Applying safety bonus (+0.08).")
        score += 0.08
    
    # PRICE-TO-BOOK ANCHOR: Prevents distressed or wildly overvalued companies
    pb_ratio = features.get("pb_ratio", 0.0)
    if pb_ratio > 3.0:
        # Overvalued asset basis: apply valuation caution
        logging.debug(f"High price-to-book ({pb_ratio:.2f}). Applying valuation caution (-0.12).")
        score -= 0.12
    elif pb_ratio < 0.5:
        # Deeply discounted asset basis: could indicate distress (combine with debt check)
        if debt_to_equity > 0.6:
            logging.debug(f"Distressed asset (PB={pb_ratio:.2f}, D/E={debt_to_equity:.2f}). Applying distress penalty (-0.25).")
            score -= 0.25
        else:
            logging.debug(f"Deep value opportunity (PB={pb_ratio:.2f}, healthy D/E). Applying value bonus (+0.15).")
            score += 0.15
    
    # Legacy debt ratio check (kept for backward compatibility)
    debt = features.get("debt_ratio", 0.0)
    if debt > 2.5:
        score -= 0.10
        
    return float(score)