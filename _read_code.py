import sys
sys.stdout.reconfigure(encoding='utf-8')

f = open(r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis\i8080_ci\assembler_widget.py', 'r', encoding='utf-8')
c = f.read()
f.close()

# Find btn_collapse_all context
idx = c.find('btn_collapse_all')
print("=== BTN COLLAPSE ALL CONTEXT ===")
print(c[max(0,idx-500):idx+800])
print()

# Find _collapse_region
idx2 = c.find('def _collapse_region')
print("=== _collapse_region ===")
print(c[idx2:idx2+2000])
print()

# Find _expand_region
idx3 = c.find('def _expand_region')
print("=== _expand_region ===")
print(c[idx3:idx3+1500])
print()

# Find _tr function
idx4 = c.find('def _tr')
print("=== _tr ===")
print(c[idx4:idx4+300])
print()

# Find set_theme or language change
idx5 = c.find('set_theme')
if idx5 == -1:
    idx5 = c.find('language')
print("=== LANGUAGE/THEME in widget ===")
print(c[max(0,idx5-200):idx5+500])
