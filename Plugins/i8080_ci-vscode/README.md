# i8080_ci-vscode

Плагин для VS Code: ассемблер и эмулятор Intel 8080/8085 (проект **i8080-5 CI**).

## Возможности

- **Подсветка синтаксиса** — TextMate-грамматика для 8080/8085 ассемблера (мнемоники, директивы, регистры, числа, метки, комментарии, препроцессор)
- **Автодополнение** — сниппеты для типовых конструкций (main, delay, sub, macro, I/O, прерывания)
- **Ассемблирование из VS Code** — вызов Python-ассемблера, ошибки/предупреждения в панели Problems
- **Живая эмуляция** — headless MCP-сервер (без GUI): reset, run, step, state, disassemble
- **Профили систем** — выбор из 12 TOML-профилей (full, micro80, radio86rk, …), тип CPU берётся из профиля
- **Статус-бар** — состояние эмулятора и текущий PC

## Требования

- **VS Code 1.85+** (2024), desktop (без Web)
- **Python 3.10+** (для ассемблера и MCP-сервера)
- **Node.js 18+** (только для сборки .vsix)
- Проект **i8080-5_CI-AI-analysis** (папка с `mcp_headless.py` и `profiles/`)

## Установка

### Вариант 1: через .vsix (рекомендуется)

```bat
cd Plugins\i8080_ci-vscode
build_vsix.bat    :: собирает i8080_ci-vscode-0.1.0.vsix
install.bat       :: устанавливает в VS Code
```

После установки: `Ctrl+Shift+P` → `Developer: Reload Window`.

### Вариант 2: режим разработки (F5)

```bat
cd Plugins\i8080_ci-vscode
dev_mode.bat
```

Откроется Extension Development Host — работайте с `.asm`-файлами.

## Настройка

Откройте Settings (`Ctrl+,`) и найдите `i8080ci`:

| Настройка | По умолчанию | Описание |
|---|---|---|
| `i8080ci.pythonPath` | *(пусто)* | Путь к Python. Пусто = автопоиск через `where python` |
| `i8080ci.projectRoot` | *(пусто)* | Корень i8080-5_CI-AI-analysis. Пусто = автопоиск вверх от файла |
| `i8080ci.profile` | `full` | Профиль системы для эмуляции |
| `i8080ci.mcpPort` | `8000` | Порт headless MCP-сервера |
| `i8080ci.mcpHost` | `127.0.0.1` | Хост MCP-сервера |
| `i8080ci.autoAssemble` | `false` | Сборка при сохранении .asm |
| `i8080ci.outputBin` | `true` | Сохранять .bin рядом с исходником |
| `i8080ci.outputMap` | `true` | Сохранять .map рядом с исходником |
| `i8080ci.showWarnings` | `true` | Показывать предупреждения |

## Команды

| Команда | Горячая клавиша | Описание |
|---|---|---|
| `i8080-5 CI: Assemble` | `Ctrl+Alt+A` | Ассемблировать текущий .asm |
| `i8080-5 CI: Assemble & Emulate` | `Ctrl+Alt+Enter` | Собрать и загрузить в эмулятор |
| `i8080-5 CI: Select Profile` | — | Выбрать профиль системы |
| `i8080-5 CI: Emulator — Start` | — | Запустить headless MCP-сервер |
| `i8080-5 CI: Emulator — Stop` | — | Остановить сервер |
| `i8080-5 CI: Emulator — Reset` | — | Сброс эмулятора |
| `i8080-5 CI: Emulator — Run` | — | Запуск |
| `i8080-5 CI: Emulator — Step Into` | `F11` | Шаг с заходом |
| `i8080-5 CI: Emulator — Step Over` | `Shift+F11` | Шаг без захода |
| `i8080-5 CI: Emulator — Stop Run` | — | Остановить выполнение |
| `i8080-5 CI: Emulator — Show State` | — | Показать регистры/флаги |
| `i8080-5 CI: Emulator — Disassemble` | — | Дизассемблировать от PC |
| `i8080-5 CI: Show Output` | — | Показать лог |

## Как это работает

- **Ассемблер** — stateless: плагин вызывает `python` с хелпером, который собирает `.asm` и возвращает JSON (бинарь, ошибки, символы, map). Бинарь и map сохраняются рядом с исходником.
- **Эмулятор** — headless MCP-сервер: плагин запускает `python mcp_headless.py --profile <X> --port <Y>` (один экземпляр, без GUI, `QT_QPA_PLATFORM=offscreen`), подключается по SSE и вызывает инструменты (51 шт.: управление, регистры, breakpoints, память, дизассемблер, трассировка).
- **Тип CPU** — для сборки определяется из директив в исходнике (`.8080`/`.8085`/`CPU 8085`, по умолчанию i8080); для эмуляции — из профиля.

## Архитектура

```
Plugins/i8080_ci-vscode/
├── package.json              # манифест (команды, грамматика, настройки)
├── syntaxes/i8080-asm.tmLanguage.json  # TextMate-грамматика
├── language-configuration.json         # комментарии, скобки, folding
├── snippets/i8080-asm.json             # автодополнение
├── src/
│   ├── extension.ts          # точка входа, команды, статус-бар
│   ├── assembler.ts          # вызов Python-ассемблера (CLI)
│   ├── diagnostics.ts        # ошибки/предупреждения в Problems
│   ├── mcp.ts                # SSE-клиент headless MCP-сервера
│   ├── python.ts             # обнаружение Python (where python)
│   └── project.ts            # определение корня проекта, профили
├── build_vsix.bat            # сборка .vsix
├── install.bat               # установка .vsix
└── dev_mode.bat              # режим разработки (F5)
```

## Разработка

### Сборка .vsix

Стандартный путь (нужен Node.js 18+ и доступ к npm):
```bat
build_vsix.bat    :: npm install + tsc + vsce package
install.bat       :: code --install-extension *.vsix
dev_mode.bat      :: Extension Development Host (F5)
```

### Локальная компиляция без npm (офлайн)

Если нет доступа к npm-реестру, можно скомпилировать TypeScript бандл-компилятором из самой VS Code:
```bat
node build.js       :: компиляция src/*.ts -> out/*.js
node typecheck.js   :: проверка типов (vscode.d.ts из VS Code + types/node-globals.d.ts)
```

### E2E-тест (вне VS Code)

```bat
node e2e_test.js
```
Тест поднимает headless MCP-сервер, проверяет: поиск Python, определение корня проекта и профилей, ассемблирование (успех + ошибка), вызовы MCP-инструментов (state, reset, read/write mem, disassemble, breakpoints, get_status, hold_bus). Ожидается `25 passed, 0 failed`.

Мок модуля `vscode` лежит в `node_modules/vscode/` (используется только e2e_test.js, в .vsix не попадает).

## Лицензия

MIT
