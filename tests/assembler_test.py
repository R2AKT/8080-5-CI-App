"""Тест препроцессора и расширенного ассемблера"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assemble8080.assembler import Assembler

# Тест 1: Псевдокоманды с точкой
source1 = """
    .org 0x100
    mvi a, 0x55
    out 0x01
    .db 0x12, 0x34
    .dw 0x1234
    .ds 4
    .end
"""
asm = Assembler()
result = asm.assemble(source1)
print(f"Тест 1 (.org, .db, .dw, .ds): {'✅' if result.success else '❌'}")
print(f"   Размер: {len(result.binary)} байт")

# Тест 2: #define и #if
source2 = """
#define PORT_A 0x01
#define USE_LED 1

#if USE_LED
    mvi a, 0xFF
    out PORT_A
#else
    mvi a, 0x00
    out PORT_A
#endif
"""
result2 = asm.assemble(source2)
print(f"Тест 2 (#define, #if): {'✅' if result2.success else '❌'}")

# Тест 3: Метки с :: и :
source3 = """
start::
    mvi a, 0x01
local_loop:
    dcr a
    jnz local_loop
    jmp start
"""
result3 = asm.assemble(source3)
print(f"Тест 3 (метки :: и :): {'✅' if result3.success else '❌'}")
print(f"   Метки: {result3.symbols}")

# Тест 4: Математические выражения
source4 = """
    mvi a, 5 + 3 * 2      ; = 11
    mvi b, 10 - 2         ; = 8
    mvi c, 0x10 + 0x20    ; = 0x30
"""
result4 = asm.assemble(source4)
print(f"Тест 4 (математика): {'✅' if result4.success else '❌'}")

# Тест 5: Макросы
source5 = """
LOAD_A MACRO value
    mvi a, value
ENDM

    LOAD_A 0x42
"""
result5 = asm.assemble(source5)
print(f"Тест 5 (макросы): {'✅' if result5.success else '❌'}")

# Тест 6: Недокументированные команды 8085
source6 = """
    .8085
    .org 0x100
    dsub b      ; Вычитание пары регистров
    arhl        ; Арифметический сдвиг
    lhlx        ; Загрузка из памяти
    shlx        ; Сохранение в память
    ldhi 0x10   ; Загрузка из памяти с инкрементом
    ldsi 0x10   ; Загрузка из памяти с инкрементом
"""
result6 = asm.assemble(source6)
print(f"Тест 6 (недокументированные команды 8085): {'✅' if result6.success else '❌'}")

print("\nВсе тесты завершены")