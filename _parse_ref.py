import re, sys
sys.stdout.reconfigure(encoding='utf-8')

html = open('_ref_page.html', encoding='utf-8').read()
tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
print(f'Found {len(tables)} tables')

for i, t in enumerate(tables):
    rows = re.findall(r'<tr.*?</tr>', t, re.DOTALL)
    print(f'Table {i}: {len(rows)} rows')
    # Extract cell text from each row
    for j, row in enumerate(rows):
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        print(f'  Row {j}: {clean}')
    open(f'_ref_table_{i}.txt', 'w', encoding='utf-8').write(t)
