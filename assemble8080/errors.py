"""Типы ошибок ассемблера."""
from dataclasses import dataclass, field


@dataclass
class AsmError:
    """Ошибка ассемблирования."""
    line: int              # Номер строки (1-based)
    col: int               # Колонка (1-based)
    message: str
    severity: str = "error"  # "error" | "warning"
    source: str = ""       # Имя файла (для INCLUDE)

    def __str__(self):
        loc = f"{self.source}:" if self.source else ""
        return f"{loc}{self.line}:{self.col}: {self.severity}: {self.message}"


@dataclass
class AsmResult:
    """Результат ассемблирования."""
    success: bool
    binary: bytes = b""
    origin: int = 0x0000
    symbols: dict = field(default_factory=dict)   # {name: address}
    labels: dict = field(default_factory=dict)    # {name: (line, address)}
    errors: list = field(default_factory=list)    # [AsmError]
    warnings: list = field(default_factory=list)
    listing: list = field(default_factory=list)   # [(addr, bytes, source_line)]

    @property
    def error_count(self):
        return len(self.errors)

    @property
    def warning_count(self):
        return len(self.warnings)
