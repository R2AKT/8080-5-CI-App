"""
Object file format for i8080-5 CI linker.

Format: JSON-based, version 1.
Each object file contains:
- Binary data (hex string)
- Origin address
- Symbol table (local + exported)
- Import list (undefined symbols)
- Relocation entries (address patches for linker)
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional


OBJ_FORMAT_VERSION = "i8080-obj-v1"


@dataclass
class Relocation:
    """A relocation entry: patch at offset with symbol's address."""
    offset: int      # Byte offset from section origin
    size: int        # 1 or 2 bytes
    symbol: str      # Symbol name to resolve


@dataclass
class ObjectFile:
    """Parsed object file."""
    name: str = ""
    source: str = ""
    org: int = 0
    size: int = 0
    data: bytes = b""
    symbols: dict = field(default_factory=dict)       # {name: offset_from_org}
    exports: list = field(default_factory=list)       # [name]
    imports: list = field(default_factory=list)       # [name]
    relocations: list = field(default_factory=list)   # [Relocation]
    
    def symbol_address(self, name: str) -> Optional[int]:
        """Get absolute address of a symbol in this object."""
        if name in self.symbols:
            return self.org + self.symbols[name]
        return None


def save_obj(path: str, obj: ObjectFile):
    """Save object file to disk (JSON)."""
    d = {
        "format": OBJ_FORMAT_VERSION,
        "name": obj.name,
        "source": obj.source,
        "org": obj.org,
        "size": obj.size,
        "data": obj.data.hex(),
        "symbols": obj.symbols,
        "exports": obj.exports,
        "imports": obj.imports,
        "relocations": [
            {"offset": r.offset, "size": r.size, "symbol": r.symbol}
            for r in obj.relocations
        ],
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2)


def load_obj(path: str) -> ObjectFile:
    """Load object file from disk (JSON)."""
    with open(path, 'r', encoding='utf-8') as f:
        d = json.load(f)
    
    if d.get("format") != OBJ_FORMAT_VERSION:
        raise ValueError(f"Unsupported object format: {d.get('format')}")
    
    obj = ObjectFile(
        name=d.get("name", ""),
        source=d.get("source", ""),
        org=d.get("org", 0),
        size=d.get("size", 0),
        data=bytes.fromhex(d.get("data", "")),
        symbols=d.get("symbols", {}),
        exports=d.get("exports", []),
        imports=d.get("imports", []),
    )
    for r in d.get("relocations", []):
        obj.relocations.append(Relocation(
            offset=r["offset"],
            size=r["size"],
            symbol=r["symbol"],
        ))
    return obj


def obj_from_asm_result(result, source_name: str = "") -> ObjectFile:
    """Create ObjectFile from AsmResult.
    
    The assembler must have tracked:
    - result.symbols: {name: absolute_address}
    - result.origin: base address
    - result.binary: assembled bytes
    - result._exports: set of exported symbol names (if set)
    - result._imports: set of imported symbol names (if set)
    - result._relocations: list of (offset, size, symbol_name)
    """
    obj = ObjectFile(
        name=os.path.splitext(os.path.basename(source_name))[0] if source_name else "",
        source=source_name,
        org=result.origin,
        size=len(result.binary),
        data=result.binary,
    )
    
    # Convert absolute addresses to offsets from org
    # Skip IMPORT symbols (they're external, not defined in this object)
    import_set = set(getattr(result, 'imports', []))
    for name, addr in result.symbols.items():
        if name in import_set:
            continue  # Don't store external symbols as local
        offset = addr - result.origin
        if offset >= 0:
            obj.symbols[name] = offset
    
    # Get exports/imports/relocations from result
    obj.exports = list(getattr(result, 'exports', []))
    obj.imports = list(getattr(result, 'imports', []))
    
    for reloc in getattr(result, 'relocations', []):
        if isinstance(reloc, tuple):
            offset, size, sym = reloc
            obj.relocations.append(Relocation(offset=offset, size=size, symbol=sym))
        elif isinstance(reloc, Relocation):
            obj.relocations.append(reloc)
    
    return obj
