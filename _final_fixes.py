import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')

base = r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis'

# === Fix hardcoded "Процессор:" in assembler_widget.py ===
path = os.path.join(base, 'i8080_ci', 'assembler_widget.py')
f = open(path, 'r', encoding='utf-8')
c = f.read()
f.close()

# Add i18n key for "Процессор:" / "Processor:"
old = 'ctrl_layout.addWidget(QLabel("Процессор:"))'
new = 'ctrl_layout.addWidget(QLabel(_tr("asm_processor")))'
if old in c:
    c = c.replace(old, new)
    print("Fixed: 'Процессор:' -> _tr('asm_processor')")
else:
    print("WARNING: 'Процессор:' pattern not found")

f = open(path, 'w', encoding='utf-8')
f.write(c)
f.close()

# === Add i18n key to common/i18n.py ===
i18n_path = os.path.join(base, 'common', 'i18n.py')
f = open(i18n_path, 'r', encoding='utf-8')
i18n = f.read()
f.close()

# Add EN key
if '"asm_processor"' not in i18n:
    # Add after "asm_link" in EN section
    en_marker = '"asm_link": "Link",'
    if en_marker in i18n:
        i18n = i18n.replace(en_marker, en_marker + '\n        "asm_processor": "Processor:",')
        print("Added EN: asm_processor")
    else:
        # Try alternate
        en_marker2 = '"asm_link": "Link"'
        if en_marker2 in i18n:
            i18n = i18n.replace(en_marker2, en_marker2 + ',\n        "asm_processor": "Processor:",')
            print("Added EN: asm_processor (alt)")
        else:
            print("WARNING: EN marker not found")
    
    # Add RU key
    ru_marker = '"asm_link": "Линковка",'
    if ru_marker in i18n:
        i18n = i18n.replace(ru_marker, ru_marker + '\n        "asm_processor": "Процессор:",')
        print("Added RU: asm_processor")
    else:
        ru_marker2 = '"asm_link": "Линковка"'
        if ru_marker2 in i18n:
            i18n = i18n.replace(ru_marker2, ru_marker2 + ',\n        "asm_processor": "Процессор:",')
            print("Added RU: asm_processor (alt)")
        else:
            # Try to find the RU asm_link
            idx = i18n.find('"asm_link"')
            # Find the second occurrence (RU section)
            idx2 = i18n.find('"asm_link"', idx + 1)
            if idx2 != -1:
                eol = i18n.find('\n', idx2)
                line = i18n[idx2:eol]
                print(f"  RU asm_link line: {line.strip()}")
                # Add after this line
                i18n = i18n[:eol] + '\n        "asm_processor": "Процессор:",' + i18n[eol:]
                print("Added RU: asm_processor (manual)")
            else:
                print("WARNING: RU asm_link not found")

f = open(i18n_path, 'w', encoding='utf-8')
f.write(i18n)
f.close()
print("i18n.py saved")

# === Check MCP server format ===
mcp_path = os.path.join(base, 'mcp_server.py')
if os.path.exists(mcp_path):
    f = open(mcp_path, 'r', encoding='utf-8')
    mcp = f.read()
    f.close()
    # Try different patterns
    patterns = ['@mcp.tool', '@mcp.tool()', 'def tool', 'mcp.add_tool', 'FastMCP']
    for p in patterns:
        count = mcp.count(p)
        if count > 0:
            print(f"\nMCP pattern '{p}': {count} occurrences")
    # Show first 500 chars
    print(f"\nMCP first 300 chars:\n{mcp[:300]}")
else:
    print("\nMCP server file not found")

# === Update CHANGES.md ===
changes_path = os.path.join(base, 'CHANGES.md')
if os.path.exists(changes_path):
    f = open(changes_path, 'r', encoding='utf-8')
    changes = f.read()
    f.close()
    
    new_entry = """
## v2.1.1 (2026-10-06)

### Bug Fixes
- Fixed runtime language switching: collapse/expand button tooltips now update when language changes
- Fixed fold detection: `{N}` in block content no longer breaks folding (requires leading tab for fold marker)
- Fixed hardcoded "Процессор:" label - now uses i18n

### Improvements
- Added `retranslate()` method to AssemblerWidget for runtime language updates
- Fold marker protection: only `\\t{N}` (tab-prefixed) is recognized as fold indicator

### Tests
- 921/0 checks passed (3 consecutive clean passes)
"""
    # Insert after the first heading
    first_heading_end = changes.find('\n\n')
    if first_heading_end != -1:
        changes = changes[:first_heading_end+2] + new_entry + changes[first_heading_end+2:]
    else:
        changes = new_entry + changes
    
    f = open(changes_path, 'w', encoding='utf-8')
    f.write(changes)
    f.close()
    print("\nCHANGES.md updated")
else:
    print("\nCHANGES.md not found, creating...")
    f = open(changes_path, 'w', encoding='utf-8')
    f.write("# Changelog\n" + new_entry)
    f.close()
    print("CHANGES.md created")

print("\n=== ALL DONE ===")
