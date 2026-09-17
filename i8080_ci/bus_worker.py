"""Background bus worker for serial communication."""
import serial
from PySide6.QtCore import QObject, Signal
from .slip import (SlipProtocol, _FEND, _FESC, _TFEND, _TFESC,
                   CMD_NOP, CMD_HOLD, CMD_UNHOLD,
                   CMD_MEM_READ_BYTE, CMD_MEM_READ_BLOCK,
                   CMD_MEM_WRITE_BYTE, CMD_MEM_WRITE_BLOCK,
                   CMD_IO_READ_BYTE, CMD_IO_READ_BLOCK,
                   CMD_IO_WRITE_BYTE, CMD_IO_WRITE_BLOCK,
                   CMD_EEPROM_WRITE_BYTE, CMD_EEPROM_WRITE_BLOCK,
                   CMD_GET_SIZE_SETUP,
                   ACK_NOP, ACK_HOLD_WAIT_LOW, ACK_HOLD_WAIT_HIGH,
                   ACK_HOLD_ACTIVE, ACK_WAIT_UNHOLD, ACK_UNHOLD,
                   ACK_MEM_READ_BYTE, ACK_MEM_READ_BLOCK,
                   ACK_MEM_WRITE_BYTE, ACK_MEM_WRITE_BLOCK,
                   ACK_IO_READ_BYTE, ACK_IO_READ_BLOCK,
                   ACK_IO_WRITE_BYTE, ACK_IO_WRITE_BLOCK,
                   ACK_EEPROM_READ_BYTE, ACK_EEPROM_READ_BLOCK,
                   ACK_EEPROM_WRITE_BYTE, ACK_EEPROM_WRITE_BLOCK,
                   ACK_ERROR, ACK_GET_SIZE_SETUP)
from common.i18n import LANGS

class BusWorker(QObject):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal(object)
    
    def __init__(self, serial_port, task, params, lang="en", max_block_size=128):
        super().__init__()
        self.ser = serial_port
        self.task = task
        self.params = params
        self.is_running = True
        self.lang = lang
        self.max_block_size = max_block_size

    def stop(self):
        self.is_running = False

    def tr(self, key):
        return LANGS.get(self.lang, LANGS["en"]).get(key, key)

    def run(self):
        if self.task == "read_block":
            self.do_read_block()
        elif self.task == "test_mem":
            self.do_test_mem()
        elif self.task == "write_block":
            self.do_write_block()
        elif self.task == "run_io_sequence":
            self.do_run_io_sequence()
        elif self.task == "read_io_block":
            self.do_read_io_block()
        elif self.task == "write_io_block":
            self.do_write_io_block()

    def send_and_recv(self, payload, timeout=2.0):
        try:
            self.ser.write(SlipProtocol.encode(payload))
            self.ser.flush()
        except serial.SerialException as e:
            self.log.emit(f"{self.tr('err_write_port')} {e}")
            return None
            
        buffer = bytearray()
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running: return None
            try:
                if self.ser.in_waiting:
                    buffer.extend(self.ser.read(self.ser.in_waiting))
                    if _FEND in buffer:
                        # Пропускаем начальные FEND (маркеры начала пакета)
                        start_idx = 0
                        while start_idx < len(buffer) and buffer[start_idx] == _FEND:
                            start_idx += 1
                        if start_idx < len(buffer):
                            # Ищем конечный FEND после данных
                            try:
                                end_idx = buffer.index(_FEND, start_idx)
                                raw = buffer[start_idx:end_idx]
                                if raw:
                                    self.ser.reset_input_buffer()
                                    return SlipProtocol.decode(raw)
                            except ValueError:
                                pass  # Конечный FEND ещё не пришёл, ждём
            except serial.SerialException as e:
                self.log.emit(f"{self.tr('err_read_port')} {e}")
                return None
            time.sleep(0.01)
        return None

    def do_read_block(self):
        addr, size = self.params
        self.log.emit(f"{self.tr('read_block_msg')} 0x{addr:04X} ({size})")
        cmd = bytes([CMD_MEM_READ_BLOCK, size & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF])
        resp = self.send_and_recv(cmd)
        mem = {}
        if resp and resp[0] == ACK_MEM_READ_BLOCK:
            for i in range(resp[1]):
                if 3 + i < len(resp):
                    mem[addr + i] = resp[3 + i]
            self.log.emit(f"{self.tr('read_ok')} {len(mem)} {self.tr('bytes')}")
        else:
            self.log.emit(self.tr('read_err'))
        self.finished.emit(mem)

    def do_write_block(self):
        mem_dict, start_addr = self.params
        self.log.emit(f"{self.tr('write_block')} 0x{start_addr:04X}...")
        addrs = sorted(mem_dict.keys())
        written = 0
        for i in range(0, len(addrs), self.max_block_size):
            if not self.is_running: break
            chunk_addrs = addrs[i:i+self.max_block_size]
            chunk_data = [mem_dict[a] for a in chunk_addrs]
            c_addr = chunk_addrs[0]
            c_size = len(chunk_data)
            
            cmd = bytearray([CMD_MEM_WRITE_BLOCK, c_size, (c_addr >> 8) & 0xFF, c_addr & 0xFF])
            cmd.extend(chunk_data)
            resp = self.send_and_recv(bytes(cmd))
            if not resp or resp[0] != ACK_MEM_WRITE_BLOCK:
                self.log.emit(f"{self.tr('write_err')} 0x{c_addr:04X}")
                break
            written += c_size
            self.progress.emit(int((i + c_size) * 100 / len(addrs)))
        self.log.emit(f"{self.tr('write_done')} ({written} {self.tr('bytes')}).")
        self.finished.emit({})

    def do_read_io_block(self):
        addr, size = self.params
        self.log.emit(f"{self.tr('io_read_block')} 0x{addr:04X} ({size})")
        cmd = bytes([CMD_IO_READ_BLOCK, size & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF])
        resp = self.send_and_recv(cmd)
        mem = {}
        if resp and resp[0] == ACK_IO_READ_BLOCK:
            for i in range(resp[1]):
                if 3 + i < len(resp):
                    mem[addr + i] = resp[3 + i]
            self.log.emit(f"{self.tr('io_read_ok')} {len(mem)} {self.tr('io_bytes')}")
        else:
            self.log.emit(self.tr('io_read_err'))
        self.finished.emit(mem)

    def do_write_io_block(self):
        mem_dict, start_addr = self.params
        self.log.emit(f"{self.tr('io_write_block')} 0x{start_addr:04X}...")
        addrs = sorted(mem_dict.keys())
        written = 0
        for i in range(0, len(addrs), self.max_block_size):
            if not self.is_running: break
            chunk_addrs = addrs[i:i+self.max_block_size]
            chunk_data = [mem_dict[a] for a in chunk_addrs]
            c_addr = chunk_addrs[0]
            c_size = len(chunk_data)
            
            cmd = bytearray([CMD_IO_WRITE_BLOCK, c_size, (c_addr >> 8) & 0xFF, c_addr & 0xFF])
            cmd.extend(chunk_data)
            resp = self.send_and_recv(bytes(cmd))
            if not resp or resp[0] != ACK_IO_WRITE_BLOCK:
                self.log.emit(f"{self.tr('io_write_err')} 0x{c_addr:04X}")
                break
            written += c_size
            self.progress.emit(int((i + c_size) * 100 / len(addrs)))
        self.log.emit(f"{self.tr('io_write_done')} ({written} {self.tr('bytes')}).")
        self.finished.emit({})

    def do_test_mem(self):
        start, end, pattern_name = self.params
        size = end - start + 1
        self.log.emit(f"{self.tr('test_mem')} 0x{start:04X}-0x{end:04X} {self.tr('pattern')} '{pattern_name}'")
        
        errors = 0
        chunk_size = self.max_block_size
        
        def get_pattern(offset, length):
            if pattern_name == "Zero": return [0x00] * length
            elif pattern_name == "One": return [0xFF] * length
            elif pattern_name == "Checker": return [0x55 if (offset + i) % 2 == 0 else 0xAA for i in range(length)]
            elif pattern_name == "Addr": return [(start + offset + i) & 0xFF for i in range(length)]
            return [0x00] * length

        for i in range(0, size, chunk_size):
            if not self.is_running: break
            c_size = min(chunk_size, size - i)
            c_addr = start + i
            data = get_pattern(i, c_size)
            
            cmd = bytearray([CMD_MEM_WRITE_BLOCK, c_size, (c_addr >> 8) & 0xFF, c_addr & 0xFF])
            cmd.extend(data)
            resp = self.send_and_recv(bytes(cmd))
            if not resp or resp[0] != ACK_MEM_WRITE_BLOCK:
                self.log.emit(f"{self.tr('write_fail')} 0x{c_addr:04X}")
                break
                
            cmd_r = bytes([CMD_MEM_READ_BLOCK, c_size, (c_addr >> 8) & 0xFF, c_addr & 0xFF])
            resp_r = self.send_and_recv(cmd_r)
            if resp_r and resp_r[0] == ACK_MEM_READ_BLOCK:
                for j in range(c_size):
                    if 3 + j < len(resp_r) and resp_r[3+j] != data[j]:
                        errors += 1
                        self.log.emit(f"{self.tr('error')}: Addr 0x{c_addr+j:04X} {self.tr('expected')} 0x{data[j]:02X}, {self.tr('got')} 0x{resp_r[3+j]:02X}")
            else:
                self.log.emit(f"{self.tr('read_fail')} 0x{c_addr:04X}")
                break
                
            self.progress.emit(int((i + c_size) * 100 / size))
            
        self.log.emit(f"{self.tr('test_done')} {self.tr('errors')}: {errors}")
        self.finished.emit({"errors": errors})

    def do_run_io_sequence(self):
        sequence = self.params['sequence']
        self.log.emit(self.tr('io_seq_start'))
        for line in sequence:
            if not self.is_running: break
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'):
                continue
                
            parts = line.split()
            cmd = parts[0].upper()
            
            try:
                if cmd == 'W' and len(parts) == 3:
                    port = int(parts[1], 16)
                    data = int(parts[2], 16)
                    payload = bytes([CMD_IO_WRITE_BYTE, (port >> 8) & 0xFF, port & 0xFF, data])
                    resp = self.send_and_recv(payload, timeout=1.0)
                    if not resp or resp[0] != ACK_IO_WRITE_BYTE:
                        self.log.emit(f"  [{self.tr('error')}] {self.tr('write_io')} 0x{port:02X}")
                    else:
                        self.log.emit(f"  [{self.tr('ok')}] W IO 0x{port:02X} = 0x{data:02X}")
                        
                elif cmd == 'R' and len(parts) == 2:
                    port = int(parts[1], 16)
                    payload = bytes([CMD_IO_READ_BYTE, (port >> 8) & 0xFF, port & 0xFF])
                    resp = self.send_and_recv(payload, timeout=1.0)
                    if resp and resp[0] == ACK_IO_READ_BYTE:
                        val = resp[3]
                        self.log.emit(f"  [{self.tr('ok')}] R IO 0x{port:02X} = 0x{val:02X}")
                    else:
                        self.log.emit(f"  [{self.tr('error')}] {self.tr('read_io')} 0x{port:02X}")
                        
                elif cmd == 'D' and len(parts) == 2:
                    ms = int(parts[1])
                    time.sleep(ms / 1000.0)
                    self.log.emit(f"  [{self.tr('delay')}] {ms} ms")
            except ValueError:
                self.log.emit(f"  [{self.tr('error')}] {self.tr('err_seq_fmt')} {line}")
                
        self.log.emit(self.tr('io_seq_done'))
        self.finished.emit({})

# ==================== WATCH ОКНО ====================

