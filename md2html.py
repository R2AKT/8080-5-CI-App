"""Convert Markdown to HTML with sticky nav, CSS, responsive design.

Usage:
    python md2html.py [input.md] [output.html]

If output is omitted, it is derived from input (same name, .html extension).
If input is omitted, the script prints usage and exits.
"""
import re
import os
import sys
import argparse

parser = argparse.ArgumentParser(
    description='Convert Markdown file to styled HTML with sticky navigation.'
)
parser.add_argument('input', nargs='?', help='Input Markdown file (.md)')
parser.add_argument('output', nargs='?', help='Output HTML file (.html)')
args = parser.parse_args()

if not args.input:
    parser.print_usage()
    sys.exit(1)

MD_PATH = args.input
HTML_PATH = args.output or os.path.splitext(MD_PATH)[0] + '.html'

if not os.path.isfile(MD_PATH):
    print(f"Error: file not found: {MD_PATH}", file=sys.stderr)
    sys.exit(1)

with open(MD_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# --- Inline formatting ---
def inline(text):
    # Code spans
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic (single *)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text

# --- Parse markdown into HTML ---
html_parts = []
in_code = False
code_lines = []
code_lang = ''
in_table = False
table_rows = []
in_ul = False
in_ol = False
ol_counter = 0
in_blockquote = False
blockquote_lines = []

def flush_code():
    global code_lines, in_code
    if code_lines:
        html_parts.append(f'<pre><code>{"".join(code_lines)}</code></pre>')
        code_lines = []
    in_code = False

def flush_table():
    global table_rows, in_table
    if table_rows:
        rows_html = []
        for i, row in enumerate(table_rows):
            cells = [c.strip() for c in row.strip('|').split('|')]
            # Skip separator rows (all dashes/colons)
            if all(re.match(r'^[-:]+$', c) for c in cells if c):
                continue
            tag = 'th' if i == 0 else 'td'
            cells_html = ''.join(f'<{tag}>{inline(c)}</{tag}>' for c in cells)
            rows_html.append(f'<tr>{cells_html}</tr>')
        html_parts.append('<table>\n' + '\n'.join(rows_html) + '\n</table>')
        table_rows = []
    in_table = False

def flush_ul():
    global in_ul
    if in_ul:
        html_parts.append('</ul>')
        in_ul = False

def flush_ol():
    global in_ol, ol_counter
    if in_ol:
        html_parts.append('</ol>')
        in_ol = False
        ol_counter = 0

def flush_blockquote():
    global blockquote_lines, in_blockquote
    if blockquote_lines:
        content = ''.join(blockquote_lines)
        html_parts.append(f'<blockquote>{content}</blockquote>')
        blockquote_lines = []
    in_blockquote = False

def flush_all():
    flush_code()
    flush_table()
    flush_ul()
    flush_ol()
    flush_blockquote()

# Collect section headers for nav
sections = []  # (level, text, anchor)

for line in lines:
    line = line.rstrip('\n')
    
    # Code block toggle
    if line.strip().startswith('```'):
        if not in_code:
            flush_all()
            in_code = True
            code_lang = line.strip()[3:].strip()
        else:
            flush_code()
        continue
    
    if in_code:
        code_lines.append(line + '\n')
        continue
    
    # Table detection
    if line.strip().startswith('|'):
        if not in_table:
            flush_all()
            in_table = True
        table_rows.append(line)
        continue
    elif in_table:
        flush_table()
    
    # Blockquote
    if line.strip().startswith('>'):
        if not in_blockquote:
            flush_all()
            in_blockquote = True
        blockquote_lines.append(inline(line.strip().lstrip('> ')) + '\n')
        continue
    elif in_blockquote:
        flush_blockquote()
    
    # Unordered list
    ul_match = re.match(r'^(\s*)[-*+]\s+(.*)', line)
    if ul_match:
        if not in_ul:
            flush_all()
            in_ul = True
            html_parts.append('<ul>')
        html_parts.append(f'<li>{inline(ul_match.group(2))}</li>')
        continue
    elif in_ul:
        flush_ul()
    
    # Ordered list
    ol_match = re.match(r'^(\s*)(\d+)[.)]\s+(.*)', line)
    if ol_match:
        if not in_ol:
            flush_all()
            in_ol = True
            html_parts.append('<ol>')
        html_parts.append(f'<li>{inline(ol_match.group(3))}</li>')
        continue
    elif in_ol:
        flush_ol()
    
    # Headers
    header_match = re.match(r'^(#{1,6})\s+(.*)', line)
    if header_match:
        flush_all()
        level = len(header_match.group(1))
        text = header_match.group(2).strip()
        # Create anchor
        anchor = re.sub(r'[^\w\s\-]', '', text.lower()).strip().replace(' ', '-')
        # Remove non-ascii for anchor
        anchor = re.sub(r'[^\w\-]', '', anchor)
        if not anchor:
            anchor = f'section-{len(sections)}'
        sections.append((level, text, anchor))
        html_parts.append(f'<h{level} id="{anchor}">{inline(text)}</h{level}>')
        continue
    
    # Horizontal rule
    if re.match(r'^\s*[-*_]{3,}\s*$', line):
        flush_all()
        html_parts.append('<hr>')
        continue
    
    # Empty line
    if not line.strip():
        flush_all()
        continue
    
    # Paragraph
    flush_all()
    html_parts.append(f'<p>{inline(line)}</p>')

# Flush remaining
flush_all()

body_html = '\n'.join(html_parts)

# --- Build nav from sections (only h2) ---
nav_items = []
for level, text, anchor in sections:
    if level == 2:
        # Clean text for nav (remove / RU part for brevity)
        nav_text = text.split('/')[0].strip()
        nav_items.append(f'<a href="#{anchor}">{nav_text}</a>')

nav_html = '\n'.join(nav_items)

# --- Full HTML ---
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{os.path.splitext(os.path.basename(MD_PATH))[0]}</title>
<style>
:root {{
    --bg: #1a1a2e;
    --bg-alt: #16213e;
    --text: #e0e0e0;
    --text-muted: #a0a0a0;
    --accent: #0f3460;
    --accent-light: #1a5276;
    --code-bg: #0d1117;
    --code-text: #c9d1d9;
    --border: #2a2a4a;
    --nav-bg: #0f1626;
    --table-stripe: #1e2a4a;
    --link: #58a6ff;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    padding-top: 60px;
}}
nav {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: var(--nav-bg);
    border-bottom: 1px solid var(--border);
    padding: 10px 20px;
    z-index: 1000;
    overflow-x: auto;
    white-space: nowrap;
    display: flex;
    gap: 4px;
    align-items: center;
}}
nav a {{
    color: var(--text-muted);
    text-decoration: none;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 0.85em;
    transition: all 0.2s;
}}
nav a:hover {{
    color: var(--text);
    background: var(--accent);
}}
.container {{
    max-width: 960px;
    margin: 0 auto;
    padding: 20px;
}}
h1 {{ color: #fff; margin: 30px 0 15px; font-size: 2em; border-bottom: 2px solid var(--accent); padding-bottom: 10px; }}
h2 {{ color: #fff; margin: 35px 0 15px; font-size: 1.5em; border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
h3 {{ color: var(--link); margin: 25px 0 10px; font-size: 1.2em; }}
h4 {{ color: var(--text); margin: 20px 0 8px; font-size: 1.05em; }}
p {{ margin: 10px 0; }}
a {{ color: var(--link); }}
code {{
    background: var(--code-bg);
    color: var(--code-text);
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.9em;
    font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace;
}}
pre {{
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 15px;
    overflow-x: auto;
    margin: 15px 0;
}}
pre code {{
    background: none;
    padding: 0;
    font-size: 0.85em;
    line-height: 1.5;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 0.9em;
}}
th {{
    background: var(--accent);
    color: #fff;
    padding: 10px 12px;
    text-align: left;
    border: 1px solid var(--border);
}}
td {{
    padding: 8px 12px;
    border: 1px solid var(--border);
}}
tr:nth-child(even) td {{ background: var(--table-stripe); }}
ul, ol {{ margin: 10px 0 10px 25px; }}
li {{ margin: 4px 0; }}
blockquote {{
    border-left: 4px solid var(--accent-light);
    padding: 10px 15px;
    margin: 15px 0;
    background: var(--bg-alt);
    border-radius: 0 6px 6px 0;
}}
hr {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 30px 0;
}}
strong {{ color: #fff; }}
@media (max-width: 768px) {{
    body {{ padding-top: 80px; }}
    nav {{ padding: 8px 10px; }}
    nav a {{ font-size: 0.75em; padding: 3px 6px; }}
    .container {{ padding: 10px; }}
    h1 {{ font-size: 1.5em; }}
    h2 {{ font-size: 1.2em; }}
    table {{ font-size: 0.8em; }}
}}
</style>
</head>
<body>
<nav>
{nav_html}
</nav>
<div class="container">
{body_html}
</div>
</body>
</html>'''

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"SUCCESS: {HTML_PATH}")
print(f"Size: {os.path.getsize(HTML_PATH)} bytes")
print(f"Sections (h2): {len([s for s in sections if s[0]==2])}")
print(f"Code blocks: {body_html.count('<pre>')}")
print(f"Tables: {body_html.count('<table>')}")
