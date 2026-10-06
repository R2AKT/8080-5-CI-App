import sys
sys.stdout.reconfigure(encoding='utf-8')

f = open(r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis\i8080_ci\main_window.py', 'r', encoding='utf-8')
mw = f.read()
f.close()

# Find on_lang_changed
idx = mw.find('def on_lang_changed')
print("=== ON_LANG_CHANGED ===")
print(mw[idx:idx+2000])
print()

# Find retranslate_ui
idx2 = mw.find('def retranslate_ui')
if idx2 == -1:
    idx2 = mw.find('retranslate')
print("=== RETRANSLATE ===")
print(mw[max(0,idx2-50):idx2+2000])
