import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
for f in ['assemble8080/mapfile.py']:
    print("="*30, f, "="*30)
    print(open(f, encoding='utf-8').read())
