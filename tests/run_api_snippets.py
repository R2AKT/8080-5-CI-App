# -*- coding: utf-8 -*-
"""Harness for interactive 'api' snippets in tests/.

These snippet files (ppi_test.py, kbd_test.py, font_test.py, etc.) are written
to run inside a live session where a global `api` (AutomationAPI) already
exists. This harness provides that `api` (MainWindow + 'full' profile) and
executes each snippet, reporting success/failure.

Run:  python tests/run_api_snippets.py
"""
import os
import sys
import traceback

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from PySide6.QtWidgets import QApplication  # noqa: E402
app = QApplication.instance() or QApplication([])

from i8080_ci.main_window import MainWindow  # noqa: E402
from i8080_ci.automation import AutomationAPI  # noqa: E402

# Snippet files that expect a global `api`
SNIPPETS = [
    "ppi_test.py",
    "kbd_test.py",
    "font_test.py",
    "display_test.py",
    "bitmap_crt_test.py",
    "discrete_crt_font_test.py",
    "crt_font_test.py",
    "device_access_test.py",
    "mmio_test.py",
    "uart_test.py",
    "test_invert_port_range.py",
    "PPI_3D_8x8x8_Flame.py",
    "PPI_3D_8x8x8_Girl.py",
    "PPI_3D_8x8x8_Heat.py",
    "PPI_3D_8x8x8_Pong.py",
    "PPI_3D_8x8x8_Rain.py",
    "PPI_3D_8x8x8_Tetris.py",
]

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def build_api():
    mw = MainWindow()
    mw.show()
    app.processEvents()
    # Load the 'full' profile which contains all devices
    try:
        mw.load_profile("full")
    except Exception as e:
        print(f"  [warn] load_profile('full'): {e}")
    app.processEvents()
    return AutomationAPI(mw)


def main():
    api = build_api()
    print(f"System devices: {sorted(api.system.devices.keys())}\n")

    passed, failed = [], []
    for name in SNIPPETS:
        path = os.path.join(TEST_DIR, name)
        if not os.path.exists(path):
            failed.append((name, "FILE NOT FOUND"))
            print(f"FAIL  {name}  (not found)")
            continue
        src = open(path, encoding='utf-8', errors='replace').read()
        ns = {'api': api, '__name__': '__snippet__'}
        try:
            exec(compile(src, name, 'exec'), ns)
            passed.append(name)
            print(f"PASS  {name}")
        except SystemExit as e:
            if e.code in (0, None):
                passed.append(name)
                print(f"PASS  {name}")
            else:
                failed.append((name, f"SystemExit({e.code})"))
                print(f"FAIL  {name}  SystemExit({e.code})")
        except Exception:
            tb = traceback.format_exc().strip().splitlines()
            failed.append((name, tb[-1]))
            print(f"FAIL  {name}  {tb[-1]}")

    print("\n" + "=" * 60)
    print(f"API SNIPPETS: {len(passed)} passed, {len(failed)} failed")
    print("=" * 60)
    if failed:
        for n, e in failed:
            print(f"  {n}: {e}")
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
