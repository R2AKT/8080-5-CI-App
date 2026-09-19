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

__all__ = [
    "Assembler", "assemble",
    "AsmError", "AsmResult",
    "MNEMONICS", "REGISTERS", "REG_PAIRS",
    "Preprocessor", "PreprocessorError",
    "NumberParser",
    "parse_number",
]
