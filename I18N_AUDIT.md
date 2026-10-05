# I18n Audit Report / Аудит интернационализации

## i8080-5 CI

**STATUS: ✅ ALL ISSUES FIXED / ВСЕ ПРОБЛЕМЫ ИСПРАВЛЕНЫ**

Pass 4 (2026-09-08) + Pass 5 (2026-09-14) — all 26 issues resolved plus additional dm_* / dw_* keys added.

---

**Date / Дата:** 2026-09-08 (audit), 2026-09-14 (final fix)
**Files / Файлы:** `i8080_ci/main_window.py`, `i8080_ci/views/search.py`, `ui/device_manager.py`, `ui/device_window.py`
**i18n System / Система i18n:** `i8080_ci/i18n.py` → `LANGS["en"]` / `LANGS["ru"]` (378 keys per language)

---

## Summary / Резюме

**EN:**

| Category / Категория | Count / Кол-во |
|-----------|--------|
| Genuinely missing translations (no key in LANGS) | **12** |
| Strings set in `__init__` but NOT updated in `retranslate_ui` | **8** |
| Bug: local variable prevents retranslation | **2** |
| Bug: wrong format string in `retranslate_ui` | **1** |
| False positives (already handled) | **~40** |
| Device Manager/Window keys (added in Pass 5) | **15** |
| Global language propagation fix | **1** |

**RU:**

| Категория | Кол-во |
|-----------|--------|
| Истинно отсутствующие переводы (нет ключа в LANGS) | **12** |
| Строки, установленные в `__init__`, но НЕ обновляемые в `retranslate_ui` | **8** |
| Баг: локальная переменная препятствует перевыдаче | **2** |
| Баг: неправильный формат в `retranslate_ui` | **1** |
| Ложные срабатывания (уже обработаны) | **~40** |
| Ключи Device Manager/Window (добавлены в Pass 5) | **15** |
| Глобальная передача языка между диалогами | **1** |

---

## 1. Genuinely Missing Translations / Истинно отсутствующие переводы

**EN:** These strings appear in the UI but have no corresponding key in the `LANGS` dictionary.

**RU:** Эти строки появляются в UI, но не имеют соответствующего ключа в словаре `LANGS`.

### 1.1 Theme Combo Box

| # | String | Context | Key | EN | RU |
|---|--------|---------|-----|----|----|
| 1 | `"Light"` | `theme_combo.addItems` | `light` ✅ | Light | Светлая |
| 2 | `"Dark"` | same | `dark` ✅ | Dark | Тёмная |

> **Note / Примечание:** Keys already existed in LANGS. The combo just didn't use them. Fixed: now uses `self.tr()`.

### 1.2 Endianness Combo Box

| # | String | Key | EN | RU |
|---|--------|-----|----|----|
| 3 | `"Little"` | `endian_little` | Little-Endian | Little-Endian |
| 4 | `"Big"` | `endian_big` | Big-Endian | Big-Endian |

### 1.3 Memory Test Patterns

| # | String | Key | EN | RU |
|---|--------|-----|----|----|
| 7 | `"Checker"` | `test_pattern_checker` | Checker | Шахматный |
| 8 | `"Zero"` | `test_pattern_zero` | Zero | Нули |
| 9 | `"One"` | `test_pattern_one` | One | Единички |
| 10 | `"Addr"` | `test_pattern_addr` | Address | Адрес |

### 1.4 MCP Server Button

| # | String | Key | EN | RU |
|---|--------|-----|----|----|
| 11 | `"MCP Server: OFF"` | `mcp_off` | MCP Server: OFF | MCP Сервер: ВЫКЛ |
| 12 | `"MCP Server: ON"` | `mcp_on` | MCP Server: ON | MCP Сервер: ВКЛ |

### 1.5 Search Dialog Placeholder

| # | String | Key | EN | RU |
|---|--------|-----|----|----|
| 13 | `"C3 00 10 or HELLO"` | `search_placeholder` | C3 00 10 or HELLO | C3 00 10 или HELLO |

### 1.6 Bus Status Suffixes

| # | String | Key | EN | RU |
|---|--------|-----|----|----|
| 14 | `"BUS ACTIVE"` | `bus_active` | BUS ACTIVE | ШИНА АКТИВНА |
| 15 | `"BUS FREE"` | `bus_free` | BUS FREE | ШИНА СВОБОДНА |

---

## 2. Strings NOT Updated in `retranslate_ui` / Строки не обновляемые в `retranslate_ui`

**EN:** These strings use hardcoded text as initial values and are never reset when the user switches language.

**RU:** Эти строки используют зажёсткованный текст как начальные значения и никогда не сбрасываются при переключении языка.

| # | Widget | LANGS Key | Issue / Проблема |
|---|--------|-----------|-------|
| 16 | `status_label_addr` | `status_addr` | Never reset in retranslate_ui / Никогда не сбрасывается |
| 17 | `status_label_data` | `status_data` | Same / Аналогично |
| 18 | `status_label_mnem` | `status_mnem` | Same / Аналогично |
| 19 | `status_label_size` | `status_size` | **Wrong format** in retranslate_ui / **Неверный формат** |
| 20 | `status_label_conn` | `disconnected` | Never reset / Никогда не сбрасывается |
| 21 | `cycles_label` | `emu_cycles` | Never reset / Никогда не сбрасывается |
| 22 | `state_label` | `emu_state` + `emu_state_halted` | Never reset / Никогда не сбрасывается |
| 23 | `lbl_trace_status` | `trace_records` | Never reset / Никогда не сбрасывается |

> **Impact / Влияние:** If app starts in English (or user switches), these labels remain in wrong language until specific event triggers update.

> **Fix pattern / Паттерн исправления:** All added to `retranslate_ui()`.

---

## 3. Bug: Local Variable Prevents Retranslation / Баг: локальная переменная

| # | Code | Problem / Проблема |
|---|------|---------|
| 24 | `devices_menu = self.menuBar().addMenu("Устройства")` | Local variable, not `self.devices_menu`. `hasattr(self, 'devices_menu')` always False. |
| 25 | `act_manager = devices_menu.addAction("Диспетчер устройств")` | Local variable, no reference stored. |

> **Fix / Исправление:** Changed to `self.devices_menu` and `self.act_device_manager` with proper references.

---

## 4. Bug: Wrong Format / Баг: неверный формат

| # | Code | Problem | Fix |
|---|------|---------|-----|
| 26 | `f"0 {self.tr('status_size')}"` | Produces `"0 Size: "` (reversed word order). Should be `f"0 {self.tr('bytes')}"` → `"0 bytes"` / `"0 байт"`. | Fixed in retranslate_ui |

---

## 5. Device Manager & Window Keys (Pass 5) / Ключи Диспетчера и Окна устройств

**EN:** The `DeviceManagerDialog` and `DeviceWindow` had entirely hardcoded Russian strings. In Pass 5, a full `tr()` method with lazy i18n import was added, along with 15 new keys:

**RU:** В `DeviceManagerDialog` и `DeviceWindow` были полностью зажёсткованные русские строки. В Pass 5 добавлен метод `tr()` с lazy-импортом i18n и 15 новых ключей:

| Key | EN | RU |
|-----|----|----|
| `dm_title` | Device Manager / Диспетчер устройств | Диспетчер устройств / Device Manager |
| `dm_subtitle` | Devices of current profile | Устройства текущего профиля |
| `dm_open` | Open | Открыть |
| `dm_close_all` | Close All | Закрыть все |
| `dm_refresh` | Refresh | Обновить |
| `dm_always_on_top` | Device windows always on top | Окна устройств всегда поверх всех |
| `dm_no_devices` | No devices | Нет устройств |
| `dm_cube_title` | 3D Cube | 3D-куб |
| `dm_keyboard_title` | Keyboard 8x8 | Клавиатура 8x8 |
| `dw_auto` | Auto | Авто |
| `dw_auto_tooltip` | Auto-refresh device state | Автообновление состояния устройства |
| `dw_refresh` | Refresh | Обновить |
| `dw_yes` | Yes | Да |
| `dw_no` | No | Нет |

---

## 6. Global Language State Fix (Pass 5) / Глобальное состояние языка

**EN:**
**Problem:** `DeviceManagerDialog.tr()` used `get_system_language()` (system locale) but didn't know about user's language selection in `MainWindow.lang_combo`.

**Solution:** Added `_current_lang` global variable and `set_language(lang)` function to `i18n.py`. `get_system_language()` now checks `_current_lang` first before falling back to `QLocale`.

**RU:**
**Проблема:** `DeviceManagerDialog.tr()` использовал `get_system_language()` (системный locale) и не знал о выборе языка пользователем.

**Решение:** Добавлена глобальная переменная `_current_lang` и функция `set_language(lang)` в `i18n.py`. `get_system_language()` теперь сначала проверяет `_current_lang`, затем fallback на `QLocale`.

```python
# i18n.py
_current_lang = None

def set_language(lang: str) -> None:
    global _current_lang
    _current_lang = lang

def get_system_language() -> str:
    if _current_lang is not None:
        return _current_lang
    from PySide6.QtCore import QLocale
    loc = QLocale.system().name()
    return 'ru' if loc.startswith('ru') else 'en'
```

Called from `main_window.py`:
- `__init__`: `set_language(self.current_lang)`
- `on_lang_changed`: `set_language(self.current_lang); self.retranslate_ui()`

---

## 7. False Positives (Already Handled) / Ложные срабатывания

**EN:** The following hardcoded strings are set in `__init__` as placeholder values but **are properly updated** in `retranslate_ui()` or `emulator_retranslate()`:

**RU:** Следующие зажёсткованные строки установлены в `__init__` как плейсхолдеры, но **корректно обновляются** в `retranslate_ui()` или `emulator_retranslate()`:

| File | Strings | Handled In |
|------|---------|-----------|
| main_window.py | "Port:", "Baud:" | retranslate_ui |
| main_window.py | "Export" | retranslate_ui |
| main_window.py | "▶ Run Script", "Load Script", etc. | retranslate_ui |
| main_window.py | Watch/BP/Register group titles | emulator_retranslate |
| main_window.py | Emulator buttons | emulator_retranslate |
| main_window.py | Trace buttons, depth, search | retranslate_ui |
| search.py | All labels/buttons | SearchDialog.retranslate() |

**Technical values (NOT user-facing / Технические значения, не user-facing):**
- Baud rates: "9600", "38400", etc.
- Bit widths: "8", "16", "24", "32"
- Language names: "Русский", "English" (by convention shown in native language)
- Register names: "A", "B", "SP", "PC", etc.
- Hex values: "0000", "00"
- Icons/symbols: "+", "❌", "🗑", etc.

---

## 8. Verification Checklist / Чек-лист верификации

After fixes, verified / После исправлений, верифицировано:

- [x] Switch EN → RU: all labels, buttons, tooltips, combos update
- [x] Switch RU → EN: same
- [x] Status bar shows correct language on initial load
- [x] Emulator tab stats show correct language
- [x] Trace tab status shows correct language
- [x] Theme/Endianness/Test pattern combos show correct language
- [x] Devices menu title AND action text update
- [x] MCP button text updates on language switch
- [x] Search dialog placeholder updates
- [x] Bus status suffix shows correct language
- [x] Device Manager dialog fully translated (EN + RU)
- [x] Device Window fully translated (EN + RU)
- [x] Global language propagates to all dialogs
