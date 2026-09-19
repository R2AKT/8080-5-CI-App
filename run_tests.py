"""Run all unit tests as scripts and collect results."""
import sys
import subprocess
import os

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Set environment for subprocesses
env = os.environ.copy()
env['PYTHONPATH'] = os.getcwd()
env['PYTHONIOENCODING'] = 'utf-8'

# All test files that are standalone scripts (no 'api' dependency)
unit_tests = [
    'tests/test_alu_8080.py',
    'tests/test_emu_integration.py',
    'tests/test_am9511.py', 'tests/test_banked.py', 'tests/test_banked_rom.py',
    'tests/test_cf_ide.py', 'tests/test_ch376s.py', 'tests/test_ch376s_fs.py',
    'tests/test_displays.py', 'tests/test_dma.py', 'tests/test_dma_device.py',
    'tests/test_e1.py', 'tests/test_i16550.py', 'tests/test_i512vi1.py',
    'tests/test_i8251.py', 'tests/test_i8253.py', 'tests/test_i8255.py',
    'tests/test_i8257.py', 'tests/test_i8259.py', 'tests/test_i8272.py',
    'tests/test_i8272_image.py', 'tests/test_i8275.py', 'tests/test_i8276.py',
    'tests/test_i8279.py', 'tests/test_integration_full.py', 'tests/test_interrupts.py',
    'tests/test_memory_bus.py', 'tests/test_memory_models.py',
    'tests/test_port_invert.py', 'tests/test_shadow_rom.py',
    'tests/test_system_integration.py', 'tests/test_wait_cf_ide.py',
    'tests/test_wait_signals.py',
]

# Filter to existing files
unit_tests = [t for t in unit_tests if os.path.isfile(t)]
print(f"Running {len(unit_tests)} test scripts...\n")

total_passed = 0
total_failed = 0
total_errors = 0
results = []

for test_file in unit_tests:
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=60, env=env
        )
        output = result.stdout + result.stderr
        
        # Count ✅ and ❌
        passed = output.count('\u2705')
        failed = output.count('\u2726') + output.count('\u274c')
        
        # Check for exceptions
        has_error = 'Traceback' in output or 'Error' in output
        
        status = 'ERROR' if has_error else ('FAIL' if failed > 0 else 'OK')
        results.append((test_file, passed, failed, status))
        total_passed += passed
        total_failed += failed
        if has_error:
            total_errors += 1
        
        # Show non-OK results
        if status != 'OK':
            print(f"  {status}: {test_file} ({passed}✅ {failed}❌)")
            # Show last few lines of error
            lines = output.splitlines()
            for line in lines[-5:]:
                if line.strip():
                    print(f"         {line.strip()[:100]}")
            print()
    
    except subprocess.TimeoutExpired:
        results.append((test_file, 0, 0, 'TIMEOUT'))
        total_errors += 1
        print(f"  TIMEOUT: {test_file}")
    except Exception as e:
        results.append((test_file, 0, 0, f'EXC: {e}'))
        total_errors += 1
        print(f"  EXC: {test_file}: {e}")

# Summary
print("=" * 60)
print(f"SUMMARY: {len(unit_tests)} test files")
print(f"  Passed checks: {total_passed}")
print(f"  Failed checks: {total_failed}")
print(f"  Error files:   {total_errors}")
print(f"  OK files:      {sum(1 for r in results if r[3] == 'OK')}")
print("=" * 60)

# Show all results
print("\nAll results:")
for f, p, fl, s in results:
    icon = '✅' if s == 'OK' else '❌'
    print(f"  {icon} {f}: {p} passed, {fl} failed [{s}]")
