"""
Linker for i8080-5 CI.

Takes multiple object files (.obj), resolves symbols, applies relocations,
and produces a single binary output.

Linker script format (.lnk):
    INPUT file1.obj file2.obj [...]  (also .lib archives)
    OUTPUT file.bin
    MAP file.map
    ORIGIN 0x0000
    SIZE 0x10000
    FILL 0xFF
"""
import os
from dataclasses import dataclass, field

from .objfile import load_obj, ObjectFile, Relocation, OBJ_FORMAT_VERSION
from .mapfile import MapEntry, generate_map
from .librarian import load_library


@dataclass
class LinkError:
    """Linker error."""
    message: str
    file: str = ""


@dataclass
class LinkResult:
    """Result of linking."""
    success: bool
    binary: bytes = b""
    origin: int = 0
    size: int = 0
    symbols: dict = field(default_factory=dict)   # {name: address}
    errors: list = field(default_factory=list)    # [LinkError]
    warnings: list = field(default_factory=list)  # [str]
    map_text: str = ""


def parse_link_script(text: str) -> dict:
    """Parse a .lnk linker script.
    
    Returns dict with keys: inputs, output, map, origin, size, fill
    """
    config = {
        "inputs": [],
        "output": "output.bin",
        "map": "",
        "origin": 0,
        "size": 0x10000,
        "fill": 0xFF,
    }
    
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith(';') or line.startswith('#'):
            continue
        
        upper = line.upper()
        
        if upper.startswith('INPUT'):
            # INPUT file1.obj file2.obj ...
            parts = line[5:].strip().split()
            config["inputs"] = parts
        elif upper.startswith('OUTPUT'):
            config["output"] = line[6:].strip().strip('"').strip("'")
        elif upper.startswith('MAP'):
            config["map"] = line[3:].strip().strip('"').strip("'")
        elif upper.startswith('ORIGIN'):
            val = line[6:].strip()
            config["origin"] = int(val, 0) if val.startswith('0x') or val.startswith('0X') else int(val)
        elif upper.startswith('SIZE'):
            val = line[4:].strip()
            config["size"] = int(val, 0) if val.startswith('0x') or val.startswith('0X') else int(val)
        elif upper.startswith('FILL'):
            val = line[4:].strip()
            config["fill"] = int(val, 0) if val.startswith('0x') or val.startswith('0X') else int(val)
    
    return config


def link(objects: list, origin: int = 0, size: int = 0x10000, fill: int = 0xFF) -> LinkResult:
    """Link multiple object files into a single binary.
    
    Args:
        objects: list of ObjectFile
        origin: base address for output
        size: total output size
        fill: fill value for gaps
    
    Returns:
        LinkResult
    """
    errors = []
    warnings = []
    
    # Step 1: Sequential placement from ORIGIN.
    # Each object's own org is IGNORED for placement - it is only the
    # assembler's virtual base used to compute data-relative offsets.
    # Modules are laid out back-to-back starting at `origin`.
    bases = []  # base address of each object in the output
    cursor = origin
    for obj in objects:
        bases.append(cursor)
        cursor += len(obj.data) if len(obj.data) else obj.size
    
    # Step 2: Build global symbol table
    # Case-insensitive mode (default): normalize keys to UPPER so that
    # relocations/imports (UPPER) match symbols (original case).
    # Case-sensitive mode: exact matching (no normalization).
    def _norm(obj, name):
        return name if obj.case_sensitive else name.upper()
    
    # First pass: collect all exported symbols
    global_symbols = {}  # {name: absolute_address}
    for idx, obj in enumerate(objects):
        for name in obj.exports:
            if name in obj.symbols:
                addr = bases[idx] + obj.symbols[name]
                key = _norm(obj, name)
                if key in global_symbols:
                    warnings.append(f"Duplicate export: {name} (in {obj.name})")
                else:
                    global_symbols[key] = addr
    
    # Also add all symbols (for local resolution within same object)
    all_symbols = {}
    for idx, obj in enumerate(objects):
        for name, offset in obj.symbols.items():
            addr = bases[idx] + offset
            key = _norm(obj, name)
            if key not in all_symbols:
                all_symbols[key] = addr
    
    # Step 3: Check for unresolved imports
    for obj in objects:
        for imp in obj.imports:
            imp_key = _norm(obj, imp)
            if imp_key not in global_symbols and imp_key not in all_symbols:
                errors.append(LinkError(
                    f"Unresolved symbol: {imp} (imported by {obj.name})",
                    file=obj.name
                ))
    
    if errors:
        return LinkResult(success=False, errors=errors)
    
    # Step 4: Allocate output buffer
    output_size = max(size, origin + max((o.org + o.size for o in objects), default=0))
    output = bytearray([fill] * output_size)
    
    # Step 5: Place object data at its assigned base
    for idx, obj in enumerate(objects):
        for i, byte in enumerate(obj.data):
            addr = bases[idx] + i
            if addr < output_size:
                output[addr] = byte
    
    # Step 6: Apply relocations
    for idx, obj in enumerate(objects):
        for reloc in obj.relocations:
            sym_key = _norm(obj, reloc.symbol)
            sym_addr = global_symbols.get(sym_key) or all_symbols.get(sym_key)
            if sym_addr is None:
                warnings.append(f"Relocation: symbol '{reloc.symbol}' not found (in {obj.name})")
                continue
            
            patch_addr = bases[idx] + reloc.offset
            if patch_addr >= output_size:
                continue
            
            patch_val = (sym_addr + getattr(reloc, 'addend', 0)) & 0xFFFF
            if reloc.size == 2:
                # 16-bit little-endian
                output[patch_addr] = patch_val & 0xFF
                output[patch_addr + 1] = (patch_val >> 8) & 0xFF
            elif reloc.size == 1:
                # 8-bit (low byte only)
                output[patch_addr] = patch_val & 0xFF
    
    # Step 7: Generate map
    map_entries = []
    for name, addr in sorted(all_symbols.items(), key=lambda x: x[1]):
        map_entries.append(MapEntry(addr, 1, "CODE", name))
    
    map_text = ""
    if map_entries:
        # Build a pseudo-AsmResult for map generation
        class _FakeResult:
            pass
        fake = _FakeResult()
        fake.origin = origin
        fake.binary = b"".join(o.data for o in objects)
        fake.symbols = all_symbols
        fake.listing = [
            (bases[i] + dl[0], bytes(dl[1]), dl[2])
            for i, o in enumerate(objects)
            for dl in getattr(o, 'data_lines', [])
        ]
        from .mapfile import generate_map
        map_text = generate_map(fake, source_name="(linked)")
    
    return LinkResult(
        success=True,
        binary=bytes(output),
        origin=origin,
        size=output_size,
        symbols=all_symbols,
        warnings=warnings,
        map_text=map_text,
    )


def _obj_from_json(d: dict) -> ObjectFile:
    """Deserialize an object file JSON dict into an ObjectFile."""
    if d.get("format") != OBJ_FORMAT_VERSION:
        raise ValueError(f"Unsupported object format: {d.get('format')}")
    obj = ObjectFile(
        name=d.get("name", ""),
        source=d.get("source", ""),
        org=d.get("org", 0),
        size=d.get("size", 0),
        data=bytes.fromhex(d.get("data", "")),
        symbols=d.get("symbols", {}),
        exports=list(d.get("exports", [])),
        imports=list(d.get("imports", [])),
        case_sensitive=d.get("case_sensitive", False),
    )
    for r in d.get("relocations", []):
        obj.relocations.append(Relocation(
            offset=r["offset"],
            size=r["size"],
            symbol=r["symbol"],
            addend=r.get("addend", 0),
        ))
    return obj


def _resolve_libraries(objects: list, libraries: list) -> None:
    """Resolution stage: pull archive modules for undefined imports.

    Mutates `objects`, appending every module extracted from the
    archives in the order they were needed.

    Args:
        objects: list of ObjectFile (project inputs).
        libraries: list of (path, dict) - loaded .lib archives.

    Raises:
        ValueError: if a required symbol is absent from every index.
    """
    extracted = set()  # (library name, module name) pairs already pulled

    def _key(obj, name):
        return name if obj.case_sensitive else name.upper()

    # Symbols already defined (exports) vs symbols requested (imports)
    resolved = set()
    required = set()
    for obj in objects:
        resolved.update(_key(obj, n) for n in obj.exports)
        required.update(_key(obj, n) for n in obj.imports)

    while True:
        unresolved = required - resolved
        if not unresolved:
            break
        symbol = sorted(unresolved)[0]

        # Search every archive index (keys are UPPER-cased export names)
        mod_name = None
        archive = None
        for _path, lib in libraries:
            index = lib.get("index", {})
            mod_name = index.get(symbol) or index.get(symbol.upper())
            if mod_name:
                archive = lib
                break

        if mod_name is None:
            raise ValueError(
                f"Linker Error: Undefined reference to symbol '{symbol}'")

        archive_key = (archive.get("name", ""), mod_name)
        if archive_key not in extracted:
            extracted.add(archive_key)
            obj_json = archive.get("modules", {}).get(mod_name)
            if obj_json is None:
                raise ValueError(
                    f"Linker Error: archive '{archive.get('name', '')}'"
                    f"index points to missing module '{mod_name}'")
            new_obj = _obj_from_json(obj_json)
            objects.append(new_obj)
            resolved.update(_key(new_obj, n) for n in new_obj.exports)
            required.update(_key(new_obj, n) for n in new_obj.imports)
        else:
            # Module already in the link set - its exports cover the symbol.
            resolved.add(symbol)


def link_from_script(script_path: str) -> LinkResult:
    """Link using a .lnk script file.

    INPUT may reference project objects (.obj) and archive libraries
    (.lib, format i8080-lib-v1). Modules are pulled from archives on
    demand: a module is linked only if it satisfies a symbol that is
    currently undefined in the project.
    """
    with open(script_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    config = parse_link_script(text)
    script_dir = os.path.dirname(os.path.abspath(script_path))
    
    # Split inputs: explicit project objects (.obj) vs archives (.lib)
    objects = []
    libraries = []  # [(path, dict)]
    errors = []
    for inp in config["inputs"]:
        path = inp if os.path.isabs(inp) else os.path.join(script_dir, inp)
        if not os.path.exists(path):
            errors.append(LinkError(f"Input file not found: {path}"))
            continue
        try:
            if path.lower().endswith(".lib"):
                libraries.append((path, load_library(path)))
            else:
                objects.append(load_obj(path))
        except Exception as e:
            errors.append(LinkError(f"Error loading {path}: {e}"))
    
    if errors:
        return LinkResult(success=False, errors=errors)
    
    # Resolution stage: pull archive modules for undefined imports
    _resolve_libraries(objects, libraries)
    
    # Link
    result = link(
        objects,
        origin=config["origin"],
        size=config["size"],
        fill=config["fill"],
    )
    
    if not result.success:
        return result
    
    # Write output
    out_path = config["output"]
    if not os.path.isabs(out_path):
        out_path = os.path.join(script_dir, out_path)
    with open(out_path, 'wb') as f:
        f.write(result.binary)
    
    # Write map
    if config["map"] and result.map_text:
        map_path = config["map"]
        if not os.path.isabs(map_path):
            map_path = os.path.join(script_dir, map_path)
        with open(map_path, 'w', encoding='utf-8') as f:
            f.write(result.map_text)
    
    return result
