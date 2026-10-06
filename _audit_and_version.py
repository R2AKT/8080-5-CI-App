import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')

base = r'c:\Мега-80\8080-5 CI\i8080-5_CI-AI-analysis'

# === TASK 3: i18n audit - find hardcoded strings in assembler_widget.py ===
print("=== I18N AUDIT: assembler_widget.py ===")
f = open(os.path.join(base, 'i8080_ci', 'assembler_widget.py'), 'r', encoding='utf-8')
c = f.read()
f.close()

# Find QPushButton/QLabel with hardcoded text (not using _tr)
# Pattern: QPushButton("...") or QLabel("...") without _tr
hardcoded = []
for i, line in enumerate(c.split('\n'), 1):
    stripped = line.strip()
    # Look for QPushButton("...") or QLabel("...") with literal text
    m = re.match(r'(?:self\.\w+\s*=\s*)?(?:QPushButton|QLabel)\("([^"]+)"\)', stripped)
    if m and '_tr(' not in line and 'self.tr(' not in line:
        text = m.group(1)
        # Skip icon-like strings (single chars, symbols)
        if len(text) > 2 and not re.match(r'^[\u2600-\u27BF\u2B00-\u2BFF\W]+$', text):
            hardcoded.append((i, stripped[:80], text))

if hardcoded:
    print(f"Found {len(hardcoded)} potentially hardcoded strings:")
    for ln, code, text in hardcoded[:20]:
        print(f"  Line {ln}: '{text}' -> {code}")
else:
    print("No hardcoded strings found (all use _tr)")

# Also check for "Процессор:" which I saw earlier
if 'Процессор:' in c:
    idx = c.find('Процессор:')
    print(f"\n  Found hardcoded 'Процессор:' at position {idx}")
    print(f"  Context: {c[max(0,idx-50):idx+50].strip()}")

# === TASK 4: Check MCP server ===
print("\n=== MCP SERVER CHECK ===")
mcp_path = os.path.join(base, 'mcp_server.py')
if os.path.exists(mcp_path):
    f = open(mcp_path, 'r', encoding='utf-8')
    mcp = f.read()
    f.close()
    # Count tools
    tool_count = mcp.count('@mcp.tool')
    print(f"MCP server: {tool_count} tools registered")
    # Check if fold-related tools exist
    if 'fold' in mcp.lower():
        print("  Fold-related tools: YES")
    else:
        print("  Fold-related tools: NO (may need to add)")
    # Check for version tool
    if 'version' in mcp.lower():
        print("  Version tool: YES")
    else:
        print("  Version tool: NO")
else:
    print("mcp_server.py not found")

# === TASK 9: Version bump ===
print("\n=== VERSION BUMP ===")
ver_path = os.path.join(base, 'version.py')
f = open(ver_path, 'r', encoding='utf-8')
ver = f.read()
f.close()
print(f"Current: {ver.strip()}")

# Bump patch version
import re
m = re.search(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', ver)
if m:
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    patch += 1
    new_ver = f"{major}.{minor}.{patch}"
    ver = ver.replace(f'"{m.group(1)}.{m.group(2)}.{m.group(3)}"', f'"{new_ver}"')
    # Update build date
    ver = re.sub(r'__build__\s*=\s*"\d+"', '__build__ = "20261006"', ver)
    f = open(ver_path, 'w', encoding='utf-8')
    f.write(ver)
    f.close()
    print(f"New version: {new_ver}")

print("\n=== DONE ===")
