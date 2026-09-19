"""Таблица символов ассемблера."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Symbol:
    name: str
    value: int = 0
    defined: bool = False
    line: int = 0
    source: str = ""
    is_equ: bool = False      # EQU-константа (не перезаписывается)
    references: list = field(default_factory=list)  # [(line, source)]


class SymbolTable:
    """Таблица символов с поддержкой двухпроходной сборки."""

    def __init__(self):
        self._symbols: dict[str, Symbol] = {}
        self._current_scope: str = ""

    def define(self, name: str, value: int, line: int,
               source: str = "", is_equ: bool = False) -> Optional[str]:
        """Определить символ. Возвращает ошибку или None."""
        name_upper = name.upper()
        if name_upper in self._symbols:
            sym = self._symbols[name_upper]
            if sym.is_equ and sym.defined:
                return f"Символ '{name}' уже определён как EQU (строка {sym.line})"
            if sym.defined and not is_equ:
                return f"Символ '{name}' уже определён (строка {sym.line})"
            sym.value = value
            sym.defined = True
            sym.line = line
            sym.source = source
            sym.is_equ = is_equ
        else:
            self._symbols[name_upper] = Symbol(
                name=name, value=value, defined=True,
                line=line, source=source, is_equ=is_equ
            )
        return None

    def resolve(self, name: str) -> Optional[int]:
        """Разрешить символ. Возвращает значение или None."""
        sym = self._symbols.get(name.upper())
        if sym is not None and sym.defined:
            return sym.value
        return None

    def add_reference(self, name: str, line: int, source: str = ""):
        sym = self._symbols.get(name.upper())
        if sym is None:
            self._symbols[name.upper()] = Symbol(name=name)
            sym = self._symbols[name.upper()]
        sym.references.append((line, source))

    def get_undefined(self) -> list[Symbol]:
        """Неопределённые символы."""
        return [s for s in self._symbols.values() if not s.defined]

    def get_all(self) -> dict[str, Symbol]:
        return dict(self._symbols)

    def clear(self):
        self._symbols.clear()

    def get_symbol(self, name: str) -> Optional[Symbol]:
        return self._symbols.get(name.upper())

    def __contains__(self, name: str) -> bool:
        return name.upper() in self._symbols

    def __len__(self) -> int:
        return len(self._symbols)
