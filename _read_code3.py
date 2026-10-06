import sys
sys.stdout.reconfigure(encoding='utf-8')

f = open(r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis\i8080_ci\main_window.py', 'r', encoding='utf-8')
mw = f.read()
f.close()

# Find language combo box
idx = mw.find('lang_combo')
print("=== LANG COMBO ===")
print(mw[max(0,idx-200):idx+800])
print()

# Find on_language_changed or similar
idx2 = mw.find('on_lang')
if idx2 == -1:
    idx2 = mw.find('language_changed')
if idx2 == -1:
    idx2 = mw.find('current_lang')
print("=== LANGUAGE CHANGED HANDLER ===")
print(mw[max(0,idx2-100):idx2+1500])
print()

# Find where AssemblerWidget is instantiated
idx3 = mw.find('AssemblerWidget(')
print("=== ASSEMBLER WIDGET INSTANTIATION ===")
print(mw[max(0,idx3-200):idx3+500])
print()

# Find current_lang attribute
idx4 = mw.find('self.current_lang')
print("=== CURRENT_LANG ===")
print(mw[max(0,idx4-200):idx4+500])
