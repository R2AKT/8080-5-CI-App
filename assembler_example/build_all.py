# -*- coding: utf-8 -*-
"""
Сборка всех примеров ассемблера.

Запускает build.py каждого примера по порядку и сводит итог.
Запуск:  python assembler_example/build_all.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = [
    '01_hello',
    '02_directives',
    '03_macros',
    '04_multifile',
]


def main():
    print("=" * 64)
    print(" Сборка всех примеров ассемблера")
    print("=" * 64)
    results = {}
    for ex in EXAMPLES:
        build = os.path.join(HERE, ex, 'build.py')
        print()
        r = subprocess.run([sys.executable, build], cwd=HERE)
        results[ex] = (r.returncode == 0)

    print()
    print("=" * 64)
    print(" ИТОГ")
    print("=" * 64)
    all_ok = True
    for ex in EXAMPLES:
        status = "OK  " if results[ex] else "FAIL"
        if not results[ex]:
            all_ok = False
        print(f"  [{status}] {ex}")
    print()
    if all_ok:
        print("  Все примеры собраны успешно.")
        return 0
    else:
        print("  Есть примеры с ошибками.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
