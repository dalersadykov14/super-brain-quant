import importlib
import traceback
import os

os.chdir(r'c:\Users\daler\Documents\Portfolio_system')
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
        print(f'OK: {mod}')
    except Exception as e:
        print(f'ERR: {mod} -> {type(e).__name__}: {e}')
        traceback.print_exc()
