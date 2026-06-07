# ml_trainer.py
try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

try:
    from sklearn.model_selection import train_test_split, GridSearchCV
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import classification_report, roc_auc_score
except ModuleNotFoundError:
    train_test_split = None
    GridSearchCV = None
    RandomForestClassifier = None
    StandardScaler = None
    Pipeline = None
    classification_report = None
    roc_auc_score = None

try:
    import joblib
except ModuleNotFoundError:
    joblib = None

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

def train_and_export_model(data_path: str):
    """Trains a production classifier model using hyperparameter tuning optimization."""
    if pd is None:
        raise ImportError("Pandas is required to train the ML model. Install it with 'pip install pandas'.")
    if any(dep is None for dep in [train_test_split, GridSearchCV, RandomForestClassifier, StandardScaler, Pipeline, classification_report, roc_auc_score]):
        raise ImportError("scikit-learn is required to train the ML model. Install it with 'pip install scikit-learn'.")
    if joblib is None:
        raise ImportError("joblib is required to export the trained model. Install it with 'pip install joblib'.")

    raw_data = pd.read_csv(data_path)
    X = raw_data[FEATURE_COLS]
    y = raw_data['included_in_portfolio']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Wrap inside a Pipeline to preserve standardization mappings
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(random_state=42, class_weight='balanced'))
    ])

    param_grid = {
        'classifier__n_estimators': [100, 200],
        'classifier__max_depth': [10, 20, None],
        'classifier__min_samples_split': [2, 5]
    }

    grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring='roc_auc', n_jobs=-1)
    grid_search.fit(X_train, y_train)
    
    best_model = grid_search.best_estimator_
    preds = best_model.predict(X_test)
    probs = best_model.predict_proba(X_test)[:, 1]

    print("--- MODEL TRAINING RUN METRICS ---")
    print(classification_report(y_test, preds))
    print("ROC AUC Metric Score:", roc_auc_score(y_test, probs))

    # Export versioned pickle serialization matrix
    joblib.dump(best_model, "ml_model_v1.pkl")
    print("Saved production model asset to: ml_model_v1.pkl")

if __name__ == "__main__":
    # Generate mock validation file if run directly
    import numpy as np
    mock_data = pd.DataFrame(np.random.randn(100, len(FEATURE_COLS)), columns=FEATURE_COLS)
    mock_data['included_in_portfolio'] = np.random.choice([0, 1], size=100)
    mock_data.to_csv("ticker_training_data.csv", index=False)
    train_and_export_model("ticker_training_data.csv")