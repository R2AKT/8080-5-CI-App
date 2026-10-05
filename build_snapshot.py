#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_snapshot.py — Автоматическое создание среза проекта (PROJECT_SNAPSHOT.md).

Использование:
    python build_snapshot.py [project_root] [output_file]

Параметры:
    project_root  — корневой каталог проекта (по умолчанию: текущий)
    output_file   — имя выходного файла (по умолчанию: PROJECT_SNAPSHOT.md)

Скрипт обходит проект, классифицирует файлы по типу и генерирует
монолитный документ-срез со следующими разделами:
    1. Дерево проекта
    2. Описание модулей (AST-анализ)
    3. Полный код всех ключевых файлов
    4. Изменения рефакторинга (из CHANGES.md)
    5. Тесты
    6. Системные профили
    7. Главное окно и вкладки
    8. Итерации и планы
    9. Известные проблемы
    10. Приложения
"""

import ast
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ─── Конфигурация ─────────────────────────────────────────────────────────────

SKIP_DIRS = {
    '__pycache__', '.git', '.svn', '.hg', 'venv', '.venv',
    'node_modules', '.idea', '.vscode', 'dist', 'build',
    '.mypy_cache', '.pytest_cache', '.ruff_cache', '.tox',
}

SKIP_FILES = {
    'build_snapshot.py',
}

CODE_EXTS = {'.py'}
PROFILE_EXTS = {'.toml'}
DOC_EXTS = {'.md'}
HTML_EXTS = {'.html', '.htm'}
CONFIG_EXTS = {'.json', '.cfg', '.ini', '.yaml', '.yml', '.txt'}
ASSET_EXTS = {'.svg', '.png', '.ico', '.jpg', '.jpeg', '.gif',
              '.woff', '.woff2', '.ttf', '.rom', '.bin'}

TEST_NAME_PATTERNS = [
    re.compile(r'^test_.*\.py$'),
    re.compile(r'.*_test\.py$'),
    re.compile(r'^tests?/'),
]

# ─── Утилиты ──────────────────────────────────────────────────────────────────

def read_file_lines(path: Path) -> list[str]:
    """Прочитать файл, вернуть список строк."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.readlines()
    except Exception:
        return []


def read_file_text(path: Path) -> str:
    """Прочитать файл, вернуть текст."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return ''


def count_lines(path: Path) -> int:
    """Подсчитать строки в файле."""
    return len(read_file_lines(path))


def is_test_file(rel_path: str) -> bool:
    """Определить, является ли файл тестом."""
    return any(p.search(rel_path) for p in TEST_NAME_PATTERNS)


def find_doc_by_keyword(docs: list[tuple[Path, Path, int]], keyword: str) -> tuple[Path, Path, int] | None:
    """Найти документ по ключевому слову в имени (регистронезависимо)."""
    for rel, path, lc in docs:
        if keyword.lower() in rel.lower():
            return (rel, path, lc)
    return None


# ─── Обход проекта ────────────────────────────────────────────────────────────

def discover_files(root: Path) -> dict:
    """Обойти проект и классифицировать все файлы."""
    result = {
        'code': [],       # (rel_path, abs_path, line_count)
        'tests': [],
        'profiles': [],
        'docs': [],
        'html': [],
        'config': [],
        'assets': [],
        'other': [],
    }

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in sorted(dirnames) if d not in SKIP_DIRS]

        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            rel_path = fpath.relative_to(root)
            rel_str = str(rel_path).replace('\\', '/')
            ext = fpath.suffix.lower()

            if fname in SKIP_FILES:
                continue

            lc = count_lines(fpath)

            if ext in CODE_EXTS:
                if is_test_file(rel_str):
                    result['tests'].append((rel_str, fpath, lc))
                else:
                    result['code'].append((rel_str, fpath, lc))
            elif ext in PROFILE_EXTS:
                result['profiles'].append((rel_str, fpath, lc))
            elif ext in DOC_EXTS:
                result['docs'].append((rel_str, fpath, lc))
            elif ext in HTML_EXTS:
                result['html'].append((rel_str, fpath, lc))
            elif ext in CONFIG_EXTS:
                result['config'].append((rel_str, fpath, lc))
            elif ext in ASSET_EXTS:
                result['assets'].append((rel_str, fpath, lc))
            else:
                result['other'].append((rel_str, fpath, lc, ext))

    return result


# ─── Дерево проекта ───────────────────────────────────────────────────────────

def build_tree(root: Path) -> str:
    """Сгенерировать дерево проекта с количеством строк."""
    lines = []

    def walk(dir_path: Path, prefix: str = ''):
        entries = []
        for item in sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if item.name in SKIP_DIRS or item.name in SKIP_FILES:
                continue
            if item.is_dir():
                entries.append((item, True))
            else:
                entries.append((item, False))

        for i, (item, is_dir) in enumerate(entries):
            is_last = (i == len(entries) - 1)
            connector = '└── ' if is_last else '├── '

            if is_dir:
                lines.append(f"{prefix}{connector}{item.name}/")
                extension = '    ' if is_last else '│   '
                walk(item, prefix + extension)
            else:
                lc = count_lines(item)
                size_str = f"{lc} строк" if lc > 0 else ""
                lines.append(f"{prefix}{connector}{item.name}  [{size_str}]")

    walk(root)
    return '\n'.join(lines)


# ─── AST-анализ Python-файлов ─────────────────────────────────────────────────

def analyze_python_file(path: Path) -> dict:
    """Проанализировать Python-файл через AST."""
    info = {
        'docstring': '',
        'imports': [],
        'classes': [],
        'functions': [],
        'constants': [],
    }

    source = read_file_text(path)
    if not source:
        return info

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return info

    # Module docstring
    if tree.body and isinstance(tree.body[0], ast.Expr):
        node = tree.body[0].value
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            info['docstring'] = node.value.strip()

    for node in tree.body:
        # Imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info['imports'].append(alias.name)
            else:
                module = node.module or ''
                names = [a.name for a in node.names]
                info['imports'].append(f"from {module} import {', '.join(names)}")

        # Classes
        elif isinstance(node, ast.ClassDef):
            cls_info = {
                'name': node.name,
                'bases': [ast.unparse(b) for b in node.bases],
                'docstring': '',
                'methods': [],
                'attributes': [],
            }
            if node.body and isinstance(node.body[0], ast.Expr):
                dnode = node.body[0].value
                if isinstance(dnode, ast.Constant) and isinstance(dnode.value, str):
                    cls_info['docstring'] = dnode.value.strip()

            for item in node.body:
                if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                    args = [a.arg for a in item.args.args]
                    cls_info['methods'].append(f"{item.name}({', '.join(args)})")
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            cls_info['attributes'].append(target.id)

            info['classes'].append(cls_info)

        # Top-level functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            info['functions'].append(f"{node.name}({', '.join(args)})")

        # Top-level constants (simple assignments)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    info['constants'].append(target.id)

    return info


# ─── Описание модулей ─────────────────────────────────────────────────────────

def build_module_descriptions(code_files: list[tuple[str, Path, int]]) -> str:
    """Сгенерировать описание модулей на основе AST."""
    lines = []
    for rel, path, lc in code_files:
        lines.append(f"### `{rel}` ({lc} строк)")
        lines.append('')

        info = analyze_python_file(path)

        if info['docstring']:
            lines.append(f"> {info['docstring'].splitlines()[0]}")
            lines.append('')

        if info['imports']:
            lines.append(f"**Импорты ({len(info['imports'])}):**")
            for imp in info['imports'][:20]:
                lines.append(f"- `{imp}`")
            if len(info['imports']) > 20:
                lines.append(f"- ... и ещё {len(info['imports']) - 20}")
            lines.append('')

        if info['classes']:
            lines.append(f"**Классы ({len(info['classes'])}):**")
            for cls in info['classes']:
                bases = f"({', '.join(cls['bases'])})" if cls['bases'] else ''
                lines.append(f"- **{cls['name']}**{bases}")
                if cls['docstring']:
                    lines.append(f"  - {cls['docstring'].splitlines()[0]}")
                if cls['methods']:
                    lines.append(f"  - Методы ({len(cls['methods'])}): {', '.join(cls['methods'][:15])}")
                    if len(cls['methods']) > 15:
                        lines.append(f"    - ... и ещё {len(cls['methods']) - 15}")
                if cls['attributes']:
                    lines.append(f"  - Атрибуты: {', '.join(cls['attributes'][:10])}")
            lines.append('')

        if info['functions']:
            lines.append(f"**Функции ({len(info['functions'])}):**")
            for fn in info['functions'][:20]:
                lines.append(f"- `{fn}`")
            if len(info['functions']) > 20:
                lines.append(f"- ... и ещё {len(info['functions']) - 20}")
            lines.append('')

        if info['constants']:
            lines.append(f"**Константы:** {', '.join(info['constants'][:15])}")
            lines.append('')

        lines.append('---')
        lines.append('')

    return '\n'.join(lines)


# ─── Полный код файлов ────────────────────────────────────────────────────────

def build_code_section(files: list[tuple[str, Path, int]], section_label: str) -> str:
    """Сгенерировать раздел с полным кодом файлов."""
    lines = []
    for rel, path, lc in files:
        marker = f"<!-- FILE: {rel} -->"
        end_marker = f"<!-- END FILE: {rel} -->"
        lines.append(f"### `{rel}` ({lc} строк)")
        lines.append('')
        lines.append(marker)
        lines.append('```python' if path.suffix == '.py' else '```')
        content = read_file_text(path)
        lines.append(content.rstrip('\n'))
        lines.append('```')
        lines.append(end_marker)
        lines.append('')
    return '\n'.join(lines)


# ─── Главное окно и вкладки ───────────────────────────────────────────────────

def find_main_window(code_files: list[tuple[str, Path, int]]) -> tuple[str, Path, int] | None:
    """Найти файл с QMainWindow."""
    for rel, path, lc in code_files:
        source = read_file_text(path)
        if 'QMainWindow' in source and 'class' in source:
            return (rel, path, lc)
    return None


def extract_tabs_and_shortcuts(path: Path) -> dict:
    """Извлечь вкладки и горячие клавиши из main_window."""
    source = read_file_text(path)
    tabs = []
    shortcuts = []
    menus = []

    # Tabs: prefer create_tab_* method calls (they define the order)
    create_tab_calls = re.findall(r'self\.create_tab_(\w+)\(\)', source)
    if create_tab_calls:
        for name in create_tab_calls:
            tabs.append(f"create_tab_{name}()")
    else:
        # Fallback: addTab calls with meaningful arguments
        for m in re.finditer(r'addTab\((\w+),\s*["\']([^"\']*)["\']\)', source):
            label = m.group(2) or m.group(1)
            tabs.append(label)

    # Shortcuts: QShortcut with QKeySequence
    for m in re.finditer(r'QShortcut\(\s*QKeySequence\(\s*["\']([^"\']+)["\']', source):
        shortcuts.append(m.group(1))
    # Fallback: QShortcut without QKeySequence wrapper
    if not shortcuts:
        for m in re.finditer(r'QShortcut\(([^)]+)\)', source):
            shortcuts.append(m.group(1).strip())

    # Menus
    for m in re.finditer(r'addMenu\(([^)]+)\)', source):
        menus.append(m.group(1).strip())

    return {'tabs': tabs, 'shortcuts': shortcuts, 'menus': menus}


def build_main_window_section(code_files: list[tuple[str, Path, int]]) -> str:
    """Сгенерировать раздел о главном окне."""
    lines = []
    mw = find_main_window(code_files)

    if mw is None:
        lines.append("Файл с QMainWindow не найден.")
        return '\n'.join(lines)

    rel, path, lc = mw
    lines.append(f"Файл: `{rel}` ({lc} строк)")
    lines.append('')

    info = extract_tabs_and_shortcuts(path)

    if info['tabs']:
        lines.append(f"**Вкладки ({len(info['tabs'])}):**")
        for i, tab in enumerate(info['tabs']):
            lines.append(f"| {i} | `{tab}` |")
        lines.append('')

    if info['shortcuts']:
        lines.append(f"**Горячие клавиши ({len(info['shortcuts'])}):**")
        for sc in info['shortcuts']:
            lines.append(f"- `{sc}`")
        lines.append('')

    if info['menus']:
        lines.append(f"**Меню ({len(info['menus'])}):**")
        for menu in info['menus']:
            lines.append(f"- `{menu}`")
        lines.append('')

    # AST info
    ast_info = analyze_python_file(path)
    if ast_info['classes']:
        lines.append("**Классы:**")
        for cls in ast_info['classes']:
            bases = f"({', '.join(cls['bases'])})" if cls['bases'] else ''
            lines.append(f"- **{cls['name']}**{bases} — {len(cls['methods'])} методов")
        lines.append('')

    return '\n'.join(lines)


# ─── Изменения рефакторинга ───────────────────────────────────────────────────

def build_changes_section(docs: list[tuple[str, Path, int]]) -> str:
    """Найти и включить CHANGES.md."""
    doc = find_doc_by_keyword(docs, 'changes')
    if doc is None:
        return "Файл с изменениями не найден."

    rel, path, lc = doc
    lines = [f"Источник: `{rel}` ({lc} строк)", '']
    lines.append('```markdown')
    lines.append(read_file_text(path).rstrip('\n'))
    lines.append('```')
    return '\n'.join(lines)


# ─── Итерации и планы ─────────────────────────────────────────────────────────

def build_iterations_section(docs: list[tuple[str, Path, int]],
                             config_files: list[tuple[str, Path, int]]) -> str:
    """Найти документы с планами/итерациями."""
    lines = []
    # Look for docs with 'plan', 'iteration', 'roadmap', 'addendum' in name
    keywords = ['plan', 'iteration', 'roadmap', 'addendum', 'analysis']
    found = []
    all_files = docs + config_files
    for kw in keywords:
        for rel, path, lc in all_files:
            if kw.lower() in rel.lower():
                found.append((rel, path, lc))
                break

    if not found:
        lines.append("Документы с планами/итерациями не найдены.")
        return '\n'.join(lines)

    for rel, path, lc in found:
        lines.append(f"### `{rel}` ({lc} строк)")
        lines.append('')
        lines.append('```markdown')
        lines.append(read_file_text(path).rstrip('\n'))
        lines.append('```')
        lines.append('')

    return '\n'.join(lines)


# ─── Известные проблемы ───────────────────────────────────────────────────────

def build_issues_section(docs: list[tuple[str, Path, int]], code_files: list[tuple[str, Path, int]]) -> str:
    """Собрать известные проблемы из документации и кода."""
    lines = []

    # Look for issues in docs
    for kw in ['issue', 'bug', 'known', 'audit']:
        doc = find_doc_by_keyword(docs, kw)
        if doc:
            rel, path, lc = doc
            lines.append(f"### Источник: `{rel}`")
            lines.append('')
            lines.append('```markdown')
            lines.append(read_file_text(path).rstrip('\n'))
            lines.append('```')
            lines.append('')

    # Scan code for TODO/FIXME/HACK comments
    todo_items = []
    for rel, path, lc in code_files:
        source = read_file_text(path)
        for i, line in enumerate(source.splitlines(), 1):
            for marker in ['TODO', 'FIXME', 'HACK', 'XXX']:
                if marker in line:
                    todo_items.append(f"- `{rel}:{i}` — {line.strip()}")

    if todo_items:
        lines.append(f"### TODO/FIXME в коде ({len(todo_items)}):")
        lines.append('')
        for item in todo_items[:50]:
            lines.append(item)
        if len(todo_items) > 50:
            lines.append(f"- ... и ещё {len(todo_items) - 50}")
        lines.append('')

    if not lines:
        lines.append("Известные проблемы не обнаружены.")

    return '\n'.join(lines)


# ─── Приложения ───────────────────────────────────────────────────────────────

def build_appendices(code_files: list[tuple[str, Path, int]],
                     profiles: list[tuple[str, Path, int]],
                     config_files: list[tuple[str, Path, int]],
                     html_files: list[tuple[str, Path, int]],
                     asset_files: list[tuple[str, Path, int]],
                     other_files: list[tuple[str, Path, int, str]]) -> str:
    """Сгенерировать приложения."""
    lines = []

    # Extract PORT_COUNTS or similar dicts from code
    lines.append("### A. Таблицы констант из кода")
    lines.append('')
    found_consts = False
    for rel, path, lc in code_files:
        source = read_file_text(path)
        # Find dict assignments with uppercase names (module-level or class-level)
        for m in re.finditer(r'^\s*([A-Z_]{3,})\s*=\s*\{([^}]+)\}', source, re.MULTILINE):
            name = m.group(1)
            body = m.group(2).strip()
            if len(body) > 20:  # skip trivial dicts
                found_consts = True
                lines.append(f"**{name}** (из `{rel}`):")
                lines.append('```python')
                lines.append(f"{name} = {{{body}}}")
                lines.append('```')
                lines.append('')
    if not found_consts:
        lines.append("Таблицы констант не обнаружены.")
        lines.append('')

    # Profile summary
    lines.append("### B. Сводка профилей")
    lines.append('')
    lines.append("| Профиль | Строк |")
    lines.append("|---------|-------|")
    for rel, path, lc in profiles:
        lines.append(f"| `{rel}` | {lc} |")
    lines.append('')

    # Config files
    if config_files:
        lines.append("### C. Конфигурационные файлы")
        lines.append('')
        for rel, path, lc in config_files:
            lines.append(f"- `{rel}` ({lc} строк)")
        lines.append('')

    # HTML files
    if html_files:
        lines.append("### D. HTML-документы")
        lines.append('')
        for rel, path, lc in html_files:
            lines.append(f"- `{rel}` ({lc} строк)")
        lines.append('')

    # Asset files
    if asset_files:
        lines.append("### E. Ресурсы (изображения, шрифты, ROM)")
        lines.append('')
        for rel, path, lc in asset_files:
            lines.append(f"- `{rel}`")
        lines.append('')

    # Other files
    if other_files:
        lines.append("### F. Прочие файлы")
        lines.append('')
        for rel, path, lc, ext in other_files:
            lines.append(f"- `{rel}` ({ext}, {lc} строк)")
        lines.append('')

    return '\n'.join(lines)


# ─── Сборка документа ─────────────────────────────────────────────────────────

def build_snapshot(root: Path) -> str:
    """Собрать полный документ-срез."""
    files = discover_files(root)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    total_code = sum(lc for _, _, lc in files['code'])
    total_tests = sum(lc for _, _, lc in files['tests'])
    total_profiles = sum(lc for _, _, lc in files['profiles'])

    doc = []
    doc.append("# СРЕЗ ПРОЕКТА (PROJECT SNAPSHOT)")
    doc.append('')
    doc.append(f"> Сгенерировано: {now}")
    doc.append(f"> Корень проекта: `{root}`")
    doc.append(f"> Код: {len(files['code'])} файлов, {total_code} строк")
    doc.append(f"> Тесты: {len(files['tests'])} файлов, {total_tests} строк")
    doc.append(f"> Профили: {len(files['profiles'])} файлов, {total_profiles} строк")
    doc.append('')
    doc.append('---')
    doc.append('')

    # ── РАЗДЕЛ 1: Дерево проекта ──
    doc.append("■ РАЗДЕЛ 1: ДЕРЕВО ПРОЕКТА")
    doc.append('')
    doc.append('```')
    doc.append(build_tree(root))
    doc.append('```')
    doc.append('')
    doc.append('---')
    doc.append('')

    # ── РАЗДЕЛ 2: Описание модулей ──
    doc.append("■ РАЗДЕЛ 2: ОПИСАНИЕ МОДУЛЕЙ")
    doc.append('')
    doc.append(build_module_descriptions(files['code']))
    doc.append('---')
    doc.append('')

    # ── РАЗДЕЛ 3: Полный код ──
    doc.append("■ РАЗДЕЛ 3: ПОЛНЫЙ КОД КЛЮЧЕВЫХ ФАЙЛОВ")
    doc.append('')
    doc.append(build_code_section(files['code'], 'code'))
    doc.append('---')
    doc.append('')

    # ── РАЗДЕЛ 4: Изменения рефакторинга ──
    doc.append("■ РАЗДЕЛ 4: ИЗМЕНЕНИЯ РЕФАКТОРИНГА")
    doc.append('')
    doc.append(build_changes_section(files['docs']))
    doc.append('')
    doc.append('---')
    doc.append('')

    # ── РАЗДЕЛ 5: Тесты ──
    doc.append("■ РАЗДЕЛ 5: ТЕСТЫ")
    doc.append('')
    doc.append(f"Всего тестовых файлов: {len(files['tests'])}, строк: {total_tests}")
    doc.append('')
    doc.append(build_code_section(files['tests'], 'tests'))
    doc.append('---')
    doc.append('')

    # ── РАЗДЕЛ 6: Системные профили ──
    doc.append("■ РАЗДЕЛ 6: СИСТЕМНЫЕ ПРОФИЛИ")
    doc.append('')
    doc.append(f"Всего профилей: {len(files['profiles'])}")
    doc.append('')
    for rel, path, lc in files['profiles']:
        doc.append(f"### `{rel}` ({lc} строк)")
        doc.append('')
        doc.append(f"<!-- FILE: {rel} -->")
        doc.append('```toml')
        doc.append(read_file_text(path).rstrip('\n'))
        doc.append('```')
        doc.append(f"<!-- END FILE: {rel} -->")
        doc.append('')
    doc.append('---')
    doc.append('')

    # ── РАЗДЕЛ 7: Главное окно и вкладки ──
    doc.append("■ РАЗДЕЛ 7: ГЛАВНОЕ ОКНО И ВКЛАДКИ")
    doc.append('')
    doc.append(build_main_window_section(files['code']))
    doc.append('---')
    doc.append('')

    # ── РАЗДЕЛ 8: Итерации и планы ──
    doc.append("■ РАЗДЕЛ 8: ИТЕРАЦИИ И ПЛАНЫ")
    doc.append('')
    doc.append(build_iterations_section(files['docs'], files['config']))
    doc.append('---')
    doc.append('')

    # ── РАЗДЕЛ 9: Известные проблемы ──
    doc.append("■ РАЗДЕЛ 9: ИЗВЕСТНЫЕ ПРОБЛЕМЫ")
    doc.append('')
    doc.append(build_issues_section(files['docs'], files['code']))
    doc.append('---')
    doc.append('')

    # ── РАЗДЕЛ 10: Приложения ──
    doc.append("■ РАЗДЕЛ 10: ПРИЛОЖЕНИЯ")
    doc.append('')
    doc.append(build_appendices(
        files['code'], files['profiles'], files['config'],
        files['html'], files['assets'], files['other']
    ))
    doc.append('---')
    doc.append('')
    doc.append(f"*Конец среза. Сгенерировано {now}.*")

    return '\n'.join(doc)


# ─── Точка входа ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        root = Path(sys.argv[1]).resolve()
    else:
        root = Path.cwd()

    if len(sys.argv) > 2:
        output = Path(sys.argv[2])
    else:
        output = root / 'PROJECT_SNAPSHOT.md'

    if not root.is_dir():
        print(f"Ошибка: каталог не найден: {root}", file=sys.stderr)
        sys.exit(1)

    print(f"Обход проекта: {root}")
    print(f"Выходной файл: {output}")

    snapshot = build_snapshot(root)

    output.write_text(snapshot, encoding='utf-8')

    size = output.stat().st_size
    line_count = snapshot.count('\n') + 1
    print(f"Готово: {output}")
    print(f"  Размер: {size:,} байт ({size // 1024} КБ)")
    print(f"  Строк: {line_count:,}")


if __name__ == '__main__':
    main()
