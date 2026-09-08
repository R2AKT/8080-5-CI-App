"""SLIP protocol constants and encoding/decoding."""

# --- Константы SLIP и Команд ---
_FEND = 0xC0; _FESC = 0xDB; _TFEND = 0xDC; _TFESC = 0xDD
CMD_NOP = 0x00
CMD_HOLD = 0x01; CMD_UNHOLD = 0x02
CMD_MEM_READ_BYTE = 0x10; CMD_MEM_READ_BLOCK = 0x11
CMD_MEM_WRITE_BYTE = 0x12; CMD_MEM_WRITE_BLOCK = 0x13
CMD_IO_READ_BYTE = 0x20; CMD_IO_READ_BLOCK = 0x21
CMD_IO_WRITE_BYTE = 0x22; CMD_IO_WRITE_BLOCK = 0x23
CMD_EEPROM_WRITE_BYTE = 0x32
CMD_EEPROM_WRITE_BLOCK = 0x33
ACK_NOP = 0x00
ACK_HOLD_WAIT_LOW = 0x00          # ожидание HLDA low
ACK_HOLD_WAIT_HIGH = 0x01         # ожидание HLDA high
ACK_HOLD_ACTIVE = 0x03
ACK_WAIT_UNHOLD = 0xF1            # ожидание освобождения
ACK_UNHOLD = 0xF2 
ACK_MEM_READ_BYTE = 0x10; ACK_MEM_READ_BLOCK = 0x11
ACK_MEM_WRITE_BYTE = 0x12; ACK_MEM_WRITE_BLOCK = 0x13
ACK_IO_READ_BYTE = 0x20; ACK_IO_READ_BLOCK = 0x21
ACK_IO_WRITE_BYTE = 0x22; ACK_IO_WRITE_BLOCK = 0x23
ACK_EEPROM_READ_BYTE = 0x30
ACK_EEPROM_READ_BLOCK = 0x31
ACK_EEPROM_WRITE_BYTE = 0x32
ACK_EEPROM_WRITE_BLOCK = 0x33
ACK_ERROR = 0xFF
CMD_GET_SIZE_SETUP = 0x40
ACK_GET_SIZE_SETUP = 0x40
# ==================== ПРОТОКОЛ SLIP ====================


class SlipProtocol:
    @staticmethod
    def encode(data: bytes) -> bytes:
        encoded = bytearray([_FEND])
        for b in data:
            if b == _FEND: encoded.extend([_FESC, _TFEND])
            elif b == _FESC: encoded.extend([_FESC, _TFESC])
            else: encoded.append(b)
        encoded.append(_FEND)
        return bytes(encoded)

    @staticmethod
    def decode(data: bytes) -> bytes:
        decoded = bytearray()
        i = 0
        while i < len(data):
            if data[i] == _FESC:
                if i + 1 < len(data):
                    if data[i+1] == _TFEND: decoded.append(_FEND)
                    elif data[i+1] == _TFESC: decoded.append(_FESC)
                    i += 2
                else: break
            else:
                decoded.append(data[i])
                i += 1
        return bytes(decoded)

# ==================== INTEL HEX PARSER ====================

