# -*- coding: utf-8 -*-
"""Full test cycle runner.

Runs:
  1. All standalone test files in tests/ (test_*.py, *_test.py, assembler_test*.py)
  2. The interactive 'api' snippets via run_api_snippets.py

Excludes the API snippet files from the standalone pass (they need the harness).

Run:  python _run_all_tests.py
"""
import subprocess
import sys
import os
import time
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['PYTHONPATH'] = ROOT

# Interactive snippets that require the `api` harness (run separately)
API_SNIPPETS = {
    "ppi_test.py", "kbd_test.py", "font_test.py", "display_test.py",
    "bitmap_crt_test.py", "discrete_crt_font_test.py", "crt_font_test.py",
    "device_access_test.py", "mmio_test.py", "uart_test.py",
    "test_invert_port_range.py",
    "PPI_3D_8x8x8_Flame.py", "PPI_3D_8x8x8_Girl.py", "PPI_3D_8x8x8_Heat.py",
    "PPI_3D_8x8x8_Pong.py", "PPI_3D_8x8x8_Rain.py", "PPI_3D_8x8x8_Tetris.py",
}
SELF = {"_run_all_tests.py", "run_api_snippets.py", "run_all.py", "_check_unused.py"}


def run_one(path, timeout=180):
    start = time.time()
    try:
        r = subprocess.run([sys.executable, "-B", path],
                           capture_output=True, text=True, timeout=timeout,
                           encoding='utf-8', errors='replace')
        dt = time.time() - start
        return r.returncode == 0, dt, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return False, time.time() - start, "TIMEOUT"
    except Exception as e:
        return False, time.time() - start, str(e)


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "tests", "*.py")))
    standalone = [f for f in files
                  if os.path.basename(f) not in API_SNIPPETS and os.path.basename(f) not in SELF]

    passed, failed = [], []
    print("=" * 64)
    print("ЧАСТЬ 1: Автономные тесты")
    print("=" * 64)
    for path in standalone:
        name = os.path.basename(path)
        ok, dt, out = run_one(path)
        if ok:
            passed.append(name)
            print(f"PASS  {name}  ({dt:.1f}s)")
        else:
            tail = "\n".join(out.splitlines()[-10:])
            failed.append((name, tail))
            print(f"FAIL  {name}  ({dt:.1f}s)")

    print("\n" + "=" * 64)
    print("ЧАСТЬ 2: Интерактивные api-сниппеты (harness)")
    print("=" * 64)
    ok, dt, out = run_one(os.path.join(ROOT, "tests", "run_api_snippets.py"), timeout=300)
    # Show only the summary line of the harness
    for line in out.splitlines():
        if "API SNIPPETS:" in line:
            print(line.strip())
    if ok:
        passed.append("run_api_snippets.py (17 snippets)")
    else:
        failed.append(("run_api_snippets.py", out[-800:]))

    print("\n" + "=" * 64)
    print(f"ИТОГО: {len(passed)} пройдено, {len(failed)} провалено")
    print("=" * 64)
    if failed:
        print("\nПРОВАЛЫ:")
        for n, e in failed:
            print(f"\n--- {n} ---")
            print(e)
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
