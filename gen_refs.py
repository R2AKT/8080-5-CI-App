"""Generate reference files using real zasm compiler.

Naming convention:
  #target bin -> *.bin
  #target ram -> *.rom
  #target rom -> *.rom
"""
import subprocess
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ZASM = r'c:\zasm\zasm.exe'
TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ASM_FOR_TEST')
DATE = '2026-09-19,11:06:55'

# (source, expected target)
SOURCES = [
    ('8080TonePlayer.asm', 'bin'),
    ('bf.asm', 'bin'),
    ('CPU_test.asm', 'ram'),
    ('ESC_DeESC.asm', 'bin'),
    ('fifo_a16.asm', 'bin'),
    ('ImperialMarch.asm', 'bin'),
    ('IMSAI8080.asm', 'bin'),
    ('kernel.asm', 'rom'),
    ('main_boot.asm', 'rom'),
    ('Mega-80.asm', 'ram'),
    ('mon85-v13.asm', 'ram'),
    ('rtty.asm', 'bin'),
    ('shell.asm', 'rom'),
    ('Smyk_player.asm', 'rom'),
    ('SW_IO.asm', 'rom'),
]


def get_target(src_path):
    """Read #target from source file."""
    with open(src_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            s = line.strip()
            if s.startswith('#target'):
                parts = s.split()
                if len(parts) > 1:
                    return parts[1].lower()
    return 'bin'


def main():
    os.chdir(TEST_DIR)
    results = []
    for src, expected_target in SOURCES:
        src_path = os.path.join(TEST_DIR, src)
        if not os.path.exists(src_path):
            print(f'  MISSING: {src}')
            continue

        target = get_target(src_path)
        if target != expected_target:
            print(f'  WARNING: {src}: #target={target}, expected {expected_target}')

        # Output name: bin -> .bin, ram/rom -> .rom
        base = os.path.splitext(src)[0]
        ext = '.bin' if target == 'bin' else '.rom'
        out_name = base + ext

        # Remove old output if exists
        out_path = os.path.join(TEST_DIR, out_name)
        if os.path.exists(out_path):
            os.remove(out_path)

        # Run zasm
        cmd = [ZASM, '-l0', f'--date={DATE}', '-o', out_name, src]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        ok = r.returncode == 0 and 'no errors' in (r.stdout + r.stderr)
        size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        status = 'OK' if ok else 'FAIL'
        results.append((src, target, out_name, size, status))
        print(f'  {status}: {src} -> {out_name} ({size} bytes)')
        if not ok:
            print(f'    stdout: {r.stdout.strip()[:200]}')
            print(f'    stderr: {r.stderr.strip()[:200]}')

    print()
    print('Summary:')
    for src, target, out_name, size, status in results:
        print(f'  {status:4s}  {src:25s} target={target:4s} -> {out_name:25s} {size:6d} bytes')


if __name__ == '__main__':
    main()
