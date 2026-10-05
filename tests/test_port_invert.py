#!/usr/bin/env python3
"""
Комплексный тест port_invert для Микро-80.
Проверяет полный путь: CPU → MemoryBus → port_invert → I8255 → Keyboard8x8
"""
import sys
sys.path.insert(0, '.')

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  \u2705 {name}")
        passed += 1
    else:
        print(f"  \u274c {name}: ожидалось {expected}, получено {actual}")
        failed += 1

# =============================================
# ТЕСТ 1: Port inversion map
# =============================================
print("\nТест 1: Порт-инверсия в MemoryBus")
print("-" * 50)

from modules.memory.memory_bus import MemoryBus, RAMRegion

bus = MemoryBus()
ram = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus.register_memory(ram)

from modules.io import I8255
ppi = I8255(base_port=0x04)
ppi.register_to_bus(bus)

# Register IO ports
num_ports = 4
for offset in range(num_ports):
    port = 0x04 + offset
    bus.register_io(port, ppi)

# Build inversion map (as system.py does)
base = 0x04
for offset in range(num_ports):
    port = base + offset
    inverted_port = base + (num_ports - 1 - offset)
    bus._port_invert_map[port] = inverted_port

# Verify map
print(f"  Map: { {hex(k): hex(v) for k,v in bus._port_invert_map.items()} }")
check("0x04 → 0x07", bus._port_invert_map[0x04], 0x07)
check("0x05 → 0x06", bus._port_invert_map[0x05], 0x06)
check("0x06 → 0x05", bus._port_invert_map[0x06], 0x05)
check("0x07 → 0x04", bus._port_invert_map[0x07], 0x04)

# =============================================
# ТЕСТ 2: IO Write через инверсию
# =============================================
print("\nТест 2: IO Write через инверсию")
print("-" * 50)

# Set control word: all output, Mode 0
# CPU writes to 0x04 → maps to device port 0x07 (offset 3 = Control)
bus.io_write(0x04, 0x80)  # 1000 0000 = all output, Mode 0
check("Control через инверсию: PPI.ctrl", ppi.control, 0x80)

# Write to Port A: CPU writes to 0x07 → maps to device port 0x04 (offset 0 = Port A)
bus.io_write(0x07, 0x01)
check("Port A через инверсию: CPU 0x07 → PPI Port A", ppi.port_a, 0x01)

# Write to Port B: CPU writes to 0x06 → maps to device port 0x05 (offset 1 = Port B)
bus.io_write(0x06, 0x02)
check("Port B через инверсию: CPU 0x06 → PPI Port B", ppi.port_b, 0x02)

# Write to Port C: CPU writes to 0x05 → maps to device port 0x06 (offset 2 = Port C)
bus.io_write(0x05, 0x03)
check("Port C через инверсию: CPU 0x05 → PPI Port C", ppi.port_c, 0x03)

# =============================================
# ТЕСТ 3: IO Read через инверсию
# =============================================
print("\nТест 3: IO Read через инверсию")
print("-" * 50)

# Set input mode for Port A: 1001 0000 = 0x90 (Mode 0, A=input, B=output)
bus.io_write(0x04, 0x90)  # CPU 0x04 → device 0x07 → Control (bit 7=1 → mode set)
check("Control set to 0x90", ppi.control, 0x90)

# Set external input for Port A (simulating keyboard)
ppi.set_external_input(0, 0xAB)

# CPU reads 0x07 → maps to device port 0x04 (Port A) → should return 0xAB
val = bus.io_read(0x07)
check("Read Port A через инверсию: CPU 0x07", val, 0xAB)

# Verify direct access still works
check("Direct PPI.io_read(0x04) = Port A", ppi.io_read(0x04), 0xAB)
check("Direct PPI.io_read(0x07) = Control", ppi.io_read(0x07), 0x90)

# =============================================
# ТЕСТ 4: Keyboard8x8 + port_invert (full integration)
# =============================================
print("\nТест 4: Keyboard8x8 + port_invert (интеграция)")
print("-" * 50)

from modules.io.keyboard8x8 import Keyboard8x8

# New PPI for keyboard test
ppi2 = I8255(base_port=0x04)
ppi2.register_to_bus(bus)  # Re-register (replaces old)
for offset in range(num_ports):
    bus.register_io(0x04 + offset, ppi2)

kbd = Keyboard8x8(name="TestKeyboard")
kbd.connect_to_ppi(ppi2, output_port=0, input_port=1)

# Set mode: Port A output (row select), Port B input (columns)
# 1000 0001 = 0x81: Mode 0, A=output, B=input
# CPU writes control via inverted port 0x04 → device port 0x07 (Control)
bus.io_write(0x04, 0x81)
check("Control word: 0x81 (A=out, B=in)", ppi2.control, 0x81)

# Press key at row=2, col=5
kbd.press_key(2, 5)

# CPU selects row 2: writes to physical port 0x07 → device Port A
bus.io_write(0x07, 0x02)  # Row 2
check("current_row = 2", kbd.current_row, 2)

# CPU reads columns: reads physical port 0x06 → device Port B
col_data = bus.io_read(0x06)
expected_col = kbd.scan_row(2)
check("Column data через инверсию", col_data, expected_col)
check("Bit 5 = 0 (key pressed)", col_data & (1 << 5), 0)
check("Other bits = 1 (key released)", (col_data | (1 << 5)) & 0xFF, 0xFF)

# Release key
kbd.release_key(2, 5)
bus.io_write(0x07, 0x02)  # Re-select row 2
col_data2 = bus.io_read(0x06)
check("After release: all bits = 1", col_data2, 0xFF)

# =============================================
# ТЕСТ 5: Reset (MemoryBus.reset_all через новый bus)
# =============================================
print("\nТест 5: Reset")
print("-" * 50)

# Simulate reset by creating new bus (as reset_all does)
new_bus = MemoryBus()
check("New bus: port_invert_map empty", len(new_bus._port_invert_map), 0)
check("Old bus: port_invert_map still has entries", len(bus._port_invert_map), 4)

# =============================================
# ТЕСТ 6: Профиль micro80 (полная загрузка)
# =============================================
print("\nТест 6: Загрузка профиля micro80")
print("-" * 50)

from modules.system import ComputerSystem

system = ComputerSystem()
system.load_profile("micro80")

# Check that PPI exists
ppi_sys = system.devices.get("PPI")
check("PPI создан", ppi_sys is not None, True)

if ppi_sys:
    check("PPI base_port = 0x04", ppi_sys.base_port, 0x04)
    
    # Check inversion map
    check("Invert map exists", len(system.bus._port_invert_map), 4)
    check("Map 0x04→0x07", system.bus._port_invert_map.get(0x04), 0x07)
    check("Map 0x07→0x04", system.bus._port_invert_map.get(0x07), 0x04)

# Check keyboard connected
kbd_sys = system.devices.get("Keyboard")
check("Keyboard создан", kbd_sys is not None, True)

# Check RAM regions
check("RAM 16KB регион", system.bus.memory_regions[0].name, "RAM 16KB")
# Profile defines: RAM, ROM, Video RAM
region_names = [r.name for r in system.bus.memory_regions]
check("Video RAM в регионах", "Video RAM" in region_names, True)
check("Monitor ROM в регионах", "Monitor ROM" in region_names, True)

# =============================================
# ИТОГО
# =============================================
print("\n" + "=" * 50)
total = passed + failed
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено (из {total})")
print("=" * 50)

if failed:
    print(" \u274c Есть проваленные тесты.")
    sys.exit(1)
else:
    print(" \u2705 Все тесты пройдены!")
