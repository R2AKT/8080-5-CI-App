"""Intel HEX format parsing and generation."""

class IntelHex:
    @staticmethod
    def parse(text):
        mem = {}
        base_addr = 0
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line.startswith(':') or len(line) < 11: continue
            try:
                length = int(line[1:3], 16)
                addr = int(line[3:7], 16)
                rec_type = int(line[7:9], 16)
                data = bytes.fromhex(line[9:-2])
                if rec_type == 0x00:
                    for i in range(length):
                        mem[base_addr + addr + i] = data[i]
                elif rec_type == 0x02:
                    base_addr = int.from_bytes(data, 'big') << 4
                elif rec_type == 0x04:
                    base_addr = int.from_bytes(data, 'big') << 16
                elif rec_type == 0x01: break
            except ValueError: continue
        return mem

    @staticmethod
    def generate(mem_dict):
        lines = []
        sorted_addrs = sorted(mem_dict.keys())
        i = 0
        while i < len(sorted_addrs):
            addr = sorted_addrs[i]
            chunk_len = min(16, len(sorted_addrs) - i)
            actual_len = 0
            for j in range(chunk_len):
                if i + j < len(sorted_addrs) and sorted_addrs[i+j] == addr + j:
                    actual_len += 1
                else: break
            
            data = [mem_dict[addr + k] for k in range(actual_len)]
            hex_data = "".join(f"{b:02X}" for b in data)
            checksum = (actual_len + (addr >> 8) + (addr & 0xFF) + 0x00 + sum(data)) & 0xFF
            checksum = (~checksum + 1) & 0xFF
            lines.append(f":{actual_len:02X}{addr:04X}00{hex_data}{checksum:02X}")
            i += actual_len
        lines.append(":00000001FF")
        return "\n".join(lines)

# ==================== I8080 DISASSEMBLER ====================

