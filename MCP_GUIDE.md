# MCP_GUIDE.md — Руководство по MCP-интеграции i8080-5 CI

> **Версия:** 2.0  
> **Дата:** 2026-08-16  
> **Протокол:** MCP (Model Context Protocol), транспорт SSE  
> **Адрес сервера:** `http://127.0.0.1:8000/sse`  
> **Зависимости:** `pip install mcp uvicorn starlette pydantic pydantic-settings`

---

## Содержание

1. [Обзор](#1-обзор)
2. [Запуск и подключение](#2-запуск-и-подключение)
3. [Tools: управление эмулятором](#3-tools-управление-эмулятором)
4. [Tools: состояние эмулятора](#4-tools-состояние-эмулятора)
5. [Tools: точки останова](#5-tools-точки-останова)
6. [Tools: анализ и трассировка](#6-tools-анализ-и-трассировка)
7. [Tools: шина и устройство](#7-tools-шина-и-устройство)
8. [Tools: память, файлы, утилиты](#8-tools-память-файлы-утилиты)
9. [Resources](#9-resources)
10. [Prompts](#10-prompts)
11. [Типовые сценарии](#11-типовые-сценарии)
12. [Устранение неполадок](#12-устранение-неполадок)

---

## 1. Обзор

**i8080-5 CI** — среда разработки и отладки для процессора Intel 8080:

- Эмулятор i8080 (полный набор инструкций, флаги, стек, такты)
- Отладчик: breakpoints, условные breakpoints, Run to Cursor, трассировка
- Hex-редактор, дизассемблер со стрелками переходов
- Работа с реальным устройством по SLIP-протоколу (COM-порт)
- Встроенный MCP-сервер для AI-ассистентов

MCP-сервер запускается **внутри программы** (вкладка «Управление», кнопка
«MCP Server: ON») и доступен по SSE.

---

## 2. Запуск и подключение

### Запуск сервера

1. Запустите `i8080_CI.py`
2. Вкладка «Управление» → кнопка **«MCP Server: ON»**
3. Сервер слушает `http://127.0.0.1:8000/sse`

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "i8080-ci": { "url": "http://127.0.0.1:8000/sse" }
  }
}
```

### Cursor (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "i8080-ci": { "url": "http://127.0.0.1:8000/sse" }
  }
}
```

### Python-клиент

```python
import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession

async def main():
    async with sse_client("http://127.0.0.1:8000/sse") as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            r = await s.call_tool("emu_get_state", {})
            print(r)

asyncio.run(main())
```

---

## 3. Tools: управление эмулятором

| Tool | Параметры | Описание |
|---|---|---|
| `emu_reset` | — | Сброс: регистры = 0, PC=0x0000, SP=0xFFFF |
| `emu_step_into` | — | Одна инструкция, заходит в CALL |
| `emu_step_over` | — | Одна инструкция, CALL выполняется целиком |
| `emu_run` | `max_instructions=10000` | Запуск до BP / HLT / лимита |
| `emu_run_to` | `addr` | Выполнять до адреса |
| `emu_stop` | — | Остановить выполнение |

Пример:

```json
{ "tool": "emu_run", "arguments": { "max_instructions": 5000 } }
```

Ответ: `"Executed 5000 instructions. Status: stopped. PC=0x0123"`

---

## 4. Tools: состояние эмулятора

| Tool | Параметры | Описание |
|---|---|---|
| `emu_get_state` | — | Все регистры, флаги, PC, SP, такты |
| `emu_get_reg` | `reg` | A,B,C,D,E,H,L,BC,DE,HL,SP,PC |
| `emu_set_reg` | `reg, val` | Установить регистр |
| `emu_get_psw` | — | PSW (A + флаги) |
| `emu_set_psw` | `val` | Установить PSW |
| `emu_get_flags` | — | Флаги S,Z,AC,P,CY |
| `emu_set_flag` | `flag, val` | Установить флаг (True/False) |

Пример ответа `emu_get_state`:

```json
{
  "A": 85, "B": 0, "C": 0, "D": 0, "E": 0, "H": 0, "L": 0,
  "SP": 65535, "PC": 1, "BC": 0, "DE": 0, "HL": 0,
  "flags": { "S": 0, "Z": 0, "AC": 0, "P": 1, "CY": 0 },
  "cycles": 7, "halted": 0, "running": 0, "interrupts": 0
}
```

---

## 5. Tools: точки останова

| Tool | Параметры | Описание |
|---|---|---|
| `emu_add_breakpoint` | `addr` | Обычная BP |
| `emu_remove_breakpoint` | `addr` | Удалить BP |
| `emu_list_breakpoints` | — | Список BP с условиями и счётчиком |
| `emu_clear_breakpoints` | — | Удалить все BP |
| `emu_add_conditional_breakpoint` | `addr, condition` | Условная BP |
| `emu_set_bp_condition` | `addr, condition` | Изменить условие (пустое = обычная BP) |
| `emu_toggle_bp_enabled` | `addr` | Вкл/выкл BP без удаления |
| `emu_get_bp_info` | `addr` | Адрес, условие, enabled, hit_count |

### Переменные условий

`A B C D E H L BC DE HL SP PC S Z AC P CY cycles mem[addr] io[port]`  
Операторы: `== != < > <= >= and or not`

Примеры условий:

```
A == 0x55
HL > 0x1000
mem[0x0100] == 0xFF
Z == 1
cycles > 10000
HL > 0x1000 and Z == 0
```

Пример:

```json
{ "tool": "emu_add_conditional_breakpoint",
  "arguments": { "addr": 256, "condition": "A == 0x55" } }
```

---

## 6. Tools: анализ и трассировка

| Tool | Параметры | Описание |
|---|---|---|
| `emu_disassemble` | `addr=None, length=32` | Дизассемблирование вокруг адреса (по умолчанию PC) |
| `emu_get_stack` | `depth=8` | Верхние N слов стека |
| `emu_trace` | `n=10` | Выполнить N инструкций, вернуть лог с регистрами |
| `emu_get_io_ports` | — | Состояние IO-портов эмулятора |
| `emu_trace_start` | — | Включить запись трассировки в буфер GUI |
| `emu_trace_stop` | — | Выключить запись |
| `emu_trace_clear` | — | Очистить буфер трассировки |
| `emu_trace_get` | `limit=0` | Записи буфера (0 = все) |
| `emu_trace_export` | `path, format="txt"` | Экспорт буфера: txt / csv / json |

Пример сценария трассировки:

```json
{ "tool": "emu_trace_start" }
{ "tool": "emu_run", "arguments": { "max_instructions": 1000 } }
{ "tool": "emu_trace_stop" }
{ "tool": "emu_trace_export", "arguments": { "path": "trace.csv", "format": "csv" } }
```

---

## 7. Tools: шина и устройство

Работа с реальным устройством требует захвата шины:

```json
{ "tool": "hold_bus" }
{ "tool": "wait_bus", "arguments": { "timeout": 5.0 } }
... работа с устройством ...
{ "tool": "unhold_bus" }
```

| Tool | Параметры | Описание |
|---|---|---|
| `hold_bus` | — | Захват шины (HOLD) |
| `unhold_bus` | — | Освобождение шины |
| `wait_bus` | `timeout=5.0` | Ждать захвата |
| `wait_unhold` | `timeout=5.0` | Ждать освобождения |
| `dev_read_mem` | `addr` | Чтение байта памяти устройства |
| `dev_write_mem` | `addr, val` | Запись байта в устройство |
| `dev_read_io` | `port` | Чтение IO-порта устройства |
| `dev_write_io` | `port, val` | Запись IO-порта устройства |
| `download` | `addr, size` | Считать блок из устройства в локальный образ |
| `upload` | `addr, size` | Записать блок из образа в устройство |

---

## 8. Tools: память, файлы, утилиты

| Tool | Параметры | Описание |
|---|---|---|
| `read_mem` | `addr` | Байт локального образа |
| `write_mem` | `addr, val` | Запись байта в образ |
| `read_block` | `addr, size` | Блок из образа |
| `write_block` | `addr, data` | Запись блока в образ |
| `fill_mem` | `addr, size, val` | Заполнить диапазон |
| `disassemble` | `addr=None, length=None, show=False` | Дизассемблировать образ |
| `search` | `pattern, mode="hex"` | Поиск в образе (hex / ascii) |
| `load_file` | `path, base_addr=0` | Загрузить .hex / .bin в образ |
| `save_file` | `path` | Сохранить образ |
| `get_status` | — | connected, bus_active, mem_size |
| `refresh` | — | Обновить GUI |

---

## 9. Resources

| URI | Описание |
|---|---|
| `memory://current` | Дамп памяти в HEX |
| `memory://disassembly` | Дизассемблированный код образа |
| `status://info` | Статус программы (JSON) |
| `emulator://state` | Состояние эмулятора |
| `emulator://stack` | Стек эмулятора |
| `emulator://breakpoints` | BP с условиями и счётчиком |

---

## 10. Prompts

| Prompt | Параметры | Назначение |
|---|---|---|
| `analyze_firmware` | `focus` | Анализ прошивки |
| `find_bugs` | — | Поиск потенциальных багов |
| `create_test_program` | `description` | Создать тестовую программу |
| `explain_code` | `addr, length` | Объяснить участок кода |
| `debug_program` | `description` | Комплексная отладка |
| `find_infinite_loop` | — | Поиск бесконечного цикла |
| `explain_instruction` | — | Объяснить текущую инструкцию |
| `trace_execution` | `num_steps` | Подробная трассировка |
| `setup_conditional_debugging` | — | Расставить условные BP |

---

## 11. Типовые сценарии

### Загрузка и анализ прошивки

```
load_file(path="firmware.hex")
disassemble(show=true)
analyze_firmware(focus="точки входа")
```

### Отладка с условной BP

```
emu_reset()
emu_add_conditional_breakpoint(addr=256, condition="A == 0x55")
emu_run()
emu_get_state()
```

### Поиск бесконечного цикла

```
emu_reset()
emu_trace(n=100)
find_infinite_loop()
```

### Дамп устройства

```
hold_bus() → wait_bus()
download(addr=0, size=4096)
unhold_bus()
save_file(path="dump.hex")
```

---

## 12. Устранение неполадок

| Симптом | Решение |
|---|---|
| «MCP Server недоступен» | `pip install mcp uvicorn starlette pydantic pydantic-settings` |
| Нет подключения к SSE | Программа запущена? Кнопка «MCP Server: ON»? Порт 8000 свободен? |
| «Emulator not initialized» | Откройте вкладку «Эмулятор» |
| «Device not connected» | Подключите COM-порт во вкладке «Управление» |
| «Bus not active» | Выполните `hold_bus()` + `wait_bus()` |
| «Syntax error in condition» | Проверьте условие: `A == 0x55`, а не `A = 0x55` |

---

*Конец документа.*