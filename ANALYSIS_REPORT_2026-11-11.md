# Технический анализ проекта i8080-5 CI — 11.11.2026

## Версия

**v2.1.15** (build 20261023)

## Статистика кода

| Метрика | Значение |
|---------|----------|
| Python-файлы | 256 |
| Строки кода (LOC) | 49 036 |
| Файлы с парсером (analyze) | 171 |
| Функций/методов | 1 548 |
| Классов | 113 |
| Язык | Python 99%, JavaScript 1% (VS Code plugin) |

### Основные модули по объёму

| Модуль | Файл | LOC | Функций | Классов |
|--------|------|-----|---------|---------|
| GUI (main window) | i8080_ci/main_window.py | 4 203 | 157 | 1 |
| Эмулятор | i8080_emulator.py | 2 000 | 63 | 2 |
| Ассемблер v2 | i8080_ci/assembler_widget.py | 2 063 | 94 | 6 |
| Ядро ассемблера | assemble8080/assembler.py | 2 103 | 37 | 4 |
| MCP сервер | mcp_server.py | 1 213 | 91 | 1 |
| i18n | common/i18n.py | 975 | 3 | 0 |
| CH376S (USB storage) | modules/io/ch376s.py | 1 055 | 59 | 3 |
| i8272 (FDC) | modules/io/i8272.py | 777 | 42 | 2 |
| Автоматизация | i8080_ci/automation.py | 736 | 56 | 1 |
| Препроцессор | assemble8080/preprocessor.py | 630 | 18 | 2 |

## Циклические тесты (3 прогона)

| Цикл | run_tests.py | Статус |
|------|-------------|--------|
| 1 | 978 passed / 0 failed / 0 errors | ✅ |
| 2 | 978 passed / 0 failed / 0 errors | ✅ |
| 3 | 978 passed / 0 failed / 0 errors | ✅ |

**3 consecutive clean cycles — стабильность подтверждена.**

## Аудитные циклы (6 скриптов)

| Скрипт | Проверок | Результат |
|--------|----------|-----------|
| audit_cycle1.py | 46 | ✅ ALL PASSED |
| audit_cycle1b.py | 43 | ✅ ALL PASSED |
| audit_cycle1c.py | 23 | ✅ ALL PASSED |
| audit_cycle2.py | 590 | ✅ ALL PASSED |
| audit_cycle3.py | 98 | ✅ ALL PASSED |
| audit_cycle4.py | 624 | ✅ ALL PASSED |
| **Итого** | **1 424** | **0 ошибок** |

## Git

| Метрика | Значение |
|---------|----------|
| Всего коммитов | 53 |
| Последний | `7fda725` docs: add mandatory XERJ usage rules |

## XERJ индекс

| Параметр | Значение |
|----------|----------|
| Префикс | `i8080ci` |
| Датасетов | 7 |
| Записей | 12 286 |
| Файлов проиндексировано | 375 |
| Бинарных (skipped) | 19 |
| Дубликатов | 3 |
| Края графа | 1 730 |
| Время переиндексации | 4.6 с |

## Тестовые файлы

38 тестовых файлов покрывают:
- Эмулятор: ALU, integration, interrupts, 8085 opcodes
- Ассемблер: full, include, linker, 8085, macro, directives
- ИО: AM9511, CH376S, CF IDE, DMA, UART, I512VI1, I8251-8259, I8272, I8275, I8276, I8279
- Память: banked, paged, segmented, shadow, MMIO
- GUI: smoke test, watch, disasm, hex
- Система: config, profiles, system integration, wait signals

## Заключение

Проект в **стабильном рабочем состоянии**. Все 978 проверок проходят без единого сбоя в 3 последовательных циклах. 1 424 аудиторских проверки покрывают:
- Корректность опкодов (SOT: OPCODE_REFERENCE.md)
- Согласованность ассемблер ↔ дизассемблер ↔ эмулятор
- Версионность (version.py = pyproject.toml = README)
- i18n полноту (EN+RU)
- Документацию (ASSEMBLER_GUIDE, OPCODE_REFERENCE)
- Примеры сборки (4 проекта в assembler_example/)

Релиз v2.1.15 загружен на GitHub (R2AKT/8080-5-CI-App) с Windows exe и Linux бинарником.
