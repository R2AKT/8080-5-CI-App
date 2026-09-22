"""
Map file generation and parsing for i8080-5 CI.

Map file format (text):
; i8080-5 CI map file v1
; source: main.asm
; date: 2026-09-22 08:45:00
; org: 0x0100
; size: 256
; symbols: 12

ADDRESS   SIZE  TYPE    NAME
0000      0003  CODE    boot_start
0008      0003  CODE    rst1_handler
0100      0002  DATA    my_var
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MapEntry:
    """One entry in the map file."""
    address: int
    size: int
    entry_type: str  # "CODE" or "DATA"
    name: str


@dataclass
class MapFile:
    """Parsed map file."""
    source: str = ""
    date: str = ""
    org: int = 0
    size: int = 0
    entries: list = field(default_factory=list)
    
    def get_symbol_at(self, addr: int) -> Optional[str]:
        """Find symbol name at or before the given address."""
        best = None
        best_addr = -1
        for e in self.entries:
            if e.address <= addr and e.address > best_addr:
                best = e.name
                best_addr = e.address
        return best
    
    def get_symbol_exact(self, addr: int) -> Optional[str]:
        """Find symbol name exactly at the given address."""
        for e in self.entries:
            if e.address == addr:
                return e.name
        return None
    
    def to_dict(self) -> dict:
        """Convert to {address: name} dict for quick lookup."""
        return {e.address: e.name for e in self.entries}


def generate_map(result, source_name: str = "", date_str: str = "") -> str:
    """Generate map file text from AsmResult.
    
    Args:
        result: AsmResult with symbols, listing, origin, binary
        source_name: name of the source file
        date_str: date string (auto-generated if empty)
    
    Returns:
        Map file text content
    """
    import datetime
    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    lines = []
    lines.append("; i8080-5 CI map file v1")
    lines.append(f"; source: {source_name or '<input>'}")
    lines.append(f"; date: {date_str}")
    lines.append(f"; org: 0x{result.origin:04X}")
    lines.append(f"; size: {len(result.binary)}")
    lines.append(f"; symbols: {len(result.symbols)}")
    lines.append("")
    lines.append("ADDRESS   SIZE  TYPE    NAME")
    
    # Build entries from symbols, sorted by address
    # Try to determine size from listing or consecutive symbols
    sorted_syms = sorted(result.symbols.items(), key=lambda x: x[1])
    
    for i, (name, addr) in enumerate(sorted_syms):
        # Determine size: distance to next symbol, or 1 if last
        if i + 1 < len(sorted_syms):
            size = sorted_syms[i + 1][1] - addr
        else:
            # Last symbol: size is from addr to end of binary
            end = result.origin + len(result.binary)
            size = max(1, end - addr)
        
        # Determine type: CODE if in listing with instructions, DATA otherwise
        entry_type = "CODE"
        # Check if this address has data directives in listing
        for (laddr, lbytes, lsrc) in result.listing:
            if laddr == addr:
                src_upper = lsrc.strip().upper()
                if any(src_upper.startswith(d) for d in ('DB', 'DW', 'DS', '.DB', '.DW', '.DS')):
                    entry_type = "DATA"
                break
        
        lines.append(f"{addr:04X}      {size:04X}  {entry_type:<6}  {name}")
    
    lines.append("")
    return "\n".join(lines)


def parse_map(text: str) -> MapFile:
    """Parse map file text into MapFile object."""
    mf = MapFile()
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith(';'):
            # Comment/metadata
            if line.startswith('; source:'):
                mf.source = line[9:].strip()
            elif line.startswith('; date:'):
                mf.date = line[7:].strip()
            elif line.startswith('; org:'):
                mf.org = int(line[6:].strip(), 16)
            elif line.startswith('; size:'):
                mf.size = int(line[7:].strip())
            continue
        if line.startswith('ADDRESS'):
            continue  # Header
        
        # Data line: ADDRESS SIZE TYPE NAME
        m = re.match(r'^([0-9A-Fa-f]{4})\s+([0-9A-Fa-f]{4})\s+(\w+)\s+(.+)$', line)
        if m:
            addr = int(m.group(1), 16)
            size = int(m.group(2), 16)
            etype = m.group(3).upper()
            name = m.group(4).strip()
            mf.entries.append(MapEntry(addr, size, etype, name))
    
    return mf


def load_map_file(path: str) -> MapFile:
    """Load and parse a map file from disk."""
    with open(path, 'r', encoding='utf-8') as f:
        return parse_map(f.read())


def save_map_file(path: str, content: str):
    """Save map file text to disk."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
