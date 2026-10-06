import sys
sys.stdout.reconfigure(encoding='utf-8')

# Read main_window.py
f = open(r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis\i8080_ci\main_window.py', 'r', encoding='utf-8')
mw = f.read()
f.close()

# Find language switching
idx = mw.find('set_language')
if idx == -1:
    idx = mw.find('language')
print("=== MAIN WINDOW LANGUAGE ===")
print(mw[max(0,idx-300):idx+1000])
print()

# Find set_theme in main_window
idx2 = mw.find('def set_theme')
if idx2 == -1:
    idx2 = mw.find('set_theme')
print("=== MAIN WINDOW SET_THEME ===")
print(mw[max(0,idx2-100):idx2+1500])
print()

# Find where AssemblerWidget is created
idx3 = mw.find('AssemblerWidget')
print("=== ASSEMBLER WIDGET CREATION ===")
print(mw[max(0,idx3-200):idx3+500])
print()

# Read i18n.py
f2 = open(r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis\common\i18n.py', 'r', encoding='utf-8')
i18n = f2.read()
f2.close()

# Find fold-related keys
idx4 = i18n.find('fold_')
print("=== I18N FOLD KEYS ===")
print(i18n[max(0,idx4-100):idx4+500])
print()

# Find get_system_language
idx5 = i18n.find('def get_system_language')
print("=== GET_SYSTEM_LANGUAGE ===")
print(i18n[idx5:idx5+500])
print()

# Find set_language in i18n
idx6 = i18n.find('def set_language')
if idx6 == -1:
    idx6 = i18n.find('set_language')
print("=== SET_LANGUAGE in i18n ===")
print(i18n[max(0,idx6-50):idx6+500])
