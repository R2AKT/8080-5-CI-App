# -*- coding: utf-8 -*-
"""
Интеграционный тест: ассемблирование всех файлов ASM_FOR_TEST.

Проверяет, что встроенный ассемблер (assemble8080) собирает все
8080-совместимые .asm/.mac файлы из каталога ASM_FOR_TEST без ошибок.

Файлы, не относящиеся к 8080 (Z80/8085/Apple II), исключены в EXCLUDE.

Запуск:  python tests/test_asm_for_test.py
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assemble8080.assembler import assemble  # noqa: E402

TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ASM_FOR_TEST')
TIMEOUT_SECS = 10

# Файлы, не для 8080 (Z80/8085/Apple II) — не тестируются
EXCLUDE = {
    'm33z.mac', 'm4rkt.mac', '4kbas.asm', 'tst8080.asm',
    '8080exer.asm',
    '8085exer.mac', 'tinybas85.asm', 'mon85-v12-ncb85.asm', 'mon85-v13.asm',
    'term85.asm', 'dop.asm', 'monnoice.asm', 'monrk.asm', 'monrk80.asm',
    'dd28.asm', 'dd29.asm',
    'basic disassembly-source.mac',
    'z_zappleasm.asm', 'z_zappleasm.original.asm',
    'axa.asm',
}


def main():
    if not os.path.isdir(TEST_DIR):
        print(f"❌ Каталог не найден: {TEST_DIR}")
        return 1

    files = sorted(
        f for f in os.listdir(TEST_DIR)
        if f.lower().endswith(('.asm', '.mac'))
    )

    results = []
    for name in files:
        if name.lower() in EXCLUDE:
            continue
        path = os.path.join(TEST_DIR, name)
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                source = f.read()
        except OSError as e:
            results.append((name, 'READ-ERR', 0, str(e)))
            continue

        t0 = time.time()
        try:
            res = assemble(source, filename=path)
            dt = time.time() - t0
        except Exception as e:
            dt = time.time() - t0
            results.append((name, 'EXC', 0, f"{type(e).__name__}: {e}"))
            continue

        if dt > TIMEOUT_SECS:
            results.append((name, 'TIMEOUT', int(dt * 1000), f"{dt:.1f}s"))
        elif res.errors:
            first = res.errors[0]
            msg = getattr(first, 'message', str(first))
            results.append((name, 'FAIL', len(res.binary), f"{len(res.errors)} err: {msg}"))
        else:
            results.append((name, 'PASS', len(res.binary), ''))

    # Отчёт
    print(f"Каталог: {TEST_DIR}")
    print(f"Файлов всего: {len(files)}, исключено: {len(files) - len(results)}\n")

    n_pass = sum(1 for r in results if r[1] == 'PASS')
    for name, status, size, msg in results:
        if status == 'PASS':
            print(f"  ✅ {name}: {size} байт")
        else:
            print(f"  ❌ {name}: {status} {msg}")

    print("\n" + "=" * 60)
    print(f"ИТОГО: {len(results)} файлов, PASS: {n_pass}, "
          f"FAIL: {len(results) - n_pass}")
    print("=" * 60)
    return 0 if n_pass == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
