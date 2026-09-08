# i8080-5 CI

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

**i8080-5 CI** (i8080-5 Control Interface) — a comprehensive Master Controller for the i8080-5 hardware platform. Combines a full i8080 CPU emulator, interactive debugger, real-hardware bridge, and AI integration (MCP server) in a single desktop application.

**i8080-5 CI** — комплексная среда управления аппаратной платформой i8080-5: эмулятор CPU, отладчик, мост к реальному устройству и интеграция с AI-ассистентами.

## Screenshots

| Main Window | Hex Editor | Disassembler |
|-------------|------------|--------------|
| <img src="8080-5 CI_app.png" width="300"> | <img src="8080-5 CI_app_hex.png" width="300"> | <img src="8080-5 CI_app_disas.png" width="300"> |

| Emulator | Trace Log | Device Connection |
|----------|-----------|-------------------|
| <img src="8080-5 CI_app_emu.png" width="300"> | <img src="8080-5 CI_app_trace.png" width="300"> | <img src="8080-5 CI_app_device.png" width="300"> |

| Micro-80 Profile | Specialist Profile |
|------------------|-------------------|
| <img src="8080-5 CI_app_Micro-80.png" width="300"> | <img src="8080-5 CI_app_Specialist.png" width="300"> |

## Features

### Emulation & Debugging

- **i8080 CPU Emulator** — full 256-instruction set including undocumented instructions
- **Debugger** — breakpoints (regular & conditional), step / step-over, run-to, watch windows, trace log
- **Disassembler** — real-time with jump arrows and instruction-type highlighting
- **Hex Editor** — view and edit memory images with search and block operations
- **Memory Test** — RAM verification using various patterns (walking bit, chessboard, etc.)
- **Comparison** — diff current memory image against a reference file

### Hardware Interface

- **Real Device Control** — read/write memory and IO ports via COM port (SLIP protocol)
- **IO Sequencer** — execute sequences of input/output operations
- **23+ IO Devices** — I8255, I8253, I8251, I8259, I8257, I8237, I8272, I8275, I8276, I8279, I16550, I512VI1, CF/IDE, CH376S (SD), AM9511, LCD1602, LCD2004, TFT8080, Keyboard 8x8, 3D Cube, Discrete Video, Bitmap Video

### System Profiles

- **TOML-based profiles** for popular i8080 systems (see [System Profiles](#system-profiles) table)
- Dynamic device configuration with memory-mapped IO support
- Shadow ROM, banked, paged, and segmented memory models

### AI Integration

- **MCP Server** — integrate with AI assistants (Claude Desktop, Cursor, etc.) via SSE transport
- **Scripts** — Python automation for reproducible tests and workflows

### UI

- **PySide6** desktop GUI with **Russian / English** interface
- **Light / Dark** themes

## Installation / Установка

### Requirements / Требования

- Python 3.10+
- PySide6, pyserial (installed automatically via requirements)

### Setup / Настройка

```bash
# Clone / extract
cd i8080-5_CI

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Run
python i8080_CI.py
```

### Build EXE (Windows)

```bash
pyinstaller --onefile --hide-console minimize-late --optimize 2 i8080_CI.py
```

## Project Structure / Структура проекта

```
i8080_CI.py                # Entry point (thin wrapper)
i8080_emulator.py          # i8080 CPU emulator (QObject, Qt Signals)
mcp_server.py              # MCP Server (FastMCP, SSE)
i8080_ci/                  # Application package
│   i18n.py                #   Internationalization (RU/EN strings, themes)
│   slip.py                #   SLIP protocol (constants, encode/decode)
│   intelhex.py            #   Intel HEX parser/generator
│   disassembler.py        #   i8080 disassembler engine
│   bus_worker.py          #   Serial bus worker (QThread)
│   automation.py          #   AutomationAPI (script interface)
│   main_window.py         #   MainWindow (QMainWindow)
│   models/
┃       hex_model.py       #     HexEditor table model
┃       watch_model.py     #     Watch window model
┃       bp_model.py        #     Breakpoint model
┃       trace_model.py     #     Trace log model
│   views/
┃       disasm_view.py     #     Disassembler view (jump arrows, colors)
┃       hex_view.py        #     Hex editor table view
┃       search.py          #     Search dialog
modules/                   # Hardware abstraction
│   system.py              #   ComputerSystem - integration hub
│   memory/                #   Memory models (banked, paged, shadow, MMIO, ...)
│   io/                    #   IO devices (I8255, I8253, I8272, I16550, ...)
│   config/                #   Device config parser & system profiles
ui/                        # Additional PySide6 widgets (device manager, etc.)
profiles/                  # TOML system profiles
roms/                      # ROM images
tests/                     # Test suite (pytest)
requirements.txt           # Python dependencies
pyproject.toml             # Project metadata
```

## MCP Server

The built-in MCP server allows AI assistants to interact with the emulator and connected hardware:

1. Launch the application
2. Enable MCP Server (button in main window or checkbox)
3. Connect an AI client — example for Claude Desktop:

```json
{
  "mcpServers": {
    "i8080": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

### Available Tools

| Category | Tools |
|----------|-------|
| Emulator | `emu_reset`, `emu_step_into`, `emu_step_over`, `emu_run`, `emu_run_to`, `emu_stop`, `emu_get_state` |
| Registers | `emu_get_reg`, `emu_set_reg`, `emu_get_psw`, `emu_set_psw`, `emu_get_flags`, `emu_set_flag` |
| Breakpoints | `emu_add_breakpoint`, `emu_remove_breakpoint`, `emu_add_conditional_breakpoint`, `emu_list_breakpoints` |
| Memory | `read_mem`, `write_mem`, `read_block`, `write_block`, `fill_mem` |
| IO | `dev_read_io`, `dev_write_io`, `emu_get_io_ports` |
| Device | `dev_read_mem`, `dev_write_mem`, `download`, `upload` |
| Analysis | `disassemble`, `search`, `load_file`, `save_file`, `analyze_firmware`, `find_bugs` |

Full guide: [MCP_GUIDE.md](MCP_GUIDE.md)

## System Profiles

| Profile | Description |
|---------|-------------|
| `micro80` | Micro-80 (16 KB RAM, I8255, I8279 KBD) |
| `microsha` | MicroSha (32 KB RAM, I8253, I8255) |
| `radio86rk` | Radio-86RK (64 KB RAM, I8255, I8279, I8253) |
| `apogey` | Apogey (64 KB RAM, I8255, I8279, video) |
| `orion128` | Orion-128 (128 KB RAM, expanded IO) |
| `vector06c` | Vector-06C (vector display) |
| `specialist` | Specialist (full IO set, bitmap video) |
| `full` | Full device set (all supported modules) |
| `empty` | Minimal configuration (CPU only) |

Profile files are located in `profiles/` and use TOML format.

## Testing / Тестирование

```bash
# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_i8255.py -v

# Run emulator standalone
python i8080_emulator.py
```

## Documentation / Документация

| Document | Description |
|----------|-------------|
| [USER_GUIDE.md](USER_GUIDE.md) | User guide / Пользовательское руководство |
| [MCP_GUIDE.md](MCP_GUIDE.md) | MCP integration guide |
| [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) | Automation scripts guide |
| [ANALYSIS.md](ANALYSIS.md) | Technical project analysis |

## Hardware Module

**8080-5-CI Module** — debug and download board for the i8080-5 platform.

<img src="8080-5 CI_top.png" width="400">

Connect to the debugging board via: [Stepper project](https://github.com/R2AKT/Stepper)

## License

[MIT](LICENSE)

License addendum: [Addendum.txt](Addendum.txt)
