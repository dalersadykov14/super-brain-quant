#!/usr/bin/env python
"""Quick validation of Alpha Vantage API key."""

import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: requests library not installed. Run: pip install requests")
    sys.exit(1)

api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

if not api_key:
    print("ERROR: ALPHA_VANTAGE_API_KEY not set in environment.")
    print("Set it in .env or export it: export ALPHA_VANTAGE_API_KEY='your_key'")
    sys.exit(1)

print(f"Testing Alpha Vantage key: {api_key[:10]}...")

try:
    resp = requests.get(
        'https://www.alphavantage.co/query',
        params={
            'function': 'GLOBAL_QUOTE',
            'symbol': 'IBM',
            'apikey': api_key
        },
        timeout=10
    )
    
    if resp.status_code != 200:
        print(f"ERROR: HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)
    
    data = resp.json()
    
    if 'Global Quote' in data and data['Global Quote']:
        quote = data['Global Quote']
        symbol = quote.get('01. symbol', 'N/A')
        price = quote.get('05. price', 'N/A')
        print(f"✓ Alpha Vantage key is valid!")
        print(f"  Sample: {symbol} @ ${price}")
    elif 'Error Message' in data:
        print(f"ERROR: {data['Error Message']}")
        sys.exit(1)
    elif 'Note' in data:
        print(f"WARNING: {data['Note']}")
        print("  (This may indicate rate limiting or API load. Key is likely valid.)")
    else:
        print("✓ Alpha Vantage key appears valid (unexpected response format, but no error)")
        print(f"  Response: {data}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
