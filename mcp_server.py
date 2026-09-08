"""
Встроенный MCP Server для i8080-5 Master Controller
Использует FastMCP API (стабильный и простой)
Транспорт: SSE (Server-Sent Events)
"""
import warnings

# Подавляем предупреждение pydantic_settings о lifespan
try:
    from pydantic_settings.sources.utils import IncompleteFieldDefinitionWarning
    warnings.filterwarnings("ignore", category=IncompleteFieldDefinitionWarning)
except ImportError:
    # Если класс недоступен, подавляем по сообщению
    warnings.filterwarnings("ignore", message=".*lifespan.*")
	
import asyncio
import json
import threading
from mcp.server.fastmcp import FastMCP


class MCPServerManager:
    """Управляет встроенным MCP Server"""
    
    def __init__(self, main_window: 'MainWindow', host: str = "127.0.0.1", port: int = 8000) -> None:
        self.mw = main_window
        self.host = host
        self.port = port
        self.thread = None
        self.running = False
        self.mcp = None
        self._stop_event = threading.Event()
        
    def start(self) -> None:
        """Запускает MCP Server в отдельном потоке"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        self.mw.log(f"MCP Server started on http://{self.host}:{self.port}/sse")
        
    def stop(self) -> None:
        """Останавливает MCP Server."""
        if not self.running:
            return
        self.running = False
        self._stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=5.0)
            self.thread = None
        self.mw.log("MCP Server stopped")
        
    def _run_server(self) -> None:
        """Запускает MCP Server в отдельном потоке."""
        try:
            self.mcp = self._create_server()
            # Запускаем SSE сервер (bloking; остановка через daemon-поток)
            self.mcp.run(transport="sse")
        except Exception as e:
            if self.running:  # Не логируем при штатной остановке
                self.mw.log(f"MCP Server error: {e}")
            self.running = False
            
    def _create_server(self) -> 'FastMCP':
        """Создаёт и настраивает FastMCP Server"""
        # Создаём FastMCP с настройками хоста и порта
        mcp = FastMCP(
            "i8080-master-controller",
            host=self.host,
            port=self.port
        )
        
        # =============================================
        # TOOLS: Управление эмулятором i8080
        # =============================================
        
        def emu_reset() -> str:
            """Сброс эмулятора i8080. Все регистры обнуляются, PC=0x0000, SP=0xFFFF."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                self.mw.emulator.reset()
                self.mw.safe_call(self.mw.update_emulator_ui)
                self.mw.safe_call(self.mw.update_emu_disasm_view)
                return "Эмулятор сброшен. PC=0x0000"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_step_into() -> str:
            """Выполнить одну инструкцию эмулятора (Step Into). Заходит в CALL."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                if self.mw.emulator.halted:
                    return "CPU halted. Use emu_reset first."
                self.mw.emulator.step_into()
                self.mw.safe_call(self.mw.update_emulator_ui)
                self.mw.safe_call(self.mw.update_emu_disasm_view)
                return f"Step Into. PC=0x{self.mw.emulator.pc:04X}, A=0x{self.mw.emulator.a:02X}"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_step_over() -> str:
            """Выполнить одну инструкцию эмулятора (Step Over). CALL выполняется целиком."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                if self.mw.emulator.halted:
                    return "CPU halted. Use emu_reset first."
                self.mw.emulator.step_over()
                self.mw.safe_call(self.mw.update_emulator_ui)
                self.mw.safe_call(self.mw.update_emu_disasm_view)
                return f"Step Over. PC=0x{self.mw.emulator.pc:04X}, A=0x{self.mw.emulator.a:02X}"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_run(max_instructions: int = 10000) -> str:
            """Запустить эмулятор до точки останова, HLT или max_instructions."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                if self.mw.emulator.halted:
                    return "CPU halted. Use emu_reset first."
                steps = self.mw.emulator.run(max_instructions)
                self.mw.safe_call(self.mw.update_emulator_ui)
                self.mw.safe_call(self.mw.update_emu_disasm_view)
                status = "halted" if self.mw.emulator.halted else "stopped"
                return f"Executed {steps} instructions. Status: {status}. PC=0x{self.mw.emulator.pc:04X}"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_run_to(addr: int) -> str:
            """Выполнять до указанного адреса (Run to Cursor)."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                if self.mw.emulator.halted:
                    return "CPU halted. Use emu_reset first."
                steps = self.mw.emulator.run_to(addr)
                self.mw.safe_call(self.mw.update_emulator_ui)
                self.mw.safe_call(self.mw.update_emu_disasm_view)
                return f"Executed {steps} instructions to 0x{addr:04X}. PC=0x{self.mw.emulator.pc:04X}"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_stop() -> str:
            """Остановить выполнение эмулятора."""
            try:
                if hasattr(self.mw, 'emulator'):
                    self.mw.emulator.stop()
                    self.mw.safe_call(self.mw.update_emulator_ui)
                    return "Emulator stopped"
                return "Emulator not initialized"
            except Exception as e:
                return f"Error: {e}"
        
        # =============================================
        # TOOLS: Состояние эмулятора
        # =============================================
        
        def emu_get_state() -> dict:
            """Получить полное состояние эмулятора: регистры, флаги, PC, SP, такты."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return {"error": "Emulator not initialized"}
                state = self.mw.emulator.get_state()
                state['flags'] = {k: int(v) for k, v in state['flags'].items()}
                state['halted'] = int(state['halted'])
                state['running'] = int(state['running'])
                state['interrupts'] = int(state['interrupts'])
                return state
            except Exception as e:
                return {"error": str(e)}
        
        def emu_get_reg(reg: str) -> str:
            """Прочитать регистр эмулятора. reg: A,B,C,D,E,H,L,BC,DE,HL,SP,PC"""
            try:
                api = self._get_api()
                val = api.emu_get_reg(reg)
                return f"{reg.upper()} = 0x{val:X} ({val})"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_set_reg(reg: str, val: int) -> str:
            """Установить регистр эмулятора. reg: A,B,C,D,E,H,L,BC,DE,HL,SP,PC"""
            try:
                api = self._get_api()
                result = api.emu_set_reg(reg, val)
                self.mw.safe_call(self.mw.update_emulator_ui)
                self.mw.safe_call(self.mw.update_emu_disasm_view)
                return result
            except Exception as e:
                return f"Error: {e}"
        
        def emu_get_psw() -> str:
            """Прочитать слово состояния процессора (PSW: A + флаги)."""
            try:
                api = self._get_api()
                val = api.emu_get_psw()
                return f"PSW = 0x{val:04X}"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_set_psw(val: int) -> str:
            """Установить слово состояния процессора (PSW: A + флаги)."""
            try:
                api = self._get_api()
                result = api.emu_set_psw(val)
                self.mw.safe_call(self.mw.update_emulator_ui)
                return result
            except Exception as e:
                return f"Error: {e}"
        
        def emu_get_flags() -> dict:
            """Прочитать флаги процессора: S, Z, AC, P, CY."""
            try:
                api = self._get_api()
                flags = api.emu_get_flags()
                return {k: int(v) for k, v in flags.items()}
            except Exception as e:
                return {"error": str(e)}
        
        def emu_set_flag(flag: str, val: bool) -> str:
            """Установить флаг процессора. flag: S,Z,AC,P,CY"""
            try:
                api = self._get_api()
                result = api.emu_set_flag(flag, val)
                self.mw.safe_call(self.mw.update_emulator_ui)
                return result
            except Exception as e:
                return f"Error: {e}"
        
        # =============================================
        # TOOLS: Точки останова
        # =============================================
        
        def emu_add_breakpoint(addr: int) -> str:
            """Добавить точку останова по адресу."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                self.mw.emulator.add_breakpoint(addr)
                if hasattr(self.mw, 'sync_breakpoints'):
                    self.mw.safe_call(self.mw.sync_breakpoints)
                return f"Breakpoint added at 0x{addr:04X}"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_remove_breakpoint(addr: int) -> str:
            """Удалить точку останова по адресу."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                self.mw.emulator.remove_breakpoint(addr)
                if hasattr(self.mw, 'sync_breakpoints'):
                    self.mw.safe_call(self.mw.sync_breakpoints)
                return f"Breakpoint removed at 0x{addr:04X}"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_list_breakpoints() -> list:
            """Список всех точек останова с условиями и статистикой."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return []
                
                result = []
                for addr in sorted(self.mw.emulator.breakpoints):
                    condition = self.mw.emulator.get_bp_condition(addr)
                    enabled = self.mw.emulator.bp_enabled.get(addr, True)
                    hit_count = self.mw.emulator.bp_hit_count.get(addr, 0)
                    
                    entry = f"0x{addr:04X}"
                    if condition:
                        entry += f" [{condition}]"
                    if not enabled:
                        entry += " (disabled)"
                    entry += f" ×{hit_count}"
                    
                    result.append(entry)
                
                return result if result else ["No breakpoints set"]
            except Exception as e:
                return [f"Error: {e}"]
        
        def emu_clear_breakpoints() -> str:
            """Удалить все точки останова, условия и статистику."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                self.mw.emulator.clear_all_breakpoints()
                if hasattr(self.mw, 'sync_breakpoints'):
                    self.mw.safe_call(self.mw.sync_breakpoints)
                return "All breakpoints, conditions and statistics cleared"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_add_conditional_breakpoint(addr: int, condition: str) -> str:
            """Добавить условную точку останова.
            
            Примеры условий:
            - "A == 0x55" — остановиться когда A станет 0x55
            - "HL > 0x1000" — когда HL превысит 0x1000
            - "mem[0x0100] == 0xFF" — когда ячейка памяти станет FF
            - "Z == 1" — когда флаг Zero установлен
            - "cycles > 10000" — после 10000 тактов
            
            Доступные переменные: A,B,C,D,E,H,L,BC,DE,HL,SP,PC,
            флаги S,Z,AC,P,CY, mem[addr], io[port], cycles
            """
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                
                # Валидация синтаксиса условия
                if condition.strip():
                    try:
                        compile(condition, '<bp_condition>', 'eval')
                    except SyntaxError as e:
                        return f"Syntax error in condition: {e}"
                
                self.mw.emulator.add_breakpoint(addr)
                if condition.strip():
                    self.mw.emulator.set_bp_condition(addr, condition)
                
                if hasattr(self.mw, 'sync_breakpoints'):
                    self.mw.safe_call(self.mw.sync_breakpoints)
                
                cond_text = f" with condition '{condition}'" if condition.strip() else ""
                return f"Breakpoint added at 0x{addr:04X}{cond_text}"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_set_bp_condition(addr: int, condition: str) -> str:
            """Установить/изменить условие для существующей точки останова.
            Пустое условие делает BP обычной."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                
                if addr not in self.mw.emulator.breakpoints:
                    return f"No breakpoint at 0x{addr:04X}. Add one first."
                
                # Валидация синтаксиса
                if condition.strip():
                    try:
                        compile(condition, '<bp_condition>', 'eval')
                    except SyntaxError as e:
                        return f"Syntax error in condition: {e}"
                
                self.mw.emulator.set_bp_condition(addr, condition)
                
                if hasattr(self.mw, 'sync_breakpoints'):
                    self.mw.safe_call(self.mw.sync_breakpoints)
                
                if condition.strip():
                    return f"Condition set for BP 0x{addr:04X}: '{condition}'"
                else:
                    return f"Condition cleared for BP 0x{addr:04X} (now unconditional)"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_toggle_bp_enabled(addr: int) -> str:
            """Включить/выключить точку останова без удаления."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return "Emulator not initialized"
                
                if addr not in self.mw.emulator.breakpoints:
                    return f"No breakpoint at 0x{addr:04X}"
                
                self.mw.emulator.toggle_bp_enabled(addr)
                enabled = self.mw.emulator.bp_enabled.get(addr, True)
                
                if hasattr(self.mw, 'sync_breakpoints'):
                    self.mw.safe_call(self.mw.sync_breakpoints)
                
                state = "enabled" if enabled else "disabled"
                return f"Breakpoint 0x{addr:04X} {state}"
            except Exception as e:
                return f"Error: {e}"
        
        def emu_get_bp_info(addr: int) -> dict:
            """Получить полную информацию о точке останова."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return {"error": "Emulator not initialized"}
                
                if addr not in self.mw.emulator.breakpoints:
                    return {"error": f"No breakpoint at 0x{addr:04X}"}
                
                return {
                    "addr": f"0x{addr:04X}",
                    "condition": self.mw.emulator.get_bp_condition(addr) or None,
                    "enabled": self.mw.emulator.bp_enabled.get(addr, True),
                    "hit_count": self.mw.emulator.bp_hit_count.get(addr, 0)
                }
            except Exception as e:
                return {"error": str(e)}
            
        # =============================================
        # TOOLS: Анализ и трассировка
        # =============================================
        
        def emu_disassemble(addr: int | None = None, length: int = 32) -> list:
            """Дизассемблировать область памяти вокруг адреса (по умолчанию PC)."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return ["Emulator not initialized"]
                if addr is None:
                    addr = self.mw.emulator.pc
                start = max(0, addr - 8)
                lines = self.mw.disassembler.disassemble(self.mw.mem_data, start, length)
                result = []
                for a, size, asm, undoc, target in lines:
                    marker = "►" if a == self.mw.emulator.pc else " "
                    bp = "●" if a in self.mw.emulator.breakpoints else " "
                    result.append(f"{marker}{bp} {a:04X}  {asm}{undoc}")
                return result
            except Exception as e:
                return [f"Error: {e}"]
        
        def emu_get_stack(depth: int = 8) -> list:
            """Получить содержимое стека (верхние N значений)."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return ["Emulator not initialized"]
                emu = self.mw.emulator
                result = []
                for i in range(depth):
                    addr = (emu.sp + i * 2) & 0xFFFF
                    value = emu.read_word(addr)
                    marker = " ← SP" if i == 0 else ""
                    result.append(f"{addr:04X}: {value:04X}{marker}")
                return result
            except Exception as e:
                return [f"Error: {e}"]
        
        def emu_trace(n: int = 10) -> list:
            """Трассировка: выполнить N инструкций и вернуть лог с состоянием."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return ["Emulator not initialized"]
                if self.mw.emulator.halted:
                    return ["CPU halted. Use emu_reset first."]
                
                emu = self.mw.emulator
                trace = []
                executed = 0
                
                for _ in range(n):
                    if emu.halted:
                        trace.append(f"[{emu.pc:04X}] HALTED")
                        break
                    
                    lines = self.mw.disassembler.disassemble(self.mw.mem_data, emu.pc, 1)
                    if lines:
                        _, _, asm, undoc, _ = lines[0]
                    else:
                        asm = f"DB {emu.read_byte(emu.pc):02X}"
                    
                    trace.append(
                        f"[{emu.pc:04X}] {asm:<15s} A={emu.a:02X} "
                        f"BC={emu.get_reg_pair('BC'):04X} DE={emu.get_reg_pair('DE'):04X} "
                        f"HL={emu.get_reg_pair('HL'):04X} SP={emu.sp:04X} "
                        f"CY={int(emu.flag_cy)} Z={int(emu.flag_z)}"
                    )
                    
                    if emu.pc in emu.breakpoints:
                        trace.append(f"  → Breakpoint hit!")
                        break
                    
                    if not emu.execute_instruction(silent=True):
                        break
                    executed += 1
                
                self.mw.safe_call(self.mw.update_emulator_ui)
                self.mw.safe_call(self.mw.update_emu_disasm_view)
                
                trace.append(f"\nExecuted {executed} instructions. PC=0x{emu.pc:04X}")
                return trace
            except Exception as e:
                import traceback
                return [f"Error: {e}", traceback.format_exc()]
        
        def emu_get_io_ports() -> dict:
            """Получить состояние всех IO-портов эмулятора."""
            try:
                if not hasattr(self.mw, 'emulator'):
                    return {"error": "Emulator not initialized"}
                return {f"0x{port:02X}": val for port, val in self.mw.emulator.io_ports.items()}
            except Exception as e:
                return {"error": str(e)}
        
        def emu_trace_start() -> str:
            """Включить запись трассировки выполнения. Трассировка записывает каждую выполненную инструкцию с состоянием регистров."""
            return api.emu_trace_start()
        
        def emu_trace_stop() -> str:
            """Выключить запись трассировки выполнения."""
            return api.emu_trace_stop()
        
        def emu_trace_clear() -> str:
            """Очистить буфер трассировки."""
            return api.emu_trace_clear()
        
        def emu_trace_get(limit: int = 0) -> list:
            """Получить записи трассировки. limit=0 — все записи, иначе последние N записей."""
            return api.emu_trace_get(limit if limit > 0 else None)
        
        def emu_trace_export(path: str, format: str = "txt") -> str:
            """Экспорт трассировки в файл. format: txt, csv, json. path — путь к файлу."""
            return api.emu_trace_export(path, format)
        
        # =============================================
        # TOOLS: Управление шиной
        # =============================================
        
        def hold_bus() -> bool:
            """Захватить шину i8080. Возвращает True если команда отправлена."""
            api = self._get_api()
            return api.hold_bus()
        
        def unhold_bus() -> bool:
            """Освободить шину i8080. Возвращает True если команда отправлена."""
            api = self._get_api()
            return api.unhold_bus()
        
        def wait_bus(timeout: float = 5.0) -> bool:
            """Ждать захвата шины. Возвращает True если шина захвачена."""
            api = self._get_api()
            return api.wait_bus(timeout)
        
        def wait_unhold(timeout: float = 5.0) -> bool:
            """Ждать освобождения шины. Возвращает True если шина освобождена."""
            api = self._get_api()
            return api.wait_unhold(timeout)
        
        # =============================================
        # TOOLS: Локальная память
        # =============================================
        
        def read_mem(addr: int) -> int | None:
            """Прочитать байт из локального образа памяти"""
            api = self._get_api()
            return api.read_mem(addr)
        
        def write_mem(addr: int, val: int) -> str:
            """Записать байт в локальный образ памяти"""
            api = self._get_api()
            api.write_mem(addr, val)
            return f"Written 0x{val:02X} to 0x{addr:04X}"
        
        def read_block(addr: int, size: int) -> list[int | None]:
            """Прочитать блок из локального образа памяти"""
            api = self._get_api()
            return api.read_block(addr, size)
        
        def write_block(addr: int, data: list[int]) -> str:
            """Записать блок в локальный образ памяти"""
            api = self._get_api()
            api.write_block(addr, data)
            return f"Written {len(data)} bytes to 0x{addr:04X}"
        
        def fill_mem(addr: int, size: int, val: int) -> str:
            """Заполнить диапазон памяти значением"""
            api = self._get_api()
            api.fill_mem(addr, size, val)
            return f"Filled {size} bytes with 0x{val:02X} starting at 0x{addr:04X}"
        
        # =============================================
        # TOOLS: Память устройства
        # =============================================
        
        def dev_read_mem(addr: int) -> int | None:
            """Прочитать байт из памяти УСТРОЙСТВА (требует шину)"""
            api = self._get_api()
            return api.dev_read_mem(addr)
        
        def dev_write_mem(addr: int, val: int) -> bool:
            """Записать байт в память УСТРОЙСТВА (требует шину)"""
            api = self._get_api()
            return api.dev_write_mem(addr, val)
        
        def dev_read_io(port: int) -> int | None:
            """Прочитать из IO-порта УСТРОЙСТВА (требует шину)"""
            api = self._get_api()
            return api.dev_read_io(port)
        
        def dev_write_io(port: int, val: int) -> bool:
            """Записать в IO-порт УСТРОЙСТВА (требует шину)"""
            api = self._get_api()
            return api.dev_write_io(port, val)
        
        # =============================================
        # TOOLS: Синхронизация
        # =============================================
        
        def download(addr: int, size: int) -> list[int] | None:
            """Считать блок из УСТРОЙСТВА в локальный образ"""
            api = self._get_api()
            return api.download(addr, size)
        
        def upload(addr: int, size: int) -> bool:
            """Записать блок из локального образа в УСТРОЙСТВО"""
            api = self._get_api()
            return api.upload(addr, size)
        
        # =============================================
        # TOOLS: Дизассемблирование и поиск
        # =============================================
        
        def disassemble(addr: int | None = None, length: int | None = None, show: bool = False) -> list[str]:
            """Дизассемблировать локальный образ памяти"""
            api = self._get_api()
            return api.disassemble(addr, length, show)
        
        def search(pattern: str, mode: str = "hex") -> list[int]:
            """Поиск в локальном образе памяти. mode: 'hex' или 'ascii'"""
            api = self._get_api()
            return api.search(pattern, mode)
        
        # =============================================
        # TOOLS: Файлы
        # =============================================
        
        def load_file(path: str, base_addr: int = 0) -> int:
            """Загрузить файл прошивки в локальный образ"""
            api = self._get_api()
            return api.load_file(path, base_addr)
        
        def save_file(path: str) -> bool:
            """Сохранить локальный образ в файл"""
            api = self._get_api()
            return api.save_file(path)
        
        # =============================================
        # TOOLS: Утилиты
        # =============================================
        
        def get_status() -> dict:
            """Получить текущее состояние программы"""
            api = self._get_api()
            return api.status()
        
        def refresh() -> str:
            """Принудительно обновить hex-редактор и дизассемблер"""
            api = self._get_api()
            api.refresh()
            return "GUI refreshed"
            
        # =============================================
        # РЕГИСТРАЦИЯ TOOLS (явная)
        # =============================================
        
        mcp.tool()(emu_reset)
        mcp.tool()(emu_step_into)
        mcp.tool()(emu_step_over)
        mcp.tool()(emu_run)
        mcp.tool()(emu_run_to)
        mcp.tool()(emu_stop)
        mcp.tool()(emu_get_state)
        mcp.tool()(emu_get_reg)
        mcp.tool()(emu_set_reg)
        mcp.tool()(emu_get_psw)
        mcp.tool()(emu_set_psw)
        mcp.tool()(emu_get_flags)
        mcp.tool()(emu_set_flag)
        mcp.tool()(emu_add_breakpoint)
        mcp.tool()(emu_remove_breakpoint)
        mcp.tool()(emu_list_breakpoints)
        mcp.tool()(emu_clear_breakpoints)
        mcp.tool()(emu_disassemble)
        mcp.tool()(emu_get_stack)
        mcp.tool()(emu_trace)
        mcp.tool()(emu_get_io_ports)
        mcp.tool()(hold_bus)
        mcp.tool()(unhold_bus)
        mcp.tool()(wait_bus)
        mcp.tool()(wait_unhold)
        mcp.tool()(read_mem)
        mcp.tool()(write_mem)
        mcp.tool()(read_block)
        mcp.tool()(write_block)
        mcp.tool()(fill_mem)
        mcp.tool()(dev_read_mem)
        mcp.tool()(dev_write_mem)
        mcp.tool()(dev_read_io)
        mcp.tool()(dev_write_io)
        mcp.tool()(download)
        mcp.tool()(upload)
        mcp.tool()(disassemble)
        mcp.tool()(search)
        mcp.tool()(load_file)
        mcp.tool()(save_file)
        mcp.tool()(get_status)
        mcp.tool()(refresh)
        mcp.tool()(emu_add_conditional_breakpoint)
        mcp.tool()(emu_set_bp_condition)
        mcp.tool()(emu_toggle_bp_enabled)
        mcp.tool()(emu_get_bp_info)
        mcp.tool()(emu_trace_start)
        mcp.tool()(emu_trace_stop)
        mcp.tool()(emu_trace_clear)
        mcp.tool()(emu_trace_get)
        mcp.tool()(emu_trace_export)
        
        # =============================================
        # RESOURCES
        # =============================================
        
        @mcp.resource("memory://current")
        def get_memory_dump() -> str:
            """Текущий дамп памяти в формате HEX"""
            lines = []
            for addr in sorted(self.mw.mem_data.keys()):
                lines.append(f"{addr:04X}: {self.mw.mem_data[addr]:02X}")
            return "\n".join(lines) if lines else "Memory is empty"
        
        @mcp.resource("memory://disassembly")
        def get_disassembly() -> str:
            """Дизассемблированный код текущего образа памяти"""
            if not self.mw.mem_data:
                return "No code to disassemble"
            api = self._get_api()
            lines = api.disassemble()
            return "\n".join(lines)
        
        @mcp.resource("status://info")
        def get_status_info() -> str:
            """Информация о текущем состоянии программы"""
            api = self._get_api()
            return json.dumps(api.status(), indent=2)
        
        @mcp.resource("emulator://state")
        def get_emulator_state() -> str:
            """Текущее состояние эмулятора i8080"""
            if not hasattr(self.mw, 'emulator'):
                return "Emulator not initialized"
            state = self.mw.emulator.get_state()
            lines = [
                f"Регистры:",
                f"  A=0x{state['A']:02X}  B=0x{state['B']:02X}  C=0x{state['C']:02X}",
                f"  D=0x{state['D']:02X}  E=0x{state['E']:02X}  H=0x{state['H']:02X}  L=0x{state['L']:02X}",
                f"  BC=0x{state['BC']:04X}  DE=0x{state['DE']:04X}  HL=0x{state['HL']:04X}",
                f"  SP=0x{state['SP']:04X}  PC=0x{state['PC']:04X}",
                f"Флаги: S={int(state['flags']['S'])} Z={int(state['flags']['Z'])} "
                f"AC={int(state['flags']['AC'])} P={int(state['flags']['P'])} CY={int(state['flags']['CY'])}",
                f"Тактов: {state['cycles']}",
                f"Состояние: {'HALTED' if state['halted'] else ('RUNNING' if state['running'] else 'READY')}"
            ]
            return "\n".join(lines)
        
        @mcp.resource("emulator://stack")
        def get_emulator_stack() -> str:
            """Содержимое стека эмулятора"""
            if not hasattr(self.mw, 'emulator'):
                return "Emulator not initialized"
            emu = self.mw.emulator
            lines = [f"Стек (SP=0x{emu.sp:04X}):"]
            for i in range(10):
                addr = (emu.sp + i * 2) & 0xFFFF
                value = emu.read_word(addr)
                marker = " ← вершина" if i == 0 else ""
                lines.append(f"  {addr:04X}: 0x{value:04X}{marker}")
            return "\n".join(lines)
        
        @mcp.resource("emulator://breakpoints")
        def get_emulator_breakpoints() -> str:
            """Список точек останова эмулятора с условиями"""
            if not hasattr(self.mw, 'emulator'):
                return "Emulator not initialized"
            bps = sorted(self.mw.emulator.breakpoints)
            if not bps:
                return "Точек останова нет"
            lines = ["Точки останова:"]
            for addr in bps:
                condition = self.mw.emulator.get_bp_condition(addr)
                enabled = self.mw.emulator.bp_enabled.get(addr, True)
                hit_count = self.mw.emulator.bp_hit_count.get(addr, 0)
                
                line = f"  0x{addr:04X}"
                if condition:
                    line += f" [{condition}]"
                if not enabled:
                    line += " (выкл)"
                line += f" ×{hit_count}"
                lines.append(line)
            return "\n".join(lines)
        
        # =============================================
        # PROMPTS
        # =============================================
        
        @mcp.prompt()
        def analyze_firmware(focus: str = "общий анализ") -> str:
            """Анализ прошивки i8080"""
            return f"""Проанализируй прошивку i8080, загруженную в программу.
Фокус анализа: {focus}
Используй доступные инструменты для:
Чтения памяти устройства (download)
Дизассемблирования кода (disassemble)
Поиска инструкций (search)
Анализа структуры программы
Предоставь подробный отчёт о:
Структуре программы
Найденных подпрограммах
Точках входа
Потенциальных проблемах"""
        
        @mcp.prompt()
        def find_bugs() -> str:
            """Поиск потенциальных багов в коде i8080"""
            return """Проанализируй код i8080 на предмет потенциальных багов.
Проверь:
Бесконечные циклы без выхода
Обращения к несуществующим адресам памяти
Некорректные команды (недокументированные опкоды)
Проблемы со стеком (PUSH без POP, переполнение стека)
Незавершённые подпрограммы (CALL без RET)
Используй инструменты disassemble и search для анализа."""
        
        @mcp.prompt()
        def create_test_program(description: str) -> str:
            """Создание тестовой программы для i8080"""
            return f"""Создай тестовую программу для i8080, которая:
{description}
Требования:
Используй только стандартные команды i8080
Программа должна начинаться с адреса 0x0000
Добавь комментарии к каждой команде
Заверши программу командой HLT или бесконечным циклом
После создания:
Запиши программу в память (write_block)
Дизассемблируй для проверки (disassemble)
Покажи результат пользователю"""
        
        @mcp.prompt()
        def explain_code(addr: str, length: str) -> str:
            """Объяснение дизассемблированного кода"""
            return f"""Объясни код i8080, начиная с адреса 0x{addr}, длиной {length} байт.
Сначала дизассемблируй код (disassemble)
Объясни каждую инструкцию
Опиши общее назначение этого участка кода
Укажи на особенности или потенциальные проблемы"""
        
        @mcp.prompt()
        def debug_program(description: str = "общая отладка") -> str:
            """Комплексная отладка программы i8080"""
            return f"""Проведи комплексную отладку программы i8080.
Фокус: {description}
План действий:
Получи текущее состояние эмулятора (emu_get_state)
Дизассемблируй программу вокруг PC (emu_disassemble)
Проверь точки останова (emu_list_breakpoints)
Выполни трассировку нескольких инструкций (emu_trace с n=10)
Проанализируй стек (emu_get_stack)
На основе анализа:
Определи, что делает программа
Найди потенциальные ошибки (бесконечные циклы, неверные переходы, проблемы со стеком)
Предложи исправления
При необходимости установи точки останова для проверки гипотез"""
        
        @mcp.prompt()
        def find_infinite_loop() -> str:
            """Поиск бесконечного цикла в программе"""
            return """Найди бесконечный цикл в программе i8080.
Алгоритм:
Сбрось эмулятор (emu_reset)
Выполни трассировку 100 инструкций (emu_trace с n=100)
Проанализируй лог: ищи повторяющиеся значения PC
Если PC повторяется более 3 раз — это цикл
Дизассемблируй область цикла (emu_disassemble)
Определи: это бесконечный цикл (JMP на себя) или конечный (с условием выхода)?
Если цикл бесконечный и нежелательный — предложи исправление
Дополнительно проверь:
Есть ли условие выхода из цикла (JZ, JNZ, JC, JNC и т.д.)
Изменяется ли переменная цикла (регистр или память)
Корректны ли флаги после операций сравнения"""
        
        @mcp.prompt()
        def explain_instruction() -> str:
            """Объяснение текущей инструкции и её контекста"""
            return """Объясни текущую инструкцию эмулятора i8080.
Шаги:
Получи состояние (emu_get_state) для текущего PC
Дизассемблируй 5 инструкций вокруг PC (emu_disassemble)
Для текущей инструкции объясни:
Что она делает (семантика)
Какие регистры/флаги изменяет
Сколько тактов занимает
Возможные побочные эффекты
Объясни контекст: что было до и что будет после
Если это CALL/RET — объясни работу со стеком
Если это условный переход — объясни условие и вероятный исход"""
        
        @mcp.prompt()
        def trace_execution(num_steps: str = "20") -> str:
            """Подробная трассировка выполнения программы"""
            return f"""Выполни подробную трассировку программы i8080 на {num_steps} шагов.
План:
Получи начальное состояние (emu_get_state)
Выполни трассировку (emu_trace с n={num_steps})
Для каждого шага проанализируй:
Какая инструкция выполнена
Как изменились регистры
Как изменились флаги
Был ли переход и куда
В конце подведи итог:
Что сделала программа за эти шаги
Есть ли аномалии (неожиданные переходы, неверные значения)
Рекомендации по дальнейшей отладке
Если обнаружена точка останова — сообщи об этом и предложи продолжить или остановиться."""
        
        @mcp.prompt()
        def setup_conditional_debugging() -> str:
            """Настройка отладки с условными точками останова"""
            return """Настрой эффективную отладку программы i8080 с использованием условных точек останова.
План действий:
1. Дизассемблируй программу (emu_disassemble) и определи ключевые участки кода
2. Найди циклы, подпрограммы и критические точки
3. Установи условные breakpoints в стратегических местах:
   - Для циклов: условие на счётчик итераций или переменную цикла
   - Для подпрограмм: условие на входные параметры
   - Для работы с памятью: условие на значение в целевой ячейке
4. Используй emu_add_conditional_breakpoint с осмысленными условиями
5. Запусти программу (emu_run) и проанализируй, где происходит остановка
6. При необходимости корректируй условия через emu_set_bp_condition

Примеры полезных условий:
- "A == 0x00" — остановка при обнулении аккумулятора
- "HL > 0x1000" — выход за пределы ожидаемого диапазона
- "mem[0x0100] != 0xFF" — изменение целевой ячейки памяти
- "SP < 0xF000" — подозрительное значение стека (переполнение)
- "cycles > 50000" — программа работает слишком долго

После настройки объясни, какие условия были выбраны и почему."""

        return mcp
        
    def _get_api(self):
        """Получает экземпляр AutomationAPI"""
        if hasattr(self.mw, '_automation_api'):
            return self.mw._automation_api
        # Создаём новый, если нет
        from i8080_CI import AutomationAPI
        return AutomationAPI(self.mw)