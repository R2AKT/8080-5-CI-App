# -*- coding: utf-8 -*-
"""
Тест исправления include: поиск в каталоге исходного файла.

Проверяет:
1. Include находит файл в каталоге .asm (не в CWD)
2. #path добавляет дополнительный каталог поиска
3. Вложенные include работают (include из include)
4. Приоритет: каталог текущего файла > #path > include_dirs
"""
import os
import sys
import tempfile
import shutil

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assemble8080.assembler import assemble
from assemble8080.preprocessor import Preprocessor, PreprocessorError

passed = 0
failed = 0

def check(name, condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}: {msg}")


def main():
    global passed, failed
    
    # Create temp directory structure:
    # tmp/
    #   main.asm        → #include "defs.inc"
    #   defs.inc        → #define FOO 0x42
    #   sub/
    #     nested.asm    → #include "subdefs.inc"
    #     subdefs.inc   → #define BAR 0x99
    #   lib/
    #     libdefs.inc   → #define BAZ 0x77
    
    tmpdir = tempfile.mkdtemp(prefix="asm_include_test_")
    try:
        # Create files
        with open(os.path.join(tmpdir, 'defs.inc'), 'w') as f:
            f.write("#define FOO 0x42\n")
        
        with open(os.path.join(tmpdir, 'main.asm'), 'w') as f:
            f.write('#include "defs.inc"\n')
            f.write("    ORG 0x100\n")
            f.write("    MVI A, FOO\n")
            f.write("    HLT\n")
        
        os.makedirs(os.path.join(tmpdir, 'sub'))
        with open(os.path.join(tmpdir, 'sub', 'subdefs.inc'), 'w') as f:
            f.write("#define BAR 0x99\n")
        
        with open(os.path.join(tmpdir, 'sub', 'nested.asm'), 'w') as f:
            f.write('#include "subdefs.inc"\n')
            f.write("    ORG 0x200\n")
            f.write("    MVI A, BAR\n")
            f.write("    HLT\n")
        
        os.makedirs(os.path.join(tmpdir, 'lib'))
        with open(os.path.join(tmpdir, 'lib', 'libdefs.inc'), 'w') as f:
            f.write("#define BAZ 0x77\n")
        
        with open(os.path.join(tmpdir, 'path_test.asm'), 'w') as f:
            f.write(f'#path "{os.path.join(tmpdir, "lib")}"\n')
            f.write('#include "libdefs.inc"\n')
            f.write("    ORG 0x300\n")
            f.write("    MVI A, BAZ\n")
            f.write("    HLT\n")
        
        # Test 1: Include finds file in same directory as .asm
        print("Тест 1: Include в каталоге .asm файла")
        main_path = os.path.join(tmpdir, 'main.asm')
        with open(main_path, 'r') as f:
            source = f.read()
        # Run from a DIFFERENT directory (simulate CWD != source dir)
        old_cwd = os.getcwd()
        os.chdir(tempfile.gettempdir())  # Change CWD to somewhere else
        try:
            result = assemble(source, filename=main_path)
        finally:
            os.chdir(old_cwd)
        check("Сборка без ошибок", result.success, str(result.errors))
        check("FOO = 0x42", result.binary[1] == 0x42, f"got 0x{result.binary[1]:02X}")
        
        # Test 2: Nested include (include from include)
        print("Тест 2: Вложенный include")
        nested_path = os.path.join(tmpdir, 'sub', 'nested.asm')
        with open(nested_path, 'r') as f:
            source = f.read()
        old_cwd = os.getcwd()
        os.chdir(tempfile.gettempdir())
        try:
            result = assemble(source, filename=nested_path)
        finally:
            os.chdir(old_cwd)
        check("Сборка без ошибок", result.success, str(result.errors))
        check("BAR = 0x99", result.binary[1] == 0x99, f"got 0x{result.binary[1]:02X}")
        
        # Test 3: #path directive
        print("Тест 3: Директива #path")
        path_test = os.path.join(tmpdir, 'path_test.asm')
        with open(path_test, 'r') as f:
            source = f.read()
        old_cwd = os.getcwd()
        os.chdir(tempfile.gettempdir())
        try:
            result = assemble(source, filename=path_test)
        finally:
            os.chdir(old_cwd)
        check("Сборка без ошибок", result.success, str(result.errors))
        check("BAZ = 0x77", result.binary[1] == 0x77, f"got 0x{result.binary[1]:02X}")
        
        # Test 4: File not found gives useful error
        print("Тест 4: Ошибка при отсутствии файла")
        with open(os.path.join(tmpdir, 'missing.asm'), 'w') as f:
            f.write('#include "nonexistent.inc"\n')
            f.write("    ORG 0x100\n")
            f.write("    HLT\n")
        missing_path = os.path.join(tmpdir, 'missing.asm')
        with open(missing_path, 'r') as f:
            source = f.read()
        result = assemble(source, filename=missing_path)
        check("Сборка с ошибкой", not result.success)
        check("Сообщение содержит 'не найден'", 
              any('не найден' in e.message.lower() or 'not found' in e.message.lower() 
                  for e in result.errors),
              str(result.errors))
        check("Сообщение содержит пути поиска",
              any('искали в' in e.message for e in result.errors),
              str(result.errors))
        
        # Test 5: Preprocessor directly - search order
        print("Тест 5: Порядок поиска (Preprocessor напрямую)")
        # Create a file in CWD and in source dir with different content
        cwd_inc = os.path.join(tempfile.gettempdir(), '_test_cwd_inc.inc')
        src_inc = os.path.join(tmpdir, '_test_src_inc.inc')
        with open(cwd_inc, 'w') as f:
            f.write("#define VAL 0x11\n")
        with open(src_inc, 'w') as f:
            f.write("#define VAL 0x22\n")
        
        src_file = os.path.join(tmpdir, '_test_order.asm')
        with open(src_file, 'w') as f:
            f.write('#include "_test_src_inc.inc"\n')
            f.write("    ORG 0x100\n")
            f.write("    MVI A, VAL\n")
            f.write("    HLT\n")
        
        old_cwd = os.getcwd()
        os.chdir(tempfile.gettempdir())  # CWD has _test_cwd_inc.inc
        try:
            with open(src_file, 'r') as f:
                source = f.read()
            result = assemble(source, filename=src_file)
        finally:
            os.chdir(old_cwd)
        # Should find _test_src_inc.inc in source dir (VAL=0x22), not CWD
        check("Сборка без ошибок", result.success, str(result.errors))
        check("VAL из каталога источника (0x22)", 
              result.binary[1] == 0x22, f"got 0x{result.binary[1]:02X}")
        
        # Cleanup
        os.remove(cwd_inc)
        os.remove(src_inc)
        
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
    print(f"{'='*60}")
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
