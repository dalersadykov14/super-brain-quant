import py_compile, traceback, sys
try:
    py_compile.compile('portfolio_manager.py', doraise=True)
    print('ok')
except Exception:
    traceback.print_exc()
    sys.exit(1)
