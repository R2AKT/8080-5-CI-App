# i8080-5 CI

> **Master Controller** для аппаратной платформы i8080-5: GUI, эмулятор, MCP-сервер и Arduino-мост.

![App Screenshot](8080-5%20CI_app.png)

## Возможности

- **GUI (PySide6)** — контроль шины памяти, IO-портов, дизассемблер, hex-редактор, trace log
- **Встроенный эмулятор i8080** — breakpoints, step/step-over, run-to, conditional breakpoints, trace
- **MCP-сервер** — интеграция с AI-ассистентами (Claude Desktop, Cursor, etc.) через SSE
- **Arduino-мост** — SLIP-протокол для управления физическим контроллером
- **23+ IO-устройства** — I8255, I8253, I8251, I8259, I8257, I8272, I8275, I8276, I8279, I16550, I512VI1, CF/IDE, CH376S (SD), AM9511, LCD, TFT, 3D Cube
- **Система профилей** — TOML-конфигурации для Micro-80, MicroSha, Radio-86RK, Apogey, Orion-128, Vector-06C, Specialist и др.
- **Скрипты автоматизации** — Python-скрипты для воспроизводимых тестов

## Быстрый старт

### Требования

- Python 3.10+
- PySide6, pyserial (установятся автоматически)

### Установка

```bash
# Клонировать / распаковать
cd i8080-5_CI

# Создать виртуальное окружение
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Установить зависимости
pip install -r requirements.txt

# Запуск
python i8080_CI.py
```

### Собрать EXE (Windows)

```bash
pyinstaller --onefile --hide-console minimize-late --optimize 2 i8080_CI.py
```

## Структура проекта

```
├── i8080_CI.py          # Главное GUI-приложение (входная точка)
├── i8080_emulator.py    # Эмулятор CPU i8080
├── mcp_server.py        # MCP Server (FastMCP, SSE)
├── i8080-5_CI.ino       # Arduino-скетч
├── modules/
│   ├── system.py        # ComputerSystem — интеграция
│   ├── memory/          # Модели памяти (banked, paged, shadow, ...)
│   ├── io/              # IO-устройства (I8255, I8272, ...)
│   └── config/          # Конфигурации и профили
├── ui/                  # PySide6 виджеты
├── profiles/            # TOML-профили систем
├── roms/                # ROM-образы
├── tests/               # Тесты (pytest)
├── requirements.txt     # Python-зависимости
└── pyproject.toml       # Проектная декларация
```

## MCP Server

Встроенный MCP-сервер позволяет AI-ассистентам взаимодействовать с контроллером:

1. Запустите приложение
2. Включите MCP Server (кнопка в главном окне или чекбокс)
3. Подключите AI-клиент (пример для Claude Desktop):

```json
{
  "mcpServers": {
    "i8080": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

Доступные tools: `emu_reset`, `emu_step`, `emu_run`, `read_memory`, `write_memory`, `read_io`, `write_io`, и др.

Подробнее: [MCP_GUIDE.md](MCP_GUIDE.md)

## Тестирование

```bash
# Все тесты
pytest tests/

# Конкретный тест
pytest tests/test_i8255.py -v

# Эмулятор (standalone)
python i8080_emulator.py
```

## Документация

| Документ | Описание |
|----------|----------|
| [USER_GUIDE.md](USER_GUIDE.md) | Пользовательское руководство |
| [MCP_GUIDE.md](MCP_GUIDE.md) | Руководство по MCP-интеграции |
| [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) | Руководство по скриптам автоматизации |
| [ANALYSIS.md](ANALYSIS.md) | Технический анализ проекта |

## Поддерживаемые профили

| Профиль | Описание |
|---------|----------|
| `micro80` | Micro-80 (16KB RAM, I8255, I8279 KBD) |
| `microsha` | MicroSha (32KB RAM, I8253, I8255) |
| `radio86rk` | Radio-86RK (64KB RAM, I8255, I8279, I8253) |
| `apogey` | Apogey (64KB RAM, I8255, I8279, video) |
| `orion128` | Orion-128 (128KB RAM, expanded IO) |
| `vector06c` | Vector-06C (vector display) |
| `specialist` | Specialist (full IO set) |
| `full` | Полный набор устройств |
| `empty` | Пустая конфигурация (только CPU) |

## Лицензия

MIT
