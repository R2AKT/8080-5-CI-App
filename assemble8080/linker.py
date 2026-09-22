"""
Linker for i8080-5 CI.

Takes multiple object files (.obj), resolves symbols, applies relocations,
and produces a single binary output.

Linker script format (.lnk):
    INPUT file1.obj file2.obj [...]
    OUTPUT file.bin
    MAP file.map
    ORIGIN 0x0000
    SIZE 0x10000
    FILL 0xFF
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from .objfile import ObjectFile, load_obj, save_obj
from .mapfile import MapFile, MapEntry, generate_map


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
    
    # Step 1: Check for ORG conflicts
    placed = {}  # {org: obj_name}
    for obj in objects:
        if obj.org in placed:
            errors.append(LinkError(
                f"ORG conflict: {obj.name} and {placed[obj.org]} both at 0x{obj.org:04X}",
                file=obj.name
            ))
        else:
            placed[obj.org] = obj.name
    
    if errors:
        return LinkResult(success=False, errors=errors)
    
    # Step 2: Build global symbol table
    # First pass: collect all exported symbols
    global_symbols = {}  # {name: absolute_address}
    for obj in objects:
        for name in obj.exports:
            if name in obj.symbols:
                addr = obj.org + obj.symbols[name]
                if name in global_symbols:
                    warnings.append(f"Duplicate export: {name} (in {obj.name})")
                else:
                    global_symbols[name] = addr
    
    # Also add all symbols (for local resolution within same object)
    all_symbols = {}
    for obj in objects:
        for name, offset in obj.symbols.items():
            addr = obj.org + offset
            if name not in all_symbols:
                all_symbols[name] = addr
    
    # Step 3: Check for unresolved imports
    for obj in objects:
        for imp in obj.imports:
            if imp not in global_symbols and imp not in all_symbols:
                errors.append(LinkError(
                    f"Unresolved symbol: {imp} (imported by {obj.name})",
                    file=obj.name
                ))
    
    if errors:
        return LinkResult(success=False, errors=errors)
    
    # Step 4: Allocate output buffer
    output_size = max(size, origin + max((o.org + o.size for o in objects), default=0))
    output = bytearray([fill] * output_size)
    
    # Step 5: Place object data
    for obj in objects:
        for i, byte in enumerate(obj.data):
            addr = obj.org + i
            if addr < output_size:
                output[addr] = byte
    
    # Step 6: Apply relocations
    for obj in objects:
        for reloc in obj.relocations:
            sym_addr = global_symbols.get(reloc.symbol) or all_symbols.get(reloc.symbol)
            if sym_addr is None:
                warnings.append(f"Relocation: symbol '{reloc.symbol}' not found (in {obj.name})")
                continue
            
            patch_addr = obj.org + reloc.offset
            if patch_addr >= output_size:
                continue
            
            if reloc.size == 2:
                # 16-bit little-endian
                output[patch_addr] = sym_addr & 0xFF
                output[patch_addr + 1] = (sym_addr >> 8) & 0xFF
            elif reloc.size == 1:
                # 8-bit (low byte only)
                output[patch_addr] = sym_addr & 0xFF
    
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
        fake.binary = bytes(output)
        fake.symbols = all_symbols
        fake.listing = []
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


def link_from_script(script_path: str) -> LinkResult:
    """Link using a .lnk script file."""
    with open(script_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    config = parse_link_script(text)
    script_dir = os.path.dirname(os.path.abspath(script_path))
    
    # Load object files
    objects = []
    errors = []
    for inp in config["inputs"]:
        path = inp if os.path.isabs(inp) else os.path.join(script_dir, inp)
        if not os.path.exists(path):
            errors.append(LinkError(f"Input file not found: {path}"))
            continue
        try:
            objects.append(load_obj(path))
        except Exception as e:
            errors.append(LinkError(f"Error loading {path}: {e}"))
    
    if errors:
        return LinkResult(success=False, errors=errors)
    
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
