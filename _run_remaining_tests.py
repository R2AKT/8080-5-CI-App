"""Run all remaining test files not covered by run_tests.py."""
import sys, subprocess, os

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

env = os.environ.copy()
env['PYTHONPATH'] = os.getcwd()
env['PYTHONIOENCODING'] = 'utf-8'
env['QT_QPA_PLATFORM'] = 'offscreen'

covered = {
    'tests/test_alu_8080.py','tests/test_emu_integration.py','tests/test_am9511.py',
    'tests/test_banked.py','tests/test_banked_rom.py','tests/test_cf_ide.py',
    'tests/test_ch376s.py','tests/test_ch376s_fs.py','tests/test_displays.py',
    'tests/test_dma.py','tests/test_dma_device.py','tests/test_e1.py',
    'tests/test_i16550.py','tests/test_i512vi1.py','tests/test_i8251.py',
    'tests/test_i8253.py','tests/test_i8255.py','tests/test_i8257.py',
    'tests/test_i8259.py','tests/test_i8272.py','tests/test_i8272_image.py',
    'tests/test_i8275.py','tests/test_i8276.py','tests/test_i8279.py',
    'tests/test_integration_full.py','tests/test_interrupts.py',
    'tests/test_memory_bus.py','tests/test_memory_models.py',
    'tests/test_port_invert.py','tests/test_shadow_rom.py',
    'tests/test_system_integration.py','tests/test_wait_cf_ide.py',
    'tests/test_wait_signals.py','tests/test_8085.py',
}

all_tests = sorted(
    f for f in os.listdir('tests')
    if f.endswith('.py') and not f.startswith('__')
)

remaining = [f'tests/{f}' for f in all_tests if f'tests/{f}' not in covered]
print(f"Running {len(remaining)} remaining test scripts...\n")

total_p = total_f = total_err = 0
for tf in remaining:
    try:
        r = subprocess.run(
            [sys.executable, tf],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=120, env=env
        )
        out = r.stdout + r.stderr
        p = out.count('\u2705')
        fl = out.count('\u274c')
        has_err = 'Traceback' in out
        status = 'ERROR' if has_err else ('FAIL' if fl > 0 or r.returncode != 0 else 'OK')
        total_p += p; total_f += fl
        if has_err: total_err += 1
        line = f"  {status:5s} {tf}: {p} passed, {fl} failed"
        if status != 'OK':
            lines = [l for l in out.splitlines() if l.strip()][-4:]
            line += "\n" + "\n".join(f"         {l.strip()[:110]}" for l in lines)
        print(line)
    except subprocess.TimeoutExpired:
        total_err += 1
        print(f"  TIMEOUT {tf}")
    except Exception as e:
        total_err += 1
        print(f"  EXC {tf}: {e}")

print("=" * 60)
print(f"SUMMARY: {len(remaining)} files | passed={total_p} failed={total_f} errors={total_err}")
print("=" * 60)
