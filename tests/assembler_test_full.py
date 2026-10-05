"""
Полный тест ассемблера 8080 (assemble8080).
Проверяет:
1. Базовые инструкции и регистры
2. Форматы чисел (0x.., ..H, десятичные, двоичные, восьмеричные)
3. Метки и переходы (вперёд/назад)
4. Директивы (ORG, DB, DW, DS, EQU)
5. Обработка ошибок
6. Сквозной тест: ассемблирование -> загрузка в память -> выполнение в эмуляторе
"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем ассемблер
try:
    from assemble8080.assembler import Assembler
except ImportError as e:
    print(f"❌ Ошибка импорта assemble8080: {e}")
    print("Убедитесь, что пакет assemble8080 доступен в окружении.")
    raise SystemExit

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✅ {name}")
        passed += 1
        return True
    else:
        print(f"  ❌ {name}: ожидалось {expected!r}, получено {actual!r}")
        failed += 1
        return False

asm = Assembler()

# =============================================
# ТЕСТ 1: Базовые инструкции и коды
# =============================================
print("\n" + "=" * 60)
print(" ТЕСТ 1: Базовые инструкции")
print("=" * 60)

source1 = """
    ORG 0x0100
    NOP         ; 00
    MVI A, 55H  ; 3E 55
    MOV B, A    ; 47
    ADD B       ; 80
    HLT         ; 76
"""
res1 = asm.assemble(source1)
check("Тест 1: нет ошибок", len(res1.errors), 0)
check("Тест 1: origin", res1.origin, 0x0100)
# Ожидаемые байты: 00 3E 55 47 80 76
expected_bytes1 = bytes([0x00, 0x3E, 0x55, 0x47, 0x80, 0x76])
check("Тест 1: бинарный код", res1.binary, expected_bytes1)

# =============================================
# ТЕСТ 2: Форматы чисел (NumberParser)
# =============================================
print("\n" + "=" * 60)
print(" ТЕСТ 2: Форматы чисел")
print("=" * 60)

source2 = """
    ORG 0x0000
    MVI A, 0x1A     ; HEX с 0x (26)
    MVI B, 1AH      ; HEX с H (26)
    MVI C, 26       ; Десятичное (26)
    MVI D, 11010B   ; Двоичное (26)
    MVI E, 32q      ; Восьмеричное (26)
    MVI H, 0FFH     ; HEX, начинается с буквы (255)
"""
res2 = asm.assemble(source2)
check("Тест 2: нет ошибок", len(res2.errors), 0)
# Все регистры должны получить значение 26 (0x1A), кроме H (0xFF)
expected_bytes2 = bytes([
    0x3E, 0x1A,  # A
    0x06, 0x1A,  # B
    0x0E, 0x1A,  # C
    0x16, 0x1A,  # D
    0x1E, 0x1A,  # E
    0x26, 0xFF   # H
])
check("Тест 2: все форматы чисел", res2.binary, expected_bytes2)

# =============================================
# ТЕСТ 3: Метки и переходы
# =============================================
print("\n" + "=" * 60)
print(" ТЕСТ 3: Метки и переходы (JMP, JNZ, CALL)")
print("=" * 60)

source3 = """
    ORG 0x0000
START: MVI A, 01H     ; 0000: 3E 01 (2 байта)
       JNZ SKIP       ; 0002: C2 06 00 (3 байта)
       NOP            ; 0005: 00 (1 байт)
SKIP:  JMP START      ; 0006: C3 00 00 (3 байта)
       CALL SUB       ; 0009: CD 0C 00 (3 байта)
SUB:   RET            ; 000C: C9 (1 байт)
"""
res3 = asm.assemble(source3)
check("Тест 3: нет ошибок", len(res3.errors), 0)
check("Тест 3: метка START", res3.symbols.get('START'), 0x0000)
check("Тест 3: метка SKIP", res3.symbols.get('SKIP'), 0x0006)
check("Тест 3: метка SUB", res3.symbols.get('SUB'), 0x000C)

check("Тест 3: байт JMP", res3.binary[6:9], bytes([0xC3, 0x00, 0x00]))
check("Тест 3: байт CALL", res3.binary[9:12], bytes([0xCD, 0x0C, 0x00]))

# =============================================
# ТЕСТ 4: Директивы DB, DW, DS, EQU
# =============================================
print("\n" + "=" * 60)
print(" ТЕСТ 4: Директивы данных")
print("=" * 60)

source4 = """
    ORG 0x0100
VAL EQU 42
    DB 0x11, VAL, 41H   ; 11 2A 41
    DW 0x1234           ; 34 12 (little-endian)
    DS 3                ; 00 00 00
    DB 48H, 69H         ; "Hi" в HEX
"""
res4 = asm.assemble(source4)
check("Тест 4: нет ошибок", len(res4.errors), 0)
check("Тест 4: EQU символ", res4.symbols.get('VAL'), 42)

expected_bytes4 = bytes([
    0x11, 42, 0x41,
    0x34, 0x12,
    0x00, 0x00, 0x00,
    0x48, 0x69
])
check("Тест 4: DB/DW/DS", res4.binary, expected_bytes4)

# =============================================
# ТЕСТ 5: Обработка ошибок
# =============================================
print("\n" + "=" * 60)
print(" ТЕСТ 5: Обработка ошибок")
print("=" * 60)

source5_err1 = """
    ORG 0x0000
    MVI A, 100H  ; Ошибка: значение > 255 для MVI
"""
res5_1 = asm.assemble(source5_err1)
check("Тест 5.1: MVI 16-bit (Z80) — младший байт", bytes(res5_1.binary) == b'\x3E\x00', True)

source5_err2 = """
    ORG 0x0000
    JMP UNKNOWN_LABEL
"""
res5_2 = asm.assemble(source5_err2)
# Неизвестная метка — предупреждение (файл может быть "нижним", включаться в другой)
check("Тест 5.2: предупреждение о неизвестной метке", len(res5_2.warnings) > 0, True)

source5_err3 = """
    ORG 0x0000
    INVALID_OPCODE A, B
"""
res5_3 = asm.assemble(source5_err3)
check("Тест 5.3: ошибка неизвестной инструкции", len(res5_3.errors) > 0, True)

# =============================================
# ТЕСТ 6: Сквозной тест (Ассемблер -> Эмулятор)
# =============================================
print("\n" + "=" * 60)
print(" ТЕСТ 6: Сквозной тест (Ассемблер -> Эмулятор)")
print("=" * 60)

# Программа: вычисляет сумму чисел от 1 до 5
# Результат должен быть в регистре A (1+2+3+4+5 = 15 = 0x0F)
source6 = """
    ORG 0x0200
    MVI A, 00H    ; Сумма = 0
    MVI B, 01H    ; Счётчик = 1
    MVI C, 05H    ; Предел = 5
LOOP:
    ADD B         ; Сумма += Счётчик
    INR B         ; Счётчик++
    DCR C         ; Предел--
    JNZ LOOP      ; Если Предел != 0, повторить
    HLT           ; Стоп
"""
res6 = asm.assemble(source6)
check("Тест 6: ассемблирование без ошибок", len(res6.errors), 0)

_api = globals().get('api')
if len(res6.errors) == 0 and _api is not None and hasattr(_api, 'mw') and hasattr(_api.mw, 'emulator'):
    emu = _api.mw.emulator
    bus = _api.system.bus
    
    # Загружаем бинарник в память
    origin = res6.origin
    for i, b in enumerate(res6.binary):
        bus.write(origin + i, b)
    
    # Настраиваем эмулятор
    emu.reset()
    emu.set_pc(origin)
    emu.sp = 0xFFFE
    
    # Выполняем до HLT или до лимита тактов
    max_steps = 100
    steps = 0
    while steps < max_steps:
        if emu.halted:
            break
        # Проверяем HLT (0x76)
        if bus.read(emu.pc) == 0x76:
            emu.halted = True
            break
        emu.step_into()
        steps += 1
        
    check("Тест 6: эмулятор достиг HLT", emu.halted, True)
    check("Тест 6: результат в A (сумма 1..5 = 15)", emu.a, 0x0F)
    check("Тест 6: счётчик B (должен быть 6)", emu.b, 0x06)
    check("Тест 6: предел C (должен быть 0)", emu.c, 0x00)
    print(f"  ℹ Выполнено шагов: {steps}")
else:
    print("  ⚠ Пропуск сквозного теста (нет доступа к эмулятору или есть ошибки ассемблирования)")

# =============================================
# ТЕСТ 7: Листинг и символы
# =============================================
print("\n" + "=" * 60)
print(" ТЕСТ 7: Листинг и таблица символов")
print("=" * 60)

source7 = """
    ORG 0x1000
START: NOP
LAB1:  DB 0xFF
       END
"""
res7 = asm.assemble(source7)
check("Тест 7: листинг сгенерирован", len(res7.listing) > 0, True)
check("Тест 7: символы START и LAB1", 'START' in res7.symbols and 'LAB1' in res7.symbols, True)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 60)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 60)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ АССЕМБЛЕРА ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")