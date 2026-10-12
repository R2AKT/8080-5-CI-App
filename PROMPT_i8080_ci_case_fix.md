# Промпт для корректировки i8080_ci: case-mismatch ломает кросс-модульную линковку

## Контекст

Пайплайн SmallC 8080:
`C -> cc8080.exe -> .s -> ci assembler -> .obj -> ci linker -> .bin -> run8080.py`

В `i8080_ci` (ветка `main`, коммит `e227f00` "Add label case sensitivity, fix ALU opcode code size")
добавлена чувствительность к регистру меток:
- по умолчанию **case-insensitive**: `main` / `Main` / `MAIN` — один и тот же символ;
- исходный регистр метки **сохраняется** в таблице символов, map-файле и `.obj`
  (например, `main`, а не `MAIN`) — это важно для SmallC, который генерирует метки в нижнем регистре;
- флаг `--case-sensitive` (и `assemble(..., case_sensitive=True)`) включает точное совпадение регистра.

Фикс размера ALU-immediate в pass 1 (из того же коммита) **подтверждён рабочим**:
смещения меток после `ADD #n` / `SUB #n` / `CMP #n` теперь корректны.

## Найденный баг (критический для пайплайна)

В режиме **case-insensitive** (по умолчанию) ассемблер выводит в `.obj` **несогласованный регистр**:

- `symbols` (таблица символов) — в **исходном** регистре (например, `main`, `helper`);
- `relocations` и `imports` — в **UPPER**-ключе (например, `MAIN`, `HELPER`),
  потому что `_track_relocation(...)` и `_imports.add(...)` получают `self._sym_key(name)`,
  а в case-insensitive режиме `_sym_key` возвращает `name.upper()`.

Линкер (`assemble8080/linker.py`) делает **точное** сопоставление имён
(`global_symbols.get(reloc.symbol)`, `imp not in global_symbols`), без нормализации регистра.

Последствие: ссылка из одного модуля на символ другого модуля **не разрешается**,
если исходный регистр определения отличается от UPPER-ключа ссылки.

### Минимальный воспроизводящий пример

Модуль A (определяет `main`, вызывает `helper`):
```asm
main:
    call helper
    ret
```
Модуль B (определяет `helper`):
```asm
helper:
    mvi a,0
    ret
```

Сборка каждого в `.obj` (case-insensitive, по умолчанию) даёт:
- `A.obj`: `symbols={'main':0}`, `imports=['HELPER']`, `relocations=[(1,2,'HELPER',0)]`
- `B.obj`: `symbols={'helper':0}`

Линковка `A + B`:
```
LINK FAIL: Unresolved symbol: HELPER (imported by A)
```
Хотя `helper` определён в B — линкер ищет `HELPER` (UPPER), а в B лежит `helper` (lower).

### Влияние на пайплайн

В пайплайне runtime (`test_crun.obj`) через `cstart` вызывает `main` теста.
- relocation runtime: `MAIN` (UPPER);
- символ теста: `main` (lower, исходный регистр).
→ `Unresolved symbol: MAIN` → **все тесты с `main` не линкуются** (56 из 97).

До введения case-sensitivity всё работало, потому что ассемблер выводил ВСЁ в UPPER
(и символы, и relocation'ы) — точное сопоставление сходилось.

## Что нужно исправить

Сделать сопоставление символов в линкере **независимым от регистра** в режиме case-insensitive,
чтобы это соответствовало задокументированному поведению (`main`/`Main`/`MAIN` — один символ).

Рекомендуемый вариант (наиболее робастный):

1. **Линкер нормализует регистр при сопоставлении** (case-insensitive режим):
   - при построении `global_symbols` / `all_symbols` ключи приводить к UPPER;
   - при проверке imports и применении relocations lookup-имя приводить к UPPER.
   - Тогда `HELPER` (relocation/import) найдёт `helper` (symbol).

2. **Режим case-sensitive** (`--case-sensitive`):
   - добавить в `.obj` флаг `case_sensitive` (bool, по умолчанию `False`);
   - ассемблер выставляет его по `Assembler.case_sensitive`;
   - линкер: если `case_sensitive=True` — точное сопоставление (без нормализации),
     если `False` — нормализация к UPPER.

Альтернативный (менее робастный) вариант: ассемблер выводит `relocations`/`imports`
в том же регистре, что и `symbols` (исходный). Но это хрупко: регистр *ссылки* может
отличаться от регистра *определения* (`shld I` vs `i:`), и в case-insensitive режиме
они обязаны совпадать независимо от регистра. Поэтому нормализация в линкере предпочтительнее.

## Проверка после фикса

1. Минимальный кросс-модульный кейс выше: `A + B` линкуется, `call helper`
   патчится на адрес `helper` в B.
2. Пайплайн: все тесты с `main` линкуются (исчезает `Unresolved symbol: MAIN`).
3. Режим `--case-sensitive`: `i` и `I` остаются разными символами
   (ссылка на `I` при определении `i` → unresolved).
4. Существующие тесты ассемблера (`_test_case.py`, `_test_alu_imm.py`) продолжают проходить.

## Что НЕ нужно менять

- Фикс размера ALU-immediate в pass 1 — уже корректен, не трогать.
- Сохранение исходного регистра в `symbols`/map/`.obj` — это задокументированное поведение,
  не откатывать в UPPER.
- Компилятор `cc8080` и тестовые `.s` — не относятся к `i8080_ci`.

## Файлы

- `assemble8080/assembler.py` — `_sym_key`, `_store_symbol`, `_track_relocation`,
  вывод `AsmResult` (symbols в исходном регистре, relocations/imports в UPPER-ключе).
- `assemble8080/linker.py` — `link()`: построение `global_symbols`/`all_symbols`,
  проверка imports, применение relocations (точное сопоставление).
- `assemble8080/objfile.py` — сериализация `.obj` (при добавлении флага `case_sensitive`).
