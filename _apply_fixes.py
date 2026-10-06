import sys
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# FIX 1: Add retranslate() method to AssemblerWidget
# FIX 2: Protect fold marker from { } in content (require leading tab)
# ============================================================

path = r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis\i8080_ci\assembler_widget.py'
f = open(path, 'r', encoding='utf-8')
content = f.read()
f.close()

# --- FIX 2: Protect fold marker regex ---
# Current: m_collapsed = _re.match(r'^\{\d+\}$', code_part.strip())
# Problem: matches ANY line that is just {number} after stripping
# Fix: Only match if the ORIGINAL line starts with a tab character
old_regex = "m_collapsed = _re.match(r'^\\{\\d+\\}$', code_part.strip())"
new_regex = "m_collapsed = _re.match(r'^\\{\\d+\\}$', code_part.strip()) if line.startswith('\\t') else None"

if old_regex in content:
    content = content.replace(old_regex, new_regex)
    print("FIX 2: Fold marker regex protected (requires leading tab)")
else:
    print("FIX 2: WARNING - old regex not found, trying alternate...")
    # Try with different quote style
    old_regex2 = "m_collapsed = _re.match(r'^\\{\\d+\\}$', code_part.strip())"
    if old_regex2 in content:
        content = content.replace(old_regex2, new_regex)
        print("FIX 2: Applied with alternate pattern")
    else:
        # Search for the actual line
        for i, line in enumerate(content.split('\n')):
            if 'm_collapsed' in line and '_re.match' in line:
                print(f"  Found at line {i+1}: {line.strip()}")
                break

# --- FIX 1: Add retranslate() method to AssemblerWidget ---
# Find the end of __init__ or a good place to add the method
# We'll add it after the set_theme method of AssemblerWidget (if exists) or before the first method after __init__

# Find a good insertion point - after the _on_expand_all method or similar
# Let's find "def _on_collapse_all" and add retranslate before it
insert_marker = "    def _on_collapse_all(self):"
retranslate_method = '''    def retranslate(self):
        """Update all translatable strings (called on language change)."""
        self.btn_collapse_all.setToolTip(_tr("fold_collapse_all"))
        self.btn_expand_all.setToolTip(_tr("fold_expand_all"))
        self.btn_assemble.setText(_tr("asm_assemble"))
        self.btn_assemble_load.setText(_tr("asm_assemble_load"))
        self.btn_assemble_obj.setText(_tr("asm_assemble_obj"))
        self.btn_link.setText(_tr("asm_link"))
        # Update folding area tooltips
        if hasattr(self, 'folding_area'):
            self.folding_area.update()

'''

if insert_marker in content:
    content = content.replace(insert_marker, retranslate_method + insert_marker)
    print("FIX 1: Added retranslate() method to AssemblerWidget")
else:
    print("FIX 1: WARNING - insert marker not found")
    # Try alternate
    alt_marker = "    def _on_expand_all(self):"
    if alt_marker in content:
        content = content.replace(alt_marker, retranslate_method + alt_marker)
        print("FIX 1: Added retranslate() before _on_expand_all")
    else:
        print("FIX 1: ERROR - could not find insertion point")

# Write back
f = open(path, 'w', encoding='utf-8')
f.write(content)
f.close()
print("assembler_widget.py saved")

# ============================================================
# FIX 3: Call retranslate() from main_window.retranslate_ui()
# ============================================================
path2 = r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis\i8080_ci\main_window.py'
f = open(path2, 'r', encoding='utf-8')
mw = f.read()
f.close()

# Find the end of retranslate_ui and add assembler widget retranslate call
# We'll add it after the tab text updates
# Look for a good spot - after "self.tabs.setTabText(10, ..."
marker = 'self.tabs.setTabText(10, self.tr("tab_compare"))   # Сравнение'
if marker in mw:
    insert_after = marker + '\n        '
    new_code = insert_after + '# Обновляем переводы ассемблера\n        if hasattr(self, \'assembler_widget\'):\n            self.assembler_widget.retranslate()\n        '
    mw = mw.replace(marker, new_code)
    print("FIX 3: Added assembler_widget.retranslate() to retranslate_ui()")
else:
    print("FIX 3: WARNING - marker not found, trying alternate")
    # Try to find the last setTabText
    last_tab = mw.rfind('self.tabs.setTabText(')
    if last_tab != -1:
        # Find end of that line
        eol = mw.find('\n', last_tab)
        line = mw[last_tab:eol]
        print(f"  Last setTabText: {line.strip()}")
        # Insert after it
        mw = mw[:eol] + '\n        # Обновляем переводы ассемблера\n        if hasattr(self, \'assembler_widget\'):\n            self.assembler_widget.retranslate()' + mw[eol:]
        print("FIX 3: Added after last setTabText")
    else:
        print("FIX 3: ERROR - could not find insertion point")

f = open(path2, 'w', encoding='utf-8')
f.write(mw)
f.close()
print("main_window.py saved")

print("\n=== ALL FIXES APPLIED ===")
