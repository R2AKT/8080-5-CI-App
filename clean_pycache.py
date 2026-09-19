#!/usr/bin/env python3
"""
clean_pycache.py — Удаление Python-кеша из дерева проекта.

Обходит все вложенные каталоги от точки запуска и удаляет:
  - каталоги __pycache__/
  - файлы *.pyc
  - файлы *.pyo

Использование:
    python clean_pycache.py [путь_корня]

Если путь не указан, используется текущий каталог.
"""

import os
import sys
import shutil
from pathlib import Path


def clean_pycache(root: Path, dry_run: bool = False) -> dict:
    """
    Обходит дерево от root и удаляет Python-кеш.

    Возвращает словарь со статистикой:
        dirs_removed: int
        files_removed: int
        total_bytes: int
    """
    stats = {"dirs_removed": 0, "files_removed": 0, "total_bytes": 0}

    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        # Удаляем файлы .pyc / .pyo
        for fname in filenames:
            if fname.endswith((".pyc", ".pyo")):
                fpath = Path(dirpath) / fname
                size = fpath.stat().st_size
                if not dry_run:
                    fpath.unlink()
                stats["files_removed"] += 1
                stats["total_bytes"] += size
                print(f"  🗑  файл: {fpath}")

        # Удаляем каталоги __pycache__
        for dname in dirnames:
            if dname == "__pycache__":
                dpath = Path(dirpath) / dname
                # Считаем размер каталога
                dir_size = sum(
                    f.stat().st_size for f in dpath.rglob("*") if f.is_file()
                )
                if not dry_run:
                    shutil.rmtree(dpath)
                stats["dirs_removed"] += 1
                stats["total_bytes"] += dir_size
                print(f"  🗑  каталог: {dpath}")

    return stats


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    # Аргументы (фильтруем флаги)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    root = Path(args[0]) if args else Path(".")

    if not root.is_dir():
        print(f"Ошибка: каталог не найден: {root}", file=sys.stderr)
        sys.exit(1)

    root = root.resolve()
    mode = " (dry-run)" if dry_run else ""
    print(f"🔍 Поиск Python-кеша в: {root}{mode}\n")

    stats = clean_pycache(root, dry_run=dry_run)

    print(f"\n{'=' * 50}")
    print(f"Каталогов __pycache__ удалено: {stats['dirs_removed']}")
    print(f"Файлов .pyc/.pyo удалено:      {stats['files_removed']}")
    print(f"Освобождено:                    {stats['total_bytes'] / 1024:.1f} КБ")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
