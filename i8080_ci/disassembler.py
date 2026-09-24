"""I8080 CPU disassembler."""

# === Опкоды переходов для подсветки в трассировке ===
JUMP_OPCODES = {
    0xC3, 0xCA, 0xC2, 0xDA, 0xD2, 0xF2, 0xFA, 0xEA, 0xE2,  # JMP, JZ, JNZ, JC, JNC, JP, JM, JPE, JPO
    0xCD, 0xCC, 0xC4, 0xDC, 0xD4, 0xF4, 0xFC, 0xEC, 0xE4,  # CALL, CZ, CNZ, CC, CNC, CP, CM, CPE, CPO
    0xC9, 0xC8, 0xC0, 0xD8, 0xD0, 0xF0, 0xF8, 0xE8, 0xE0,  # RET, RZ, RNZ, RC, RNC, RP, RM, RPE, RPO
    0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF,        # RST 0-7
    0xCB, 0xD9, 0xDD, 0xED, 0xFD,                          # Пересекающиеся: JMP*/RET*/CALL*/JNK/JK
}



class I8080Disassembler:
    REGS = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
    ALUS = ['ADD', 'ADC', 'SUB', 'SBB', 'ANA', 'XRA', 'ORA', 'CMP']
    RP = ['B', 'D', 'H', 'SP']
    RP_PUSH = ['B', 'D', 'H', 'PSW']
    CC = ['NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M']

    def __init__(self, map_file=None, cpu_type="i8080"):
        self.cpu_type = cpu_type  # "i8080" или "i8085"
        self.table = self._generate_table()
        self._map = map_file  # MapFile or None
        self._map_dict = {}   # {address: name}
        if map_file:
            self._map_dict = map_file.to_dict()
        
    def set_cpu_type(self, cpu_type: str) -> None:
        """Установить тип процессора и перегенерировать таблицу опкодов."""
        if cpu_type != self.cpu_type:
            self.cpu_type = cpu_type
            self.table = self._generate_table()
        
    def _generate_table(self):
        t = {}
        t[0x00] = (1, "NOP"); t[0x76] = (1, "HLT")
        
        # LXI: 0x01, 0x11, 0x21, 0x31
        for i in range(4): t[0x01 + i*16] = (3, f"LXI {self.RP[i]},{{1:02X}}{{0:02X}}h")
        
        # DAD: 0x09, 0x19, 0x29, 0x39 ← ДОБАВЛЕНО
        for i in range(4): t[0x09 + i*16] = (1, f"DAD {self.RP[i]}")
        
        # INX: 0x03, 0x13, 0x23, 0x33
        for i in range(4): t[0x03 + i*16] = (1, f"INX {self.RP[i]}")
        
        # DCX: 0x0B, 0x1B, 0x2B, 0x3B
        for i in range(4): t[0x0B + i*16] = (1, f"DCX {self.RP[i]}")
        
        # INR: 0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x34, 0x3C
        for i in range(8): t[0x04 + i*8] = (1, f"INR {self.REGS[i]}")
        
        # DCR: 0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D
        for i in range(8): t[0x05 + i*8] = (1, f"DCR {self.REGS[i]}")
        
        # MVI: 0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E
        for i in range(8): t[0x06 + i*8] = (2, f"MVI {self.REGS[i]},{{0:02X}}h")
        
        t[0x02] = (1, "STAX B"); t[0x12] = (1, "STAX D")
        t[0x0A] = (1, "LDAX B"); t[0x1A] = (1, "LDAX D")
        t[0x22] = (3, "SHLD {1:02X}{0:02X}h"); t[0x2A] = (3, "LHLD {1:02X}{0:02X}h")
        t[0x32] = (3, "STA {1:02X}{0:02X}h"); t[0x3A] = (3, "LDA {1:02X}{0:02X}h")
        t[0x07] = (1, "RLC"); t[0x0F] = (1, "RRC"); t[0x17] = (1, "RAL"); t[0x1F] = (1, "RAR")
        t[0x27] = (1, "DAA"); t[0x2F] = (1, "CMA"); t[0x37] = (1, "STC"); t[0x3F] = (1, "CMC")
        t[0xE3] = (1, "XTHL"); t[0xE9] = (1, "PCHL"); t[0xF9] = (1, "SPHL")
        t[0xEB] = (1, "XCHG"); t[0xF3] = (1, "DI"); t[0xFB] = (1, "EI")
        t[0xDB] = (2, "IN {0:02X}h"); t[0xD3] = (2, "OUT {0:02X}h")
        
        for i in range(0x40, 0x80):
            if i not in t:
                dst = (i >> 3) & 7; src = i & 7
                t[i] = (1, f"MOV {self.REGS[dst]},{self.REGS[src]}")
                
        for i in range(0x80, 0xC0):
            alu = (i >> 3) & 7; src = i & 7
            t[i] = (1, f"{self.ALUS[alu]} {self.REGS[src]}")
            
        for i in range(8):
            t[0xC0 + i*8] = (1, f"R{self.CC[i]}")
            t[0xC2 + i*8] = (3, f"J{self.CC[i]} {{1:02X}}{{0:02X}}h")
            t[0xC4 + i*8] = (3, f"C{self.CC[i]} {{1:02X}}{{0:02X}}h")
            
        t[0xC3] = (3, "JMP {1:02X}{0:02X}h")
        t[0xCD] = (3, "CALL {1:02X}{0:02X}h")
        t[0xC9] = (1, "RET")
        
        for i in range(4):
            t[0xC1 + i*16] = (1, f"POP {self.RP_PUSH[i]}")
            t[0xC5 + i*16] = (1, f"PUSH {self.RP_PUSH[i]}")
            
        for i in range(8):
            t[0xC6 + i*8] = (2, f"{self.ALUS[i]} {{0:02X}}h")
            
        t[0xC7] = (1, "RST 0"); t[0xCF] = (1, "RST 1"); t[0xD7] = (1, "RST 2")
        t[0xDF] = (1, "RST 3"); t[0xE7] = (1, "RST 4"); t[0xEF] = (1, "RST 5")
        t[0xF7] = (1, "RST 6"); t[0xFF] = (1, "RST 7")
        
        # === ПЕРЕСЕКАЮЩИЕСЯ ОПКОДЫ 8080/8085 ===
        if self.cpu_type == "i8085":
            # 8085: 2 задокументированные (SIM, RIM) + недокументированные
            t[0x20] = (1, "RIM")
            t[0x30] = (1, "SIM")
            t[0x08] = (1, "DSUB")
            t[0x10] = (1, "ARHL")
            t[0x18] = (1, "RDEL")
            t[0x28] = (2, "LDHI {0:02X}h")
            t[0x38] = (2, "LDSI {0:02X}h")
            t[0xCB] = (1, "RSTV")
            t[0xD9] = (1, "SHLX")
            t[0xDD] = (3, "JNK {1:02X}{0:02X}h")
            t[0xED] = (1, "LHLX")
            t[0xFD] = (3, "JK {1:02X}{0:02X}h")
        else:
            # 8080: недокументированные
            for op in [0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38]:
                t[op] = (1, "NOP*")
            t[0xCB] = (3, "JMP* {1:02X}{0:02X}h")
            t[0xD9] = (1, "RET*")
            t[0xDD] = (3, "CALL* {1:02X}{0:02X}h")
            t[0xED] = (3, "CALL* {1:02X}{0:02X}h")
            t[0xFD] = (3, "CALL* {1:02X}{0:02X}h")
        return t

    def get_target(self, op, args):
        if op in [0xC3, 0xCD] or \
           op in [0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA] or \
           op in [0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC]:
            if len(args) >= 2:
                return (args[1] << 8) | args[0]
        elif op in [0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF]:
            return ((op - 0xC7) // 8) * 8
        # Пересекающиеся опкоды с целевым адресом
        elif self.cpu_type == "i8080" and op in [0xCB, 0xDD, 0xED, 0xFD]:
            if len(args) >= 2:
                return (args[1] << 8) | args[0]
        elif self.cpu_type == "i8085" and op in [0xDD, 0xFD]:
            if len(args) >= 2:
                return (args[1] << 8) | args[0]
        return None

    def get_mnemonic(self, byte_val):
        """Возвращает мнемонику для одного байта (для подсказок)"""
        if byte_val in self.table:
            size, fmt = self.table[byte_val]
            # Извлекаем мнемонику из формата (первое слово)
            parts = fmt.split()
            if parts:
                mnemonic = parts[0]
                # Для команд с аргументами показываем только мнемонику
                if "{" in fmt:
                    return f"{mnemonic} ..."
                return mnemonic
        return f"DB {byte_val:02X}h"

    def set_map(self, map_file):
        """Set map file for symbol resolution."""
        self._map = map_file
        self._map_dict = map_file.to_dict() if map_file else {}
    
    def _resolve_symbol(self, addr):
        """Resolve address to symbol name from map file."""
        if not self._map_dict:
            return None
        if addr in self._map_dict:
            return self._map_dict[addr]
        return None
    
    def disassemble(self, mem_dict, start_addr, length):
        lines = []
        i = 0
        while i < length:
            addr = start_addr + i
            if addr not in mem_dict:
                i += 1; continue
            op = mem_dict[addr]
            if op not in self.table:
                sym = self._resolve_symbol(addr)
                prefix = f"{sym}: " if sym else ""
                lines.append((addr, 1, f"{prefix}DB {op:02X}h", "*", None))
                i += 1; continue
            
            size, fmt = self.table[op]
            args = [mem_dict.get(addr+1+k, 0) for k in range(size-1)]
            try:
                asm = fmt.format(*args) if args else fmt
            except (ValueError, IndexError, KeyError):
                asm = fmt
            
            # Resolve symbol at current address
            sym = self._resolve_symbol(addr)
            if sym:
                asm = f"{sym}: {asm}"
            
            # Resolve target address to symbol
            target = self.get_target(op, args)
            if target is not None:
                target_sym = self._resolve_symbol(target)
                if target_sym:
                    # Replace hex address with symbol name in the asm string
                    hex_str = f"{target:04X}h"
                    if hex_str in asm:
                        asm = asm.replace(hex_str, target_sym)
            
            undoc = "*" if "NOP*" in asm or "RET*" in asm or "CALL*" in asm else ""
            
            lines.append((addr, size, asm, undoc, target))
            i += size
        return lines

# ==================== КАСТОМНЫЙ ВИДЖЕТ ДИЗАССЕМБЛЕРА СО СТРЕЛКАМИ ====================

