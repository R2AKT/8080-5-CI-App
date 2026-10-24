# -*- coding: utf-8 -*-
"""
Тесты архиватора библиотек (librarian) и этапа разрешения зависимостей
линкера (автоматическое извлечение модулей из .lib).
"""
import os
import sys
import json
import tempfile
import shutil

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assemble8080.librarian import create_library, load_library, LIB_FORMAT_VERSION
from assemble8080.objfile import ObjectFile, Relocation, save_obj, load_obj
from assemble8080.linker import link_from_script

passed = 0
failed = 0


def check(name, condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  \u2705 {name}")
    else:
        failed += 1
        print(f"  \u274c {name}: {msg}")


def mkobj(path, name, org, data, symbols=None, exports=None, imports=None, relocs=None):
    """Собрать и сохранить ObjectFile во временный .obj."""
    obj = ObjectFile(
        name=name,
        source=name + ".asm",
        org=org,
        size=len(data) // 2,
        data=bytes.fromhex(data),
        symbols=symbols or {},
        exports=exports or [],
        imports=imports or [],
    )
    for r in (relocs or []):
        obj.relocations.append(Relocation(*r))
    save_obj(path, obj)
    return obj


def main():
    global passed, failed
    tmpdir = tempfile.mkdtemp(prefix="lib_link_test_")

    try:
        # === Тест 1: успешное создание библиотеки ===
        print("Тест 1: Создание библиотеки (.lib) библиотекарем")
        obj_mul = mkobj(
            os.path.join(tmpdir, "math_mul.obj"), "math_mul", 0x200,
            "00", symbols={"CCMULT": 0}, exports=["CCMULT"], imports=["CCSXT"])
        obj_div = mkobj(
            os.path.join(tmpdir, "math_div.obj"), "math_div", 0x300,
            "00", symbols={"CCDIV": 0}, exports=["CCDIV"])

        lib_path = os.path.join(tmpdir, "test_math.lib")
        create_library(
            [os.path.join(tmpdir, "math_mul.obj"),
             os.path.join(tmpdir, "math_div.obj")],
            lib_path, "test_math")
        check("Файл .lib создан", os.path.exists(lib_path))

        with open(lib_path, 'r', encoding='utf-8') as f:
            lib = json.load(f)
        check("Поле format == i8080-lib-v1", lib["format"] == LIB_FORMAT_VERSION, lib["format"])
        check("Имя библиотеки", lib["name"] == "test_math")
        check(
            "Индекс ровно {CCMULT, CCDIV}",
            lib["index"] == {"CCMULT": "math_mul", "CCDIV": "math_div"},
            str(lib["index"]))
        check("Модули: оба присутствуют", set(lib["modules"]) == {"math_mul", "math_div"})
        check("Модуль math_mul: полный JSON сохранён",
              lib["modules"]["math_mul"]["data"] == "00"
              and lib["modules"]["math_mul"]["exports"] == ["CCMULT"]
              and lib["modules"]["math_mul"]["imports"] == ["CCSXT"]
              and lib["modules"]["math_mul"]["symbols"] == {"CCMULT": 0})
        check("load_library: валидация формата", load_library(lib_path)["name"] == "test_math")

        # === Тест 2: дубликат экспорта -> ValueError ===
        print("Тест 2: Перехват дубликата символов библиотекарем")
        mkobj(os.path.join(tmpdir, "dup_a.obj"), "dup_a", 0x400,
              "00", symbols={"CCMULT": 0}, exports=["CCMULT"])
        mkobj(os.path.join(tmpdir, "dup_b.obj"), "dup_b", 0x500,
              "00", symbols={"CCMULT": 0}, exports=["CCMULT"])
        caught = False
        try:
            create_library(
                [os.path.join(tmpdir, "dup_a.obj"), os.path.join(tmpdir, "dup_b.obj")],
                os.path.join(tmpdir, "dup.lib"), "dup")
        except ValueError as e:
            caught = "Duplicate export symbol 'CCMULT'" in str(e)
        check("Дубликат экспорта заблокирован (Duplicate export symbol)", caught)
        check("Сборка заблокирована, .lib не создан",
              not os.path.exists(os.path.join(tmpdir, "dup.lib")))

        # === Тест 3: автоматическое извлечение нужного модуля из .lib ===
        print("Тест 3: Resolving — извлечение востребованного модуля из .lib")
        mkobj(os.path.join(tmpdir, "main.obj"), "main", 0x100,
              "CD0000", symbols={"MAIN": 0}, exports=["MAIN"], imports=["CCMULT"],
              relocs=[(1, 2, "CCMULT")])
        mkobj(os.path.join(tmpdir, "ccmul.obj"), "ccmul", 0x200,
              "80C9", symbols={"CCMULT": 0}, exports=["CCMULT"])
        mkobj(os.path.join(tmpdir, "ccdiv.obj"), "ccdiv", 0x300,
              "90C9", symbols={"CCDIV": 0}, exports=["CCDIV"])

        lib2 = os.path.join(tmpdir, "runtime.lib")
        create_library(
            [os.path.join(tmpdir, "ccmul.obj"), os.path.join(tmpdir, "ccdiv.obj")],
            lib2, "runtime")

        lnk = os.path.join(tmpdir, "project.lnk")
        with open(lnk, 'w', encoding='utf-8') as f:
            f.write("INPUT main.obj runtime.lib\nOUTPUT app.bin\nORIGIN 0x0100\n")

        result = link_from_script(lnk)
        check("Линковка завершилась успехом", result.success, str(result.errors))
        check("Итоговый бинарник содержит код main", result.binary[0x100] == 0xCD)
        check("CALL CCMULT пересчитан на адрес 0x0103 (ccmul сразу после main)",
              result.binary[0x100:0x103] == bytes([0xCD, 0x03, 0x01]),
              result.binary[0x100:0x103].hex())
        check("Код ccmul извлечён и наложен на 0x0103",
              result.binary[0x103:0x105] == bytes([0x80, 0xC9]),
              result.binary[0x103:0x105].hex())
        check("Символ CCMULT в глобальной таблице = 0x0103",
              result.symbols.get("CCMULT") == 0x103, str(result.symbols.get("CCMULT")))
        check("Неиспользуемый ccdiv ОТСУТСТВУЕТ (fill 0xFF на 0x0300)",
              result.binary[0x300:0x302] == bytes([0xFF, 0xFF]),
              result.binary[0x300:0x302].hex())
        check("app.bin записан на диск", os.path.exists(os.path.join(tmpdir, "app.bin")))

        # === Тест 4: паника линкера при отсутствии символа ===
        print("Тест 4: Undefined reference — символ не найден в библиотеке")
        mkobj(os.path.join(tmpdir, "main_u.obj"), "main_u", 0x100,
              "CD0000", symbols={"MAIN": 0}, exports=["MAIN"], imports=["UNKNOWN_SYM"],
              relocs=[(1, 2, "UNKNOWN_SYM")])
        lnk2 = os.path.join(tmpdir, "project_u.lnk")
        with open(lnk2, 'w', encoding='utf-8') as f:
            f.write("INPUT main_u.obj runtime.lib\nOUTPUT app_u.bin\nORIGIN 0x0100\n")
        caught = False
        try:
            link_from_script(lnk2)
        except ValueError as e:
            caught = "Undefined reference to symbol 'UNKNOWN_SYM'" in str(e)
        check("Символ не найден (Undefined reference to 'UNKNOWN_SYM')", caught)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Summary
    print(f"\n{'='*60}")
    print(f"РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
    print(f"{'='*60}")
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
