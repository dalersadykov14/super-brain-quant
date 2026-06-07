import py_compile, glob, sys

files = glob.glob('*.py')
errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
    except Exception as e:
        errors.append((f, str(e)))

if errors:
    for f, e in errors:
        print(f + ' -> ' + e)
    sys.exit(1)
print('ok')
