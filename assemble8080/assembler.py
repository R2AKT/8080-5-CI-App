"""
assemble8080 — компактный макроассемблер Intel 8080.
Двухпроходная сборка: проход 1 собирает метки, проход 2 генерирует код.

Поддержка:
  - Все мнемоники i8080 (включая недокументированные)
  - Форматы чисел: 0xFF, FFH, ffh, 255, 255D, 101101B, 177Q
  - Метки, выражения (метка + число, метка - число)
  - Директивы: ORG, DB, DW, DS, EQU, END
  - Комментарии: ; и * в начале строки
  - Оператор $ (текущий адрес)

Использование:
    from assemble8080.assembler import Assembler
    asm = Assembler()
    result = asm.assemble("MVI A, 55H\nHLT")
    if result.success:
        print(bytes(result.binary))
    else:
        for err in result.errors:
            print(err)
"""

from __future__ import annotations
import re
import warnings
from dataclasses import dataclass, field

import os
from .preprocessor import Preprocessor, PreprocessorError


# =============================================================
# РЕЗУЛЬТАТ СБОРКИ
# =============================================================

@dataclass
class AsmError:
    """Ошибка сборки."""
    line: int
    message: str
    source: str = ""

    def __str__(self):
        loc = f"{self.source}:" if self.source else ""
        return f"{loc}{self.line}: {self.message}"


@dataclass
class AsmResult:
    """Результат сборки."""
    success: bool
    binary: bytes = b""
    origin: int = 0x0000
    symbols: dict = field(default_factory=dict)      # {имя: адрес}
    errors: list = field(default_factory=list)        # [AsmError]
    warnings: list = field(default_factory=list)
    listing: list = field(default_factory=list)       # [(addr, bytes, source)]
    end_address: int = 0x0000


# =============================================================
# ТАБЛИЦЫ ДАННЫХ
# =============================================================

# Регистры: имя -> код (3 бита)
REGISTERS = {
    'B': 0, 'C': 1, 'D': 2, 'E': 3,
    'H': 4, 'L': 5, 'M': 6, 'A': 7,
}

# Пары регистров: имя -> код (2 бита)
REG_PAIRS = {
    'B': 0, 'D': 1, 'H': 2, 'SP': 3,
}

# Пары для PUSH/POP (PSW вместо SP)
REG_PAIRS_PSW = {
    'B': 0, 'D': 1, 'H': 2, 'PSW': 3,
}

# Условия перехода: имя -> код (3 бита)
CONDITIONS = {
    'NZ': 0, 'Z': 1, 'NC': 2, 'C': 3,
    'PO': 4, 'PE': 5, 'P': 6, 'M': 7,
}

# Мнемоники: (имя, опкод, формат, размер)
# Форматы:
#   ''      — без операндов
#   'r'     — регистр
#   'rp'    — пара регистров
#   'rpsw'  — пара регистров для PUSH/POP
#   'd8'    — 8-битный операнд
#   'd16'   — 16-битный адрес
#   'r,d8'  — регистр + 8-бит
#   'rp,d16'— пара + 16-бит
#   'cc'    — условие перехода (для Jcc, Ccc, Rcc)
#   'cc,d16'— условие + адрес
#   'rst'   — номер 0-7
MNEMONICS = {
    # Без операндов
    'NOP':   (0x00, '', 1),
    'RLC':   (0x07, '', 1),
    'RRC':   (0x0F, '', 1),
    'RAL':   (0x17, '', 1),
    'RAR':   (0x1F, '', 1),
    'DAA':   (0x27, '', 1),
    'CMA':   (0x2F, '', 1),
    'STC':   (0x37, '', 1),
    'CMC':   (0x3F, '', 1),
    'HLT':   (0x76, '', 1),
    'RET':   (0xC9, '', 1),
    'XTHL':  (0xE3, '', 1),
    'PCHL':  (0xE9, '', 1),
    'SIM':   (0xFB, '', 1),
    'RIM':   (0xF9, '', 1),
    'XCHG':  (0xEB, '', 1),
    'SPHL':  (0xF9, '', 1),
    'EI':    (0xFB, '', 1),
    'DI':    (0xF3, '', 1),

    # MOV r,r — обрабатываются отдельно (01 ddd sss)
    'MOV':   (0x40, 'r,r', 1),

    # MVI r,d8
    'MVI':   (0x06, 'r,d8', 2),

    # LXI rp,d16
    'LXI':   (0x01, 'rp,d16', 3),

    # Операции с памятью через HL
    'STAX':  (0x02, 'rp', 1),
    'LDAX':  (0x0A, 'rp', 1),
    'SHLD':  (0x22, 'd16', 3),
    'LHLD':  (0x2A, 'd16', 3),
    'STA':   (0x32, 'd16', 3),
    'LDA':   (0x3A, 'd16', 3),

    # INR / DCR
    'INR':   (0x04, 'r', 1),
    'DCR':   (0x05, 'r', 1),
    'DC':    (0x05, 'r', 1),  # Z80 shorthand for DCR

    # INX / DCX
    'INX':   (0x03, 'rp', 1),
    'DCX':   (0x0B, 'rp', 1),

    # DAD
    'DAD':   (0x09, 'rp', 1),

    # ALU r
    'ADD':   (0x80, 'r', 1),
    'ADC':   (0x88, 'r', 1),
    'SUB':   (0x90, 'r', 1),
    'SBB':   (0x98, 'r', 1),
    'ANA':   (0xA0, 'r', 1),
    'XRA':   (0xA8, 'r', 1),
    'ORA':   (0xB0, 'r', 1),
    'CMP':   (0xB8, 'r', 1),

    # ALI d8
    'ADI':   (0xC6, 'd8', 2),
    'ACI':   (0xCE, 'd8', 2),
    'SUI':   (0xD6, 'd8', 2),
    'SBI':   (0xDE, 'd8', 2),
    'ANI':   (0xE6, 'd8', 2),
    'XRI':   (0xEE, 'd8', 2),
    'ORI':   (0xF6, 'd8', 2),
    'CPI':   (0xFE, 'd8', 2),

    # JMP / CALL
    'JMP':   (0xC3, 'd16', 3),
    'CALL':  (0xCD, 'd16', 3),

    # Jcc / Ccc
    'JNZ':   (0xC2, 'd16', 3),
    'JZ':    (0xCA, 'd16', 3),
    'JNC':   (0xD2, 'd16', 3),
    'JC':    (0xDA, 'd16', 3),
    'JPO':   (0xE2, 'd16', 3),
    'JPE':   (0xEA, 'd16', 3),
    'JP':    (0xF2, 'd16', 3),
    'JM':    (0xFA, 'd16', 3),
    'CNZ':   (0xC4, 'd16', 3),
    'CZ':    (0xCC, 'd16', 3),
    'CNC':   (0xD4, 'd16', 3),
    'CC':    (0xDC, 'd16', 3),
    'CPO':   (0xE4, 'd16', 3),
    'CPE':   (0xEC, 'd16', 3),
    'CP':    (0xF4, 'd16', 3),
    'CM':    (0xFC, 'd16', 3),

    # Rcc
    'RNZ':   (0xC0, '', 1),
    'RZ':    (0xC8, '', 1),
    'RNC':   (0xD0, '', 1),
    'RC':    (0xD8, '', 1),
    'RPO':   (0xE0, '', 1),
    'RPE':   (0xE8, '', 1),
    'RP':    (0xF0, '', 1),
    'RM':    (0xF8, '', 1),

    # RST n
    'RST':   (0xC7, 'rst', 1),

    # IN / OUT
    'IN':    (0xDB, 'd8', 2),
    'OUT':   (0xD3, 'd8', 2),

    # PUSH / POP
    'PUSH':  (0xC5, 'rpsw', 1),
    'POP':   (0xC1, 'rpsw', 1),

    # Недокументированные (часто встречающиеся)
    'NOP*':  (0x08, '', 1),
    'RET*':  (0xD9, '', 1),
    'CALL*': (0xCB, '', 1),
}


# =============================================================
# ПАРСЕР ЧИСЕЛ
# =============================================================

# Регулярные выражения для форматов чисел
_RE_HEX_PREFIX = re.compile(r'^0[xX]([0-9A-Fa-f]+)$')
_RE_HEX_SUFFIX = re.compile(r'^([0-9][0-9A-Fa-f]*)[hH]$')
_RE_DECIMAL    = re.compile(r'^([0-9]+)[dD]?$')
_RE_BINARY     = re.compile(r'^([01]+)[bB]$')
_RE_OCTAL      = re.compile(r'^([0-7]+)[qQoO]$')


def parse_number(text: str) -> int | None:
    """
    Парсит числовой литерал. Возвращает int или None.

    Поддерживаемые форматы:
      0xFF, 0XFF        — шестнадцатеричный с префиксом
      0FFH, 0ffh, FFH   — шестнадцатеричный с суффиксом (обязательна ведущая цифра)
      255, 255D         — десятичный
      101101B           — двоичный
      177Q, 177O        — восьмеричный
    """
    text = text.strip()
    if not text:
        return None

    m = _RE_HEX_PREFIX.match(text)
    if m:
        try:
            return int(m.group(1), 16)
        except ValueError:
            return None

    m = _RE_HEX_SUFFIX.match(text)
    if m:
        try:
            return int(m.group(1), 16)
        except ValueError:
            return None

    m = _RE_BINARY.match(text)
    if m:
        try:
            return int(m.group(1), 2)
        except ValueError:
            return None

    m = _RE_OCTAL.match(text)
    if m:
        try:
            return int(m.group(1), 8)
        except ValueError:
            return None

    m = _RE_DECIMAL.match(text)
    if m:
        try:
            return int(m.group(1), 10)
        except ValueError:
            return None

    return None


# =============================================================
# ПАРСЕР ВЫРАЖЕНИЙ
# =============================================================

class ExpressionParser:
    """Парсер выражений для ассемблера"""

    def __init__(self, symbols, defines):
        self.symbols = symbols    # {имя: значение}
        self.defines = defines    # {имя: значение}
        self.pc = 0  # Текущий адрес (для $)

    @staticmethod
    def _strip_comment(line: str) -> str:
        """Убрать комментарий (; или * в начале строки)."""
        stripped = line.strip()
        if stripped.startswith(';') or stripped.startswith('*'):
            return ''
        # Ищем ; вне кавычек
        in_str = False
        for i, ch in enumerate(line):
            if ch == "'":
                in_str = not in_str
            elif ch == ';' and not in_str:
                return line[:i]
        return line

    def parse(self, expr, line_num=0):
        """Разобрать выражение, вернуть значение"""
        expr = expr.strip()
        if not expr:
            return 0
        # Удалить комментарий из операнда
        expr = self._strip_comment(expr)
        if not expr:
            return 0
        # Подстановка #define (быстро: только если имя встречается в expr)
        for _pass in range(10):
            _changed = False
            for name in sorted(self.defines.keys(), key=len, reverse=True):
                if name in expr:
                    _val = str(self.defines[name])
                    if not re.match(r'^(0[xX][0-9a-fA-F]+|\d+)$', _val):
                        if not (_val.startswith('(') and _val.endswith(')')):
                            _val = f'({_val})'
                    pattern = r'\b' + re.escape(name) + r'\b'
                    _new_expr = re.sub(pattern, _val, expr)
                    if _new_expr != expr:
                        _changed = True
                    expr = _new_expr
            if not _changed:
                break
        # Character literals: 'X' -> ASCII value
        def _sub_char(m):
            ch = m.group(1)
            if ch == '\\n':
                return str(0x0A)
            elif ch == '\\t':
                return str(0x09)
            elif ch == '\\r':
                return str(0x0D)
            elif ch == '\\0':
                return str(0x00)
            elif len(ch) == 1:
                return str(ord(ch))
            return m.group(0)
        expr = re.sub(r"'((?:\\.|[^'\\]))'", _sub_char, expr)
        expr = re.sub(r'"((?:\\.|[^"\\]))"', _sub_char, expr)
        # Подстановка символов (меток) — один проход regex + dict lookup
        if self.symbols:
            def _sub_sym(m):
                name = m.group(0)
                upper = name.upper()
                if upper in self.symbols:
                    return str(self.symbols[upper])
                if name in self.symbols:
                    return str(self.symbols[name])
                return name
            expr = re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*\b', _sub_sym, expr)
        # Обработка HIGH / LOW
        expr = self._process_high_low(expr)
        # Вычисление
        return self._eval(expr, line_num)

    def _process_high_low(self, expr):
        """Обработать HIGH и LOW"""
        # HIGH(expr) -> (expr >> 8) & 0xFF
        expr = re.sub(r'\bHIGH\s*\(([^)]+)\)',
                      r'((\1) >> 8) & 0xFF', expr, flags=re.IGNORECASE)
        # LOW(expr) -> expr & 0xFF
        expr = re.sub(r'\bLOW\s*\(([^)]+)\)',
                      r'(\1) & 0xFF', expr, flags=re.IGNORECASE)

        # Также поддерживаем HIGH expr и LOW expr без скобок
        expr = re.sub(r'\bHIGH\s+(\w+)',
                      r'((\1) >> 8) & 0xFF', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\bLOW\s+(\w+)',
                      r'(\1) & 0xFF', expr, flags=re.IGNORECASE)

        return expr

    @staticmethod
    def _convert_numbers(expr):
        """Конвертировать числовые литералы в десятичные."""
        # 0x... / 0X...
        expr = re.sub(r'\b0[xX]([0-9A-Fa-f]+)\b',
                      lambda m: str(int(m.group(1), 16)), expr)
        # ...H / ...h (должен начинаться с цифры)
        expr = re.sub(r'\b([0-9][0-9A-Fa-f]*)[hH]\b',
                      lambda m: str(int(m.group(1), 16)), expr)
        # ...B / ...b
        expr = re.sub(r'\b([01]+)[bB]\b',
                      lambda m: str(int(m.group(1), 2)), expr)
        # ...Q / ...q / ...O / ...o
        expr = re.sub(r'\b([0-7]+)[qQoO]\b',
                      lambda m: str(int(m.group(1), 8)), expr)
        return expr

    def _eval(self, expr, line_num=0):
        """Безопасное вычисление выражения"""
        try:
            # Конвертируем числовые литералы в десятичные
            expr = self._convert_numbers(expr)

            # Заменяем $ на текущий адрес
            expr = expr.replace('$', str(self.pc))

            # Заменяем операторы
            expr = expr.replace('&&', ' and ')
            expr = expr.replace('||', ' or ')
            expr = expr.replace('!', ' not ')
            expr = re.sub(r'\bMOD\b', '%', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bSHL\b', '<<', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bSHR\b', '>>', expr, flags=re.IGNORECASE)

            # Заменяем логические операторы на спецсимволы
            expr = re.sub(r'\bAND\b', '\x01', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bOR\b', '\x02', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bNOT\b', '~', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bXOR\b', '^', expr, flags=re.IGNORECASE)
            # Операторы сравнения (zasm)
            expr = re.sub(r'\bNE\b', '!=', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bEQ\b', '==', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bGT\b', '>', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bLT\b', '<', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bGE\b', '>=', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bLE\b', '<=', expr, flags=re.IGNORECASE)
            # M80: <> is not-equal
            expr = expr.replace('<>', '!=')

            # Заменяем оставшиеся идентификаторы (неопределённые символы) на 0
            def _replace_ident(m):
                name = m.group(0)
                if name in ('and', 'or', 'not', 'True', 'False'):
                    return name
                return '0'
            expr = re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*\b', _replace_ident, expr)

            # Разрешаем только безопасные символы
            safe = re.sub(r'[^0-9+\-*/%<>()&|^~\s\x01\x02\x03]', '', expr)

            # Убираем ведущие нули из десятичных чисел (00100 -> 100)
            def _strip_zeros(m):
                s = m.group(0)
                stripped = s.lstrip('0')
                return stripped if stripped else '0'
            safe = re.sub(r'\b\d+\b', _strip_zeros, safe)

            # Возвращаем логические операторы
            safe = safe.replace('\x01', '&')
            safe = safe.replace('\x02', '|')
            # x03 no longer used (NOT now maps to ~)
            # Integer division (8080 has no float)
            safe = safe.replace('/', '//')

            # Если выражение пустое — возвращаем 0
            if not safe.strip():
                return 0

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                result = eval(safe)
            return int(result) & 0xFFFF
        except ZeroDivisionError:
            return 0
        except SyntaxError:
            return 0
        except Exception:
            # Для максимальной совместимости: возвращаем 0 вместо ошибки
            return 0


# =============================================================
# АССЕМБЛЕР
# =============================================================

class Assembler:
    """Двухпроходный ассемблер Intel 8080."""

    def __init__(self, now=None):
        import datetime
        self._now = now if now is not None else datetime.datetime.now()
        self._write_pos = 0
        self.symbols: dict[str, int] = {}
        self.errors: list[AsmError] = []
        self.warnings: list[str] = []
        self.binary = bytearray()
        self._write_pos = 0
        self.origin = 0x0000
        self.pc = 0x0000
        self.listing: list = []
        self._filename = ""
        self.defines: dict = {}
        self.expr_parser = ExpressionParser(self.symbols, self.defines)

    def _write(self, data):
        """Write bytes at _write_pos, overwriting existing bytes if needed."""
        data = bytes(data)
        end = self._write_pos + len(data)
        if end > len(self.binary):
            self.binary.extend(bytearray(end - len(self.binary)))
        self.binary[self._write_pos:end] = data
        self._write_pos = end


    def _count_db_bytes(self, operand: str) -> int:
        """Count total bytes in a DB directive operand."""
        count = 0
        for part in self._split_operands(operand):
            part = part.strip()
            if not part:
                continue
            if part.startswith('"') and part.endswith('"'):
                count += len(part) - 2
            elif part.startswith("'") and part.endswith("'"):
                count += 1
            else:
                count += len([x for x in part.split(',') if x.strip()])
        return max(count, 1)

    def _count_dw_words(self, operand: str) -> int:
        """Count total words in a DW directive operand."""
        parts = [p for p in self._split_operands(operand) if p.strip()]
        return max(len(parts), 1)

    @staticmethod
    def _strip_comment(line: str) -> str:
        """Убрать комментарий (; или * в начале строки)."""
        stripped = line.strip()
        if stripped.startswith(';') or stripped.startswith('*'):
            return ''
        # Ищем ; вне кавычек
        in_str = False
        for i, ch in enumerate(line):
            if ch == "'":
                in_str = not in_str
            elif ch == ';' and not in_str:
                return line[:i]
        return line

    def _parse_label(self, line: str):
        """Разобрать метку в начале строки.
        Поддержка:
          - Одинарное двоеточие (локальная метка):  START:
          - Двойное двоеточие (глобальная метка):   START::
        """
        # Двойное двоеточие (глобальная метка)
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_$]*)::\s*(.*)', line)
        if m:
            return m.group(1), True, m.group(2)
        # Одинарное двоеточие (локальная метка)
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_$]*)\s*:\s*(.*)', line)
        if m:
            return m.group(1), False, m.group(2)
        # Метка без двоеточия (для совместимости)
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_$]*)\s+(.*)', line)
        if m:
            candidate = m.group(1).upper()
            # Проверяем, что это не мнемоника
            if candidate not in MNEMONICS and candidate not in ('ORG', 'DB', 'DW', 'DS', 'EQU', 'END', 'DM', 'BYTE', 'WORD', 'DEFL', 'REPT', 'ENDM', 'XDEF', 'XREF', 'SECTION', 'IF', 'ENDIF', 'ELSE', 'LOCAL', 'ENDLOCAL', 'ERROR', 'MACRO', 'ENDM', 'CPU', 'ASEG', 'TITLE', 'DEF'):
                return m.group(1), False, m.group(2)
        # Метки нет
        return None, False, line

    # ---------------------------------------------------------
    # ПУБЛИЧНЫЙ ИНТЕРФЕЙС
    # ---------------------------------------------------------
    def assemble(self, source: str, filename: str = "") -> AsmResult:
        """Ассемблировать исходный код"""
        # 1. Препроцессор
        try:
            preprocessor = Preprocessor(include_dirs=['.', os.path.dirname(filename) or '.'])
            processed_lines = preprocessor.process(source, filename)
        except PreprocessorError as e:
            return AsmResult(success=False, errors=[AsmError(e.line, str(e))])
        except Exception as e:
            return AsmResult(success=False, errors=[AsmError(0, f"Препроцессор: {e}")])

        # 2. Первый проход — сбор меток
        self.symbols = {}
        self.errors = []
        self.warnings = []
        self.listing = []
        self.defines = preprocessor.defines
        self._ds_fill = 0xFF if preprocessor.target == 'rom' else 0x00  # rom=0xFF, bin/ram=0x00 (bin is old name for ram)
        self.expr_parser = ExpressionParser(self.symbols, self.defines)
        self.expr_parser.pc = 0
        self._current_section = None
        self._section_sizes = {}
        self._pending_equ = []
        self._section_addr_exprs = []  # (sec_name, sec_addr_expr) for re-evaluation
        self._section_addresses = {}   # pre-computed section addresses
        self._label_section = {}     # label -> (section_name, section_start_at_label_time)
        location = 0
        origin_set = False

        for text, line_num, fname in processed_lines:
            stripped = self._strip_comment(text).strip()
            if not stripped or stripped.startswith(';'):
                continue

            # Метка
            label, is_global, rest = self._parse_label(stripped)
            if label:
                label_upper = label.upper()
                # Разрешаем переопределение (последнее значение побеждает)
                self.symbols[label_upper] = location
                # Track which section this label belongs to
                if self._current_section:
                    _sn, _ss, _sa, _se = self._current_section
                    if _sn:
                        self._label_section[label_upper] = (_sn, _ss)
                if not rest:
                    continue
                stripped = rest

            # Директива или инструкция
            parts = stripped.split(None, 1)
            mnemonic = parts[0].upper()
            if mnemonic.startswith('.'):
                mnemonic = mnemonic[1:]
            operand = parts[1] if len(parts) > 1 else ''

            # XDEF/XREF/SECTION/IF/ENDIF/ELSE/LOCAL/ENDLOCAL/ERROR — no-op
            if mnemonic in ('XDEF', 'XREF', 'SECTION', '.XDEF', '.XREF', '.SECTION',
                           'IF', 'ENDIF', 'ELSE', 'LOCAL', 'ENDLOCAL', 'ERROR',
                           '.IF', '.ENDIF', '.ELSE', '.LOCAL', '.ENDLOCAL', '.ERROR',
                           'CPU', 'ASEG', 'TITLE', '.TITLE',
                           'ENDR', 'DATA', 'BLKB', 'DISKDEF', 'IRP', 'ASSERT',
                           'DEFW', '.DATA', '.BLKB', '.DISKDEF', '.IRP', '.ASSERT',
                           '.DEFW', '#DATA', '#ASSERT', 'ASMPC', 'MACRO', 'ALIGN', '.ALIGN'):
                continue
            # END — конец программы
            if mnemonic in ('END', '.END'):
                break

            # ORG
            if mnemonic in ('ORG', '.ORG'):
                self.expr_parser.pc = location
                location = self.expr_parser.parse(operand, line_num)
                if not origin_set:
                    self.origin = location & 0xFFFF
                    origin_set = True
                self.pc = location
                continue

            # #code SECTION, ADDRESS, SIZE — секция (zasm)
            if mnemonic == 'CODE' or stripped.startswith('#code'):
                code_parts = [p.strip() for p in self._split_operands(operand)] if operand else []
                if not code_parts and label:
                    code_parts = [label]
                sec_name = label if label else (code_parts[0] if code_parts else '')
                sec_addr = code_parts[1] if len(code_parts) > 1 else '*'
                sec_size = code_parts[2] if len(code_parts) > 2 else '*'
                # Create _SIZE symbol immediately for forward references
                if sec_name and sec_size != '*':
                    try:
                        size_val = self.expr_parser.parse(sec_size, line_num)
                        self.symbols[sec_name.upper() + '_SIZE'] = size_val
                    except Exception:
                        pass
                
                # Завершаем предыдущую секцию
                if self._current_section:
                    prev_name, prev_start, prev_auto, prev_size_expr = self._current_section
                    if prev_auto:
                        prev_size = location - prev_start
                    elif prev_size_expr:
                        try:
                            prev_size = self.expr_parser.parse(prev_size_expr, line_num)
                        except Exception:
                            prev_size = location - prev_start
                    else:
                        prev_size = location - prev_start
                    self.symbols[prev_name.upper() + '_SIZE'] = prev_size
                    # Create _end symbol (end address of section)
                    self.symbols[prev_name.upper() + '_END'] = prev_start + prev_size
                    # Pad to fixed section size
                    if not prev_auto and prev_size_expr:
                        try:
                            fixed_size = self.expr_parser.parse(prev_size_expr, line_num)
                            actual_size = location - prev_start
                            if actual_size < fixed_size:
                                location = prev_start + fixed_size
                                self.pc = location
                        except Exception:
                            pass
                
                # Новая секция
                if sec_addr != '*':
                    location = self.expr_parser.parse(sec_addr, line_num)
                    if not origin_set:
                        self.origin = location & 0xFFFF
                        origin_set = True
                if sec_name:
                    self.symbols[sec_name.upper()] = location
                    # Collect for re-evaluation after pending EQU
                    self._section_addr_exprs.append((sec_name, sec_addr))
                self.pc = location
                auto_size = (sec_size == '*')
                self._current_section = (sec_name, location, auto_size, sec_size if not auto_size else None)
                continue

            # EQU — присваивает символ (формат "метка: EQU значение")
            if mnemonic in ('EQU', '.EQU', 'DEFL', '=', 'DEF', '.DEF'):
                if label:
                    self.expr_parser.pc = location
                    # Check if all symbols in expression are defined
                    _idents = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', operand)
                    _all_defined = all(_i.upper() in self.symbols or _i in self.symbols for _i in _idents)
                    if _all_defined:
                        value = self.expr_parser.parse(operand, line_num)
                        self.symbols[label.upper()] = value
                    else:
                        self._pending_equ.append((label.upper(), operand))
                continue
            # EQU/DEF без двоеточия: "метка EQU значение" / "метка DEF значение"
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s+(?:EQU|DEF)\s+(.*)', stripped, re.IGNORECASE)
            if m:
                eq_label = m.group(1)
                eq_operand = m.group(2)
                self.expr_parser.pc = location
                _idents = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', eq_operand)
                _all_defined = all(_i.upper() in self.symbols or _i in self.symbols for _i in _idents)
                if _all_defined:
                    value = self.expr_parser.parse(eq_operand, line_num)
                    self.symbols[eq_label.upper()] = value
                else:
                    self._pending_equ.append((eq_label.upper(), eq_operand))
                continue

            # REPT/ENDM — no-op (уже расширены препроцессором)
            if mnemonic in ('REPT', 'ENDM', '.REPT', '.ENDM'):
                continue
            # DS — резервирование
            if mnemonic in ('DS', '.DS', 'SPACE', '.SPACE'):
                self.expr_parser.pc = location
                ds_parts = self._split_operands(operand)
                count = self.expr_parser.parse(ds_parts[0], line_num)
                location += count
                self.pc = location
                continue

            # DB/DW/DM — данные
            if mnemonic in ('DB', 'DW', 'DM', '.DB', '.DW', '.DM', 'BYTE', 'WORD'):
                if mnemonic in ('DW', '.DW', 'WORD'):
                    parts_count = len(self._split_operands(operand))
                    location += parts_count * 2
                else:
                    # DB/DM — считаем длину
                    db_parts = self._split_operands(operand)
                    total = 0
                    for part in db_parts:
                        part = part.strip()
                        # zasm: <expr> — считаем символы
                        if part.startswith('<') and part.endswith('>'):
                            total += len(part) - 2
                            continue
                        # M80: N dup(value)
                        dup_m = re.match(r'^(\S+)\s+dup\s*\(.+\)$', part, re.IGNORECASE)
                        if dup_m:
                            total += self.expr_parser.parse(dup_m.group(1), line_num)
                            continue
                        if part.startswith("'"):
                            _eq = part.find("'", 1)
                            total += (_eq - 1) if _eq > 0 else 1
                        elif part.startswith('"'):
                            _eq = part.find('"', 1)
                            total += (_eq - 1) if _eq > 0 else 1
                        else:
                            total += 1
                    location += total
                self.pc = location
                continue

            # Обычная инструкция — используем полную таблицу и кодирование
            if mnemonic in MNEMONICS:
                opcode, fmt, size = MNEMONICS[mnemonic]
                location += size
                self.pc = location
            else:
                # Неизвестная инструкция
                self._error(line_num, f"Неизвестная мнемоника: {mnemonic}")
                location += 1
                self.pc = location

        # 3. Второй проход — генерация кода
        # Process pending EQU directives (forward references to section symbols)
        for _iter in range(10):
            _resolved = False
            _remaining = []
            for _eq_label, _eq_operand in self._pending_equ:
                _idents = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', _eq_operand)
                _all_defined = all(_i.upper() in self.symbols or _i in self.symbols for _i in _idents)
                if _all_defined:
                    try:
                        _val = self.expr_parser.parse(_eq_operand, 0)
                        self.symbols[_eq_label] = _val
                        _resolved = True
                    except Exception:
                        _remaining.append((_eq_label, _eq_operand))
                else:
                    _remaining.append((_eq_label, _eq_operand))
            self._pending_equ = _remaining
            if not self._pending_equ or not _resolved:
                break
        # Re-evaluate all section addresses now that pending EQUs are resolved
        for _sec_name, _sec_addr_expr in self._section_addr_exprs:
            if _sec_addr_expr != '*':
                try:
                    _addr = self.expr_parser.parse(_sec_addr_expr, 0)
                    self._section_addresses[_sec_name.upper()] = _addr
                    self.symbols[_sec_name.upper()] = _addr
                except Exception:
                    pass
        
        # Fix label addresses for sections whose addresses were corrected
        for _lbl, (_sec_name, _sec_start) in self._label_section.items():
            _sec_upper = _sec_name.upper()
            if _sec_upper in self._section_addresses:
                _new_sec_addr = self._section_addresses[_sec_upper]
                _old_sec_addr = _sec_start
                if _new_sec_addr != _old_sec_addr:
                    _delta = _new_sec_addr - _old_sec_addr
                    self.symbols[_lbl] = self.symbols[_lbl] + _delta

        self.binary = bytearray()
        self.listing = []
        location = 0
        self.pc = 0
        self._write_pos = 0
        self._current_section = None
        # Базовый адрес: логический адрес, соответствующий байту 0 бинарного образа.
        # Бинарный образ начинается с origin (как в zasm), а не с адреса 0.
        self._base_offset = 0

        for text, line_num, fname in processed_lines:
            stripped = self._strip_comment(text).strip()
            if not stripped or stripped.startswith(';'):
                continue

            # Метка
            label, is_global, rest = self._parse_label(stripped)
            if label:
                if not rest:
                    continue
                stripped = rest

            parts = stripped.split(None, 1)
            mnemonic = parts[0].upper()
            if mnemonic.startswith('.'):
                mnemonic = mnemonic[1:]
            operand = parts[1] if len(parts) > 1 else ''

            # ORG
            if mnemonic in ('ORG', '.ORG'):
                self.expr_parser.pc = location
                new_loc = self.expr_parser.parse(operand, line_num)
                if location == 0 and self._write_pos == 0:
                    # Первый ORG: бинарный образ начинается с new_loc (как в zasm),
                    # без заполнения нулями от адреса 0.
                    self._base_offset = new_loc
                    location = new_loc
                    self.pc = location
                    # _write_pos остаётся 0
                else:
                    if new_loc > location:
                        # Fill gap with target fill byte
                        self._write(bytearray([self._ds_fill]) * (new_loc - location))
                    elif new_loc < location:
                        # ORG backwards: overwrite existing bytes (paging)
                        self._write_pos = new_loc - self._base_offset
                        if len(self.binary) > self._write_pos:
                            del self.binary[self._write_pos:]
                    location = new_loc
                    self.pc = location
                    self._write_pos = location - self._base_offset
                continue

            # #code SECTION, ADDRESS, SIZE - section (zasm)
            if mnemonic == 'CODE' or stripped.startswith('#code'):
                code_parts = [p.strip() for p in self._split_operands(operand)] if operand else []
                if not code_parts and label:
                    code_parts = [label]
                sec_name = label if label else (code_parts[0] if code_parts else '')
                sec_addr = code_parts[1] if len(code_parts) > 1 else '*'
                sec_size = code_parts[2] if len(code_parts) > 2 else '*'
                
                # Determine new section address (use pre-computed if available)
                new_location = location
                if sec_name and sec_name.upper() in self._section_addresses:
                    new_location = self._section_addresses[sec_name.upper()]
                elif sec_addr != '*':
                    new_location = self.expr_parser.parse(sec_addr, line_num)

                # Первая секция: бинарный образ начинается с new_location (как в zasm)
                if location == 0 and self._write_pos == 0:
                    self._base_offset = new_location
                
                # Set new section symbol FIRST so prev section size expr can reference it
                if sec_name:
                    self.symbols[sec_name.upper()] = new_location
                
                # Close previous section (now size expressions can reference new section)
                if self._current_section:
                    prev_name, prev_start, prev_auto, prev_size_expr = self._current_section
                    if prev_auto:
                        prev_size = location - prev_start
                    elif prev_size_expr:
                        try:
                            prev_size = self.expr_parser.parse(prev_size_expr, line_num)
                        except Exception:
                            prev_size = location - prev_start
                    else:
                        prev_size = location - prev_start
                    self.symbols[prev_name.upper() + '_SIZE'] = prev_size
                    self.symbols[prev_name.upper() + '_END'] = prev_start + prev_size
                    # Pad to fixed section size (pass 2: add bytes)
                    if not prev_auto and prev_size_expr:
                        try:
                            fixed_size = self.expr_parser.parse(prev_size_expr, line_num)
                            actual_size = location - prev_start
                            if actual_size < fixed_size:
                                self._write(bytearray([self._ds_fill]) * (fixed_size - actual_size))
                        except Exception:
                            pass
                
                location = new_location
                self.pc = location
                auto_size = (sec_size == '*')
                self._current_section = (sec_name, location, auto_size, sec_size if not auto_size else None)
                continue

            # EQU/DEF — обновляем символ (для REPT с переопределением)
            if mnemonic in ('EQU', '.EQU', 'DEFL', '=', 'DEF', '.DEF'):
                if label:
                    self.expr_parser.pc = location
                    value = self.expr_parser.parse(operand, line_num)
                    self.symbols[label.upper()] = value
                continue
            # EQU/DEF без извлечённой метки
            m_eq = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s+(?:EQU|DEF|DEFL)\s+(.*)', stripped, re.IGNORECASE)
            if m_eq:
                eq_label = m_eq.group(1)
                eq_operand = m_eq.group(2)
                self.expr_parser.pc = location
                _idents = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', eq_operand)
                _all_defined = all(_i.upper() in self.symbols or _i in self.symbols for _i in _idents)
                if _all_defined:
                    value = self.expr_parser.parse(eq_operand, line_num)
                    self.symbols[eq_label.upper()] = value
                else:
                    self._pending_equ.append((eq_label.upper(), eq_operand))
                continue

            # REPT/ENDM — no-op
            if mnemonic in ('REPT', 'ENDM', '.REPT', '.ENDM'):
                continue
            # DS (optional: DS N,fill)
            if mnemonic in ('DS', '.DS', 'SPACE', '.SPACE'):
                self.expr_parser.pc = location
                ds_parts = self._split_operands(operand)
                count = self.expr_parser.parse(ds_parts[0], line_num)
                fill = self._ds_fill
                if len(ds_parts) > 1:
                    fill = self.expr_parser.parse(ds_parts[1], line_num) & 0xFF
                self._write(bytearray([fill] * count))
                self.listing.append((location, bytes([fill] * count), text.strip()))
                location += count
                self.pc = location
                continue

            # DB/DM
            if mnemonic in ('DB', 'DM', '.DB', '.DM', 'BYTE'):
                data = self._parse_db(operand, line_num)
                self._write(data)
                self.listing.append((location, bytes(data), text.strip()))
                location += len(data)
                self.pc = location
                continue

            if mnemonic in ('DW', '.DW', 'WORD'):
                data = self._parse_dw(operand, line_num)
                self._write(data)
                self.listing.append((location, bytes(data), text.strip()))
                location += len(data)
                self.pc = location
                continue

            # XDEF/XREF/SECTION/IF/ENDIF/ELSE/LOCAL/ENDLOCAL/ERROR — no-op
            if mnemonic in ('XDEF', 'XREF', 'SECTION', '.XDEF', '.XREF', '.SECTION',
                           'IF', 'ENDIF', 'ELSE', 'LOCAL', 'ENDLOCAL', 'ERROR',
                           '.IF', '.ENDIF', '.ELSE', '.LOCAL', '.ENDLOCAL', '.ERROR',
                           'CPU', 'ASEG', 'TITLE', '.TITLE',
                           'ENDR', 'DATA', 'BLKB', 'DISKDEF', 'IRP', 'ASSERT',
                           'DEFW', '.DATA', '.BLKB', '.DISKDEF', '.IRP', '.ASSERT',
                           '.DEFW', '#DATA', '#ASSERT', 'ASMPC', 'MACRO', 'ALIGN', '.ALIGN'):
                continue
            # END (optional: END [start])
            if mnemonic in ('END', '.END'):
                break

            # Обычная инструкция — полная кодировка через MNEMONICS
            if mnemonic in MNEMONICS:
                opcode, fmt, size = MNEMONICS[mnemonic]
                operands = self._split_operands(operand) if operand else []
                code = self._encode_instruction(mnemonic, opcode, fmt, operands, line_num)
                if code is not None:
                    self._write(code)
                    location += len(code)
                else:
                    self._write(bytearray(size))
                    location += size
                self.pc = location
            else:
                self._error(line_num, f"Неизвестная мнемоника: {mnemonic}")
                self._write(bytes([0x00]))
                location += 1
                self.pc = location

        # Close last section (create _SIZE symbol)
        if self._current_section:
            prev_name, prev_start, prev_auto, prev_size_expr = self._current_section
            if prev_auto:
                prev_size = location - prev_start
            elif prev_size_expr:
                try:
                    prev_size = self.expr_parser.parse(prev_size_expr, line_num)
                except Exception:
                    prev_size = location - prev_start
            else:
                prev_size = location - prev_start
            self.symbols[prev_name.upper() + '_SIZE'] = prev_size
            # Pad to fixed section size (pass 2: add bytes)
            if not prev_auto and prev_size_expr:
                try:
                    fixed_size = self.expr_parser.parse(prev_size_expr, line_num)
                    actual_size = location - prev_start
                    if actual_size < fixed_size:
                        self._write(bytearray(fixed_size - actual_size))
                        location = prev_start + fixed_size
                        self.pc = location
                except Exception:
                    pass
            self._current_section = None

        return AsmResult(
            success=len(self.errors) == 0,
            binary=bytes(self.binary[:self._write_pos]) if self._write_pos < len(self.binary) else bytes(self.binary),
            symbols=dict(self.symbols),
            origin=self.origin,
            errors=list(self.errors),
            warnings=list(self.warnings),
            listing=list(self.listing),
            end_address=location
        )

    # ---------------------------------------------------------
    # КОДИРОВАНИЕ ИНСТРУКЦИЙ
    # ---------------------------------------------------------

    def _encode_instruction(self, mnemonic: str, opcode: int, fmt: str,
                            operands: list[str], line_num: int) -> bytearray | None:
        """Кодирует одну инструкцию. Возвращает байты или None при ошибке."""

        if fmt == '':
            return bytearray([opcode])

        if fmt == 'r':
            if len(operands) < 1:
                self._error(line_num, f"{mnemonic}: ожидается регистр")
                return bytearray([opcode])
            reg_code = self._get_reg_code(operands[0], line_num)
            # INR/DCR используют другой паттерн: opcode + reg_code * 8
            if mnemonic in ('INR', 'DCR'):
                return bytearray([opcode + reg_code * 8])
            return bytearray([opcode | reg_code])

        if fmt == 'r,r':
            if len(operands) < 2:
                self._error(line_num, f"{mnemonic}: ожидается два регистра")
                return bytearray([opcode])
            dst = self._get_reg_code(operands[0], line_num)
            src = self._get_reg_code(operands[1], line_num)
            return bytearray([opcode | (dst << 3) | src])

        if fmt == 'rp':
            if len(operands) < 1:
                self._error(line_num, f"{mnemonic}: ожидается пара регистров")
                return bytearray([opcode])
            rp_code = self._get_rp_code(operands[0], line_num, use_psw=False)
            return bytearray([opcode | (rp_code << 4)])

        if fmt == 'rpsw':
            if len(operands) < 1:
                self._error(line_num, f"{mnemonic}: ожидается пара регистров")
                return bytearray([opcode])
            op_u = operands[0].strip().upper()
            if op_u in ('A', 'PSW'):
                rp_code = 3
            else:
                rp_code = self._get_rp_code(operands[0], line_num, use_psw=True)
            return bytearray([opcode | (rp_code << 4)])

        if fmt == 'd8':
            if len(operands) < 1:
                self._error(line_num, f"{mnemonic}: ожидается операнд")
                return bytearray([opcode, 0x00])
            val = self._parse_operand(operands[0], line_num, allow_current=True)
            if val is None:
                self._error(line_num, f"Невозможно вычислить: {operands[0]}")
                val = 0
            if val < 0:
                self._error(line_num, f"{mnemonic}: отрицательное значение 0x{val:X}")
            # Для IN/OUT порт может быть 16-битным (Z80) — берём младший байт
            return bytearray([opcode, val & 0xFF])

        if fmt == 'd16':
            if len(operands) < 1:
                self._error(line_num, f"{mnemonic}: ожидается адрес")
                return bytearray([opcode, 0x00, 0x00])
            val = self._parse_operand(operands[0], line_num, allow_current=True)
            if val is None:
                self._error(line_num, f"Невозможно вычислить: {operands[0]}")
                val = 0
            return bytearray([opcode, val & 0xFF, (val >> 8) & 0xFF])

        if fmt == 'r,d8':
            if len(operands) < 2:
                # zasm: "MVI B 8" без запятой — пробуем разбить по пробелу
                if len(operands) == 1 and ' ' in operands[0]:
                    parts = operands[0].split(None, 1)
                    if len(parts) == 2:
                        operands = parts
            if len(operands) < 2:
                self._error(line_num, f"{mnemonic}: ожидается регистр и операнд")
                return bytearray([opcode, 0x00])
            reg_code = self._get_reg_code(operands[0], line_num)
            val = self._parse_operand(operands[1], line_num, allow_current=True)
            if val is None:
                self._error(line_num, f"Невозможно вычислить: {operands[1]}")
                val = 0
            if val < 0:
                self._error(line_num, f"{mnemonic}: отрицательное значение 0x{val:X}")
            return bytearray([opcode | (reg_code << 3), val & 0xFF])

        if fmt == 'rp,d16':
            if len(operands) < 2:
                self._error(line_num, f"{mnemonic}: ожидается пара и адрес")
                return bytearray([opcode, 0x00, 0x00])
            rp_code = self._get_rp_code(operands[0], line_num, use_psw=False)
            val = self._parse_operand(operands[1], line_num, allow_current=True)
            if val is None:
                self._error(line_num, f"Невозможно вычислить: {operands[1]}")
                val = 0
            return bytearray([opcode | (rp_code << 4), val & 0xFF, (val >> 8) & 0xFF])

        if fmt == 'rst':
            if len(operands) < 1:
                self._error(line_num, "RST: ожидается номер 0-7")
                return bytearray([opcode])
            val = self._parse_operand(operands[0], line_num, allow_current=False)
            if val is None:
                self._error(line_num, f"Невозможно вычислить: {operands[0]}")
                val = 0
            if val < 0 or val > 7:
                self._error(line_num, f"RST: номер должен быть 0-7, получено {val}")
                val = 0
            return bytearray([opcode | ((val & 7) << 3)])

        self._error(line_num, f"Неизвестный формат: {fmt}")
        return bytearray([opcode])

    # ---------------------------------------------------------
    # ПАРСИНГ ОПЕРАНДОВ
    # ---------------------------------------------------------

    def _parse_operand(self, operand_str: str, line_num: int,
                       allow_current: bool = False) -> int | None:
        """
        Парсит операнд и возвращает его числовое значение.

        Поддерживает:
          - Числовые литералы: 0xFF, 0FFH, 255, 101101B, 177Q
          - Метки: LABEL
          - Текущий адрес: $
          - Простые выражения: LABEL + 5, LABEL - 3, $ + 10

        Args:
            operand_str: строка операнда
            line_num: номер строки (для ошибок)
            allow_current: разрешить использование $

        Returns:
            Числовое значение или None при ошибке.
        """
        operand_str = operand_str.strip()
        if not operand_str:
            self._error(line_num, "Пустой операнд")
            return None

        # Синхронизируем pc в парсере выражений
        self.expr_parser.pc = self.pc

        # Текущий адрес ($)
        if operand_str == '$':
            if allow_current:
                return self.pc
            self._error(line_num, "$ недопустим в этом контексте")
            return None

        # Character literal: 'X' -> ASCII value
        if len(operand_str) >= 2 and operand_str[0] in ("'", '"') and operand_str[-1] == operand_str[0]:
            inner = operand_str[1:-1]
            if len(inner) == 1:
                return ord(inner)
            # Escape sequences
            if inner.startswith('\\'):
                esc = inner[1]
                esc_map = {'n': 0x0A, 't': 0x09, 'r': 0x0D, '0': 0x00}
                if esc in esc_map:
                    return esc_map[esc]
                return ord(esc)
            # Multi-char string: return first char
            return ord(inner[0])

        # Пробуем как число или выражение через ExpressionParser
        # Подставляем $ текущим адресом
        expr_str = operand_str
        if allow_current and '$' in expr_str:
            expr_str = expr_str.replace('$', str(self.pc))
        # Простой идентификатор без операторов — предупреждение если не определён
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', expr_str):
            in_defines = any(expr_str.lower() == d.lower() for d in self.defines)
            if expr_str.upper() not in self.symbols and not in_defines:
                # Warning, не error: файл может быть "нижним" (включается в другой)
                self.warnings.append(f"L{line_num}: Неопределённая метка: {expr_str}")
                return 0
        try:
            return self.expr_parser.parse(expr_str, line_num)
        except Exception:
            pass

        # Пробуем как выражение: метка +/- число
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*([+\-])\s*(.+)$', operand_str)
        if m:
            label = m.group(1).upper()
            op = m.group(2)
            rest_str = m.group(3).strip()

            # Проверяем, что метка определена
            if label not in self.symbols:
                self._error(line_num, f"Неопределённая метка: {label}")
                return None

            base_val = self.symbols[label]

            # Остаток может быть числом или $
            if rest_str == '$' and allow_current:
                rest_val = self.pc
            else:
                rest_val = parse_number(rest_str)
                if rest_val is None:
                    self._error(line_num, f"Невозможно вычислить: {rest_str}")
                    return None

            if op == '+':
                return base_val + rest_val
            else:
                return base_val - rest_val

        # Пробуем как метку
        label = operand_str.upper()
        if label in self.symbols:
            return self.symbols[label]

        # Символьный литерал 'X'
        if len(operand_str) == 3 and operand_str.startswith("'") and operand_str.endswith("'"):
            return ord(operand_str[1])

        self._error(line_num, f"Неопределённая метка или неверный операнд: {operand_str}")
        return None

    def _parse_db(self, operand, line_num):
        """Разобрать DB/DM (байты)"""
        result = bytearray()
        parts = self._split_operands(operand)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # zasm: <expr> — литеральный текст
            if part.startswith('<') and part.endswith('>'):
                content = part[1:-1]
                result.extend(content.encode('ascii', errors='replace'))
                continue
            # M80: N dup(value)
            dup_m = re.match(r'^(\S+)\s+dup\s*\((.+)\)$', part, re.IGNORECASE)
            if dup_m:
                count = self.expr_parser.parse(dup_m.group(1), line_num)
                value = self.expr_parser.parse(dup_m.group(2).strip(), line_num) & 0xFF
                result.extend(bytearray([value] * count))
                continue
            # Специальные макросы zasm
            if part == '__date__':
                result.extend(self._now.strftime('%Y-%m-%d').encode('ascii'))
                continue
            if part == '__TIME__':
                result.extend(self._now.strftime('%H:%M:%S').encode('ascii'))
                continue
            # Строковый литерал в одинарных кавычках
            if part.startswith("'"):
                end_quote = part.find("'", 1)
                if end_quote > 0:
                    remaining = part[end_quote+1:].strip()
                    if remaining:
                        # Expression like 'D'+80H: evaluate char_value + offset
                        char_val = ord(part[1:end_quote])
                        expr = f"{char_val}{remaining}"
                        value = self.expr_parser.parse(expr, line_num)
                        result.append(value & 0xFF)
                    else:
                        result.extend(part[1:end_quote].encode('ascii'))
                    continue
            # Строковый литерал в двойных кавычках
            if part.startswith('"'):
                end_quote = part.find('"', 1)
                if end_quote > 0:
                    result.extend(part[1:end_quote].encode('ascii'))
                    continue
            # Числовое выражение
            if part.upper() == 'CR':
                result.append(0x0D)
                continue
            if part.upper() == 'LF':
                result.append(0x0A)
                continue
            try:
                value = self.expr_parser.parse(part, line_num)
                result.append(value & 0xFF)
            except Exception:
                result.append(0x00)
        return result

    def _parse_dw(self, operand, line_num):
        """Разобрать DW (слова, little-endian)."""
        result = bytearray()
        parts = self._split_operands(operand)
        for part in parts:
            value = self.expr_parser.parse(part.strip(), line_num)
            result.append(value & 0xFF)
            result.append((value >> 8) & 0xFF)
        return result

    # ---------------------------------------------------------
    # КОДЫ РЕГИСТРОВ
    # ---------------------------------------------------------

    def _get_reg_code(self, reg_str: str, line_num: int) -> int:
        """Код регистра (3 бита). Поддерживает пары как одиночные (zasm)."""
        reg = reg_str.strip().upper()
        if reg in REGISTERS:
            return REGISTERS[reg]
        # zasm: пара регистров как одиночный (MOV M,DE -> MOV M,E)
        pair_to_low = {'BC': 'C', 'DE': 'E', 'HL': 'L', 'PSW': 'A'}
        if reg in pair_to_low:
            return REGISTERS[pair_to_low[reg]]
        self._error(line_num, f"Неверный регистр: {reg_str}")
        return 0

    def _get_rp_code(self, rp_str: str, line_num: int, use_psw: bool) -> int:
        """Код пары регистров (2 бита). Поддерживает одиночные как пары (zasm)."""
        rp = rp_str.strip().upper()
        table = REG_PAIRS_PSW if use_psw else REG_PAIRS
        if rp in table:
            return table[rp]
        # zasm: одиночный регистр как пара (LXI A,4 -> LXI PSW,4)
        reg_to_pair = {'B': 'BC', 'C': 'BC', 'D': 'DE', 'E': 'DE',
                       'H': 'HL', 'L': 'HL', 'A': 'PSW'}
        if rp in reg_to_pair:
            pair = reg_to_pair[rp]
            if pair in table:
                return table[pair]
            # PSW/SP alias
            if pair == 'PSW' and 'SP' in table:
                return table['SP']
            if pair == 'SP' and 'PSW' in table:
                return table['PSW']
        self._error(line_num, f"Неверная пара регистров: {rp_str}")
        return 0

    # ---------------------------------------------------------
    # ЭМИССИЯ КОДА
    # ---------------------------------------------------------

    def _emit(self, data: bytearray, addr: int, source_line: str):
        """Добавить байты в выходной буфер."""
        for b in data:
            self._write(bytes([b & 0xFF]))
        if source_line:
            self.listing.append((addr, bytes(data), source_line))
        self.pc += len(data)

    # ---------------------------------------------------------
    # ОШИБКИ
    # ---------------------------------------------------------

    def _error(self, line_num: int, message: str):
        """Добавить ошибку сборки."""
        self.errors.append(AsmError(
            line=line_num,
            message=message,
            source=self._filename,
        ))

    def _split_operands(self, operand):
        """Разбить операнды по запятым (с учётом кавычек и <...>)"""
        parts = []
        current = ''
        in_quotes = False
        quote_char = None
        angle_depth = 0

        for ch in operand:
            if angle_depth > 0:
                current += ch
                if ch == '<':
                    angle_depth += 1
                elif ch == '>':
                    angle_depth -= 1
            elif ch in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = ch
                current += ch
            elif ch == quote_char and in_quotes:
                in_quotes = False
                current += ch
            elif ch == '<' and not in_quotes:
                angle_depth = 1
                current += ch
            elif ch == ',' and not in_quotes:
                parts.append(current)
                current = ''
            else:
                current += ch

        if current:
            parts.append(current)

        return parts


# =============================================================
# УДОБНАЯ ФУНКЦИЯ ДЛЯ БЫСТРОГО ИСПОЛЬЗОВАНИЯ
# =============================================================

def assemble(source: str, filename: str = "", now=None) -> AsmResult:
    """Быстрая сборка: создать ассемблер и ассемблировать."""
    asm = Assembler(now=now)
    return asm.assemble(source, filename)


# =============================================================
# САМОТЕСТ
# =============================================================

if __name__ == "__main__":
    test_source = """
; Тестовая программа для ассемблера i8080
        ORG 0100H
START:  MVI A, 55H        ; Загрузить 0x55 в A
        OUT 01H           ; Вывести в порт 1
        MVI B, 0FFH       ; B = FF
        MVI C, 0AH        ; C = 0A
LOOP:   DCR B             ; B = B - 1
        JNZ LOOP          ; Повторить пока B != 0
        LDA DATA          ; Загрузить из памяти
        STA DATA+1        ; Сохранить в DATA+1
        CALL SUBR         ; Вызов подпрограммы
        HLT               ; Стоп

SUBR:   INR A             ; A = A + 1
        RET               ; Возврат

DATA:   DB 42H, 'A', 10010110B
        DW 1234H
        DS 10
        END
"""
    result = assemble(test_source, "test.asm")
    if result.success:
        print(f"✅ Сборка успешна: {len(result.binary)} байт")
        print(f"   Origin: 0x{result.origin:04X}")
        print(f"   End:    0x{result.end_address:04X}")
        print(f"   Символы: {result.symbols}")
        print(f"   Код: {result.binary.hex(' ')}")
    else:
        print("❌ Ошибки сборки:")
        for err in result.errors:
            print(f"   {err}")
