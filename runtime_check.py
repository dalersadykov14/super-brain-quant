import importlib
import os
import sys
import yaml

print('Runtime environment validation')

# 1. Check required packages
required = ['pyyaml', 'requests', 'pandas', 'scikit-learn', 'joblib', 'numpy']
missing = []
for pkg in required:
    try:
        importlib.import_module(pkg)
    except Exception:
        missing.append(pkg)

if missing:
    print('Missing packages:', ', '.join(missing))
else:
    print('All required packages appear importable.')

# 2. Load config.yaml
cfg_path = 'config.yaml'
if not os.path.exists(cfg_path):
    print('Missing config.yaml')
    sys.exit(1)

with open(cfg_path, 'r') as f:
    try:
        cfg = yaml.safe_load(f)
        print('Loaded config.yaml')
    except Exception as e:
        print('Failed to parse config.yaml:', e)
        sys.exit(1)

schwab = cfg.get('schwab_api', {})
print('Schwab config: enable_live_trades=', schwab.get('enable_live_trades'))

if schwab.get('enable_live_trades'):
    # Check env vars
    for k in ['SCHWAB_CLIENT_ID', 'SCHWAB_CLIENT_SECRET', 'SCHWAB_ACCOUNT_ID']:
        if not os.getenv(k):
            print('Warning: missing environment variable', k)
    # Ensure redirect_uri present
    if not schwab.get('redirect_uri'):
        print('Warning: schwab.redirect_uri not set in config.yaml')

# 3. Optional API keys
alpha_key = os.getenv('ALPHA_VANTAGE_API_KEY')
news_key = os.getenv('NEWS_API_KEY')

if alpha_key:
    print('Alpha Vantage API key present; performing harmless probe...')
    try:
        import requests
        resp = requests.get(
            'https://www.alphavantage.co/query',
            params={'function': 'GLOBAL_QUOTE', 'symbol': 'IBM', 'apikey': alpha_key},
            timeout=10
        )
        if resp.status_code == 200:
            print('Alpha Vantage probe succeeded (status 200).')
        else:
            print(f'Alpha Vantage probe warning: HTTP {resp.status_code}')
    except Exception as e:
        print('Alpha Vantage probe error:', e)
else:
    print('Alpha Vantage API key absent; data_ingestion will use fallbacks')

if news_key:
    print('NewsAPI key present; performing harmless probe...')
    try:
        import requests
        resp = requests.get(
            'https://newsapi.org/v2/everything',
            params={'q': 'AAPL', 'pageSize': 1, 'apiKey': news_key},
            timeout=10
        )
        if resp.status_code == 200:
            print('NewsAPI probe succeeded (status 200).')
        else:
            print(f'NewsAPI probe warning: HTTP {resp.status_code}')
    except Exception as e:
        print('NewsAPI probe error:', e)
else:
    print('NewsAPI key absent; sentiment will be fallback heuristic')

print('Runtime check complete')
