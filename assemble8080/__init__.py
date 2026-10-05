"""
assemble8080 — компактный макроассемблер i8080.
"""
from .assembler import (
    Assembler, assemble,
    AsmError, AsmResult,
    MNEMONICS, REGISTERS, REG_PAIRS,
    parse_number,
)
from .preprocessor import Preprocessor, PreprocessorError
from .numbers import NumberParser
from .mapfile import MapFile, MapEntry, generate_map, parse_map, load_map_file, save_map_file
from .objfile import ObjectFile, Relocation, save_obj, load_obj, obj_from_asm_result
from .linker import link, link_from_script, parse_link_script, LinkResult, LinkError

__all__ = [
    "Assembler", "assemble",
    "AsmError", "AsmResult",
    "MNEMONICS", "REGISTERS", "REG_PAIRS",
    "Preprocessor", "PreprocessorError",
    "NumberParser",
    "parse_number",
    "MapFile", "MapEntry", "generate_map", "parse_map",
    "load_map_file", "save_map_file",
    "ObjectFile", "Relocation", "save_obj", "load_obj", "obj_from_asm_result",
    "link", "link_from_script", "parse_link_script",
    "LinkResult", "LinkError",
]
