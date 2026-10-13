import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
print("=== version.py ===")
print(open('version.py', encoding='utf-8').read())
print("=== README (version refs) ===")
for i,l in enumerate(open('README.md', encoding='utf-8').read().splitlines()):
    if re.search(r'2\.1\.\d|version|badge|v2\.', l, re.I):
        print(f"{i+1}: {l}")
print("=== CHANGES.md (first 30 lines) ===")
for i,l in enumerate(open('CHANGES.md', encoding='utf-8').read().splitlines()[:30]):
    print(f"{i+1}: {l}")
