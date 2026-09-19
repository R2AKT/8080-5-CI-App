"""
Парсер чисел для ассемблера 8080.
Поддерживает форматы:
  0x1A, 0X1A      — шестнадцатеричный с префиксом
  1AH, 1Ah, 01AH  — шестнадцатеричный с суффиксом
  26, 26d, 26D    — десятичный
  00011010B, 11010b — двоичный
  32q, 32o        — восьмеричный
"""
import re


class NumberParser:
    """Парсер числовых литералов ассемблера 8080."""

    # Регулярные выражения для форматов
    RE_HEX_PREFIX = re.compile(r'^0[xX]([0-9A-Fa-f]+)$')
    RE_HEX_SUFFIX = re.compile(r'^([0-9][0-9A-Fa-f]*)[hH]$')
    RE_DECIMAL    = re.compile(r'^([0-9]+)[dD]?$')
    RE_BINARY     = re.compile(r'^([01]+)[bB]$')
    RE_OCTAL      = re.compile(r'^([0-7]+)[qQoO]$')

    @classmethod
    def parse(cls, text: str) -> int | None:
        """
        Парсит строку как число.
        Возвращает целое число или None, если не удалось распознать.
        """
        text = text.strip()
        if not text:
            return None

        # 1) 0x... / 0X...
        m = cls.RE_HEX_PREFIX.match(text)
        if m:
            try:
                return int(m.group(1), 16)
            except ValueError:
                return None

        # 2) ...H / ...h (должен начинаться с цифры!)
        m = cls.RE_HEX_SUFFIX.match(text)
        if m:
            try:
                return int(m.group(1), 16)
            except ValueError:
                return None

        # 3) Двоичный ...B / ...b
        m = cls.RE_BINARY.match(text)
        if m:
            try:
                return int(m.group(1), 2)
            except ValueError:
                return None

        # 4) Восьмеричный ...q / ...o
        m = cls.RE_OCTAL.match(text)
        if m:
            try:
                return int(m.group(1), 8)
            except ValueError:
                return None

        # 5) Десятичный (с необязательным суффиксом d/D)
        m = cls.RE_DECIMAL.match(text)
        if m:
            try:
                return int(m.group(1), 10)
            except ValueError:
                return None

        return None

    @classmethod
    def is_number(cls, text: str) -> bool:
        """Проверка, является ли строка числовым литералом."""
        return cls.parse(text) is not None

    @classmethod
    def is_valid_hex(cls, text: str) -> bool:
        """Проверка валидности шестнадцатеричного формата."""
        text = text.strip()
        return bool(cls.RE_HEX_PREFIX.match(text) or cls.RE_HEX_SUFFIX.match(text))
