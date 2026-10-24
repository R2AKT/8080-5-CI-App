"""
assemble8080 — компактный макроассемблер i8080.

Использует PEP 562 lazy imports: подмодули загружаются
только при первом обращении, что исключает RuntimeWarning
при `python -m assemble8080.assembler`.
"""

# Карта: имя → (подмодуль, [экспортируемые имена])
_LAZY_MAP = {
    "Assembler":           ("assembler",    ["Assembler"]),
    "assemble":            ("assembler",    ["assemble"]),
    "AsmError":            ("assembler",    ["AsmError"]),
    "AsmResult":           ("assembler",    ["AsmResult"]),
    "MNEMONICS":           ("assembler",    ["MNEMONICS"]),
    "MNEMONICS_8080":      ("assembler",    ["MNEMONICS_8080"]),
    "MNEMONICS_8085":      ("assembler",    ["MNEMONICS_8085"]),
    "ALL_MNEMONICS":       ("assembler",    ["ALL_MNEMONICS"]),
    "REGISTERS":           ("assembler",    ["REGISTERS"]),
    "REG_PAIRS":           ("assembler",    ["REG_PAIRS"]),
    "REG_PAIRS_PSW":       ("assembler",    ["REG_PAIRS_PSW"]),
    "CONDITIONS":          ("assembler",    ["CONDITIONS"]),
    "parse_number":        ("numbers",      ["parse_number"]),
    "NumberParser":        ("numbers",      ["NumberParser"]),
    "Preprocessor":        ("preprocessor", ["Preprocessor"]),
    "PreprocessorError":   ("preprocessor", ["PreprocessorError"]),
    "MapFile":             ("mapfile",      ["MapFile"]),
    "MapEntry":            ("mapfile",      ["MapEntry"]),
    "generate_map":        ("mapfile",      ["generate_map"]),
    "parse_map":           ("mapfile",      ["parse_map"]),
    "load_map_file":       ("mapfile",      ["load_map_file"]),
    "save_map_file":       ("mapfile",      ["save_map_file"]),
    "ObjectFile":          ("objfile",      ["ObjectFile"]),
    "Relocation":          ("objfile",      ["Relocation"]),
    "save_obj":            ("objfile",      ["save_obj"]),
    "load_obj":            ("objfile",      ["load_obj"]),
    "obj_from_asm_result": ("objfile",      ["obj_from_asm_result"]),
    "link":                ("linker",       ["link"]),
    "link_from_script":    ("linker",       ["link_from_script"]),
    "parse_link_script":   ("linker",       ["parse_link_script"]),
    "LinkResult":          ("linker",       ["LinkResult"]),
    "LinkError":           ("linker",       ["LinkError"]),
}

__all__ = list(_LAZY_MAP.keys())


def __getattr__(name):
    if name in _LAZY_MAP:
        mod_name, attrs = _LAZY_MAP[name]
        import importlib
        mod = importlib.import_module(f".{mod_name}", __name__)
        val = getattr(mod, name)
        # Кэшируем в namespace пакета, чтобы subsequent getattr шло напрямую
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return __all__
