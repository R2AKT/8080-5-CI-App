# -*- coding: utf-8 -*-
"""
Общий модуль для сборки примеров ассемблера.

Добавляет корень проекта в sys.path и предоставляет удобные функции:
  - read(path) / write_bin(path, data)
  - assemble_file(path) -> AsmResult
  - report(result, label) -> bool
  - save_obj_file(result, path, source_name)
  - run_link(script_path) -> LinkResult
"""
import os
import sys

# Корень проекта (родитель каталога assembler_example)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from assemble8080.assembler import assemble
from assemble8080.objfile import obj_from_asm_result, save_obj, load_obj
from assemble8080.linker import link, link_from_script
from assemble8080.mapfile import generate_map, save_map_file


def read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_bin(path, data):
    with open(path, 'wb') as f:
        f.write(data)


def assemble_file(path):
    """Ассемблировать файл .asm, возвращает AsmResult."""
    src = read(path)
    return assemble(src, filename=path)


def report(result, label):
    """Вывести результат сборки. Возвращает True при успехе."""
    if result.success:
        print(f"  [OK]   {label}: {len(result.binary)} байт, "
              f"origin=0x{result.origin:04X}, символов: {len(result.symbols)}")
        for w in result.warnings:
            print(f"         (warn) {w}")
    else:
        print(f"  [FAIL] {label}:")
        for e in result.errors:
            print(f"         {e}")
    return result.success


def save_obj_file(result, path, source_name):
    """Создать и сохранить объектный файл из AsmResult."""
    obj = obj_from_asm_result(result, source_name=source_name)
    save_obj(path, obj)
    return obj


def save_map(result, path, source_name=""):
    """Сохранить map-файл из AsmResult (map_text генерируется автоматически)."""
    if result.map_text:
        save_map_file(path, result.map_text)
        return True
    # Fallback: сгенерировать вручную
    text = generate_map(result, source_name=source_name)
    save_map_file(path, text)
    return True


def run_link(script_path):
    """Слинковать по .lnk-скрипту. Возвращает LinkResult."""
    return link_from_script(script_path)


def hexdump(data, start=0, width=16):
    """Короткий hexdump для вывода в консоль."""
    lines = []
    for off in range(0, len(data), width):
        chunk = data[off:off + width]
        hexs = ' '.join(f'{b:02X}' for b in chunk)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {start + off:04X}: {hexs:<{width * 3}}  {asc}")
    return '\n'.join(lines)
