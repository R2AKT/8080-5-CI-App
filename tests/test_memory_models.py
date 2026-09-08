"""Тест PagedRegion, SegmentedRegion, SegmentedPagedRegion (итерация E2)"""
from modules import MemoryBus, PagedRegion, SegmentedRegion, SegmentedPagedRegion

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}: ожидалось {expected}, получено {actual}")
        failed += 1

# =============================================
# ТЕСТ 1: PagedRegion — страничная память
# =============================================
print("\nТест 1: PagedRegion — страничная память")
print("-" * 50)

bus = MemoryBus()
paged = PagedRegion(
    0x0000, 0xFFFF,
    page_size=16384,          # 16КБ на страницу
    num_physical_pages=16,    # 16 физических страниц = 256КБ
    switch_ports=[0x00, 0x01, 0x02, 0x03],  # Порты для 4 виртуальных страниц
    name="PagedRAM"
)
bus.register_memory(paged)

# Запись в виртуальную страницу 0 (физическая страница 0)
bus.write(0x0000, 0xAA)
check("Запись в страницу 0", bus.read(0x0000), 0xAA)

# Переключаем виртуальную страницу 0 на физическую страницу 1
bus.io_write(0x00, 1)
check("Страница 0 -> физическая 1 (пусто)", bus.read(0x0000), 0x00)

# Запись в физическую страницу 1
bus.write(0x0000, 0xBB)
check("Запись в физическую 1", bus.read(0x0000), 0xBB)

# Возвращаем на физическую страницу 0
bus.io_write(0x00, 0)
check("Возврат на физическую 0", bus.read(0x0000), 0xAA)

# Запись в виртуальную страницу 1 (независимо от страницы 0)
bus.write(0x4000, 0xCC)
check("Запись в страницу 1", bus.read(0x4000), 0xCC)
check("Страница 0 не изменилась", bus.read(0x0000), 0xAA)

# =============================================
# ТЕСТ 2: SegmentedRegion — сегментная память
# =============================================
print("\nТест 2: SegmentedRegion — сегментная память")
print("-" * 50)

bus2 = MemoryBus()
segmented = SegmentedRegion(
    0x0000, 0xFFFF,
    num_segments=16,      # 16 сегментов по 64КБ = 1МБ
    switch_port=0x10,     # Порт для переключения сегмента
    name="SegmentedRAM"
)
bus2.register_memory(segmented)

# Запись в сегмент 0
bus2.write(0x0000, 0x11)
check("Запись в сегмент 0", bus2.read(0x0000), 0x11)

# Переключаем на сегмент 1
bus2.io_write(0x10, 1)
check("Сегмент 1 (пусто)", bus2.read(0x0000), 0x00)

# Запись в сегмент 1
bus2.write(0x0000, 0x22)
check("Запись в сегмент 1", bus2.read(0x0000), 0x22)

# Возврат на сегмент 0
bus2.io_write(0x10, 0)
check("Возврат на сегмент 0", bus2.read(0x0000), 0x11)

# =============================================
# ТЕСТ 3: SegmentedPagedRegion — сегментно-страничная память
# =============================================
print("\nТест 3: SegmentedPagedRegion — сегментно-страничная")
print("-" * 50)

bus3 = MemoryBus()
seg_paged = SegmentedPagedRegion(
    0x0000, 0xFFFF,
    segment_size=16384,       # 16КБ на сегмент
    num_physical_pages=16,    # 16 физических страниц = 256КБ
    base_port=0x00,           # Порты 0x00-0x03 для 4 сегментов
    name="SegmentedPagedRAM"
)
bus3.register_memory(seg_paged)

# Запись в сегмент 0 (физическая страница 0)
bus3.write(0x0000, 0xAA)
check("Запись в сегмент 0", bus3.read(0x0000), 0xAA)

# Переключаем сегмент 0 на физическую страницу 1
bus3.io_write(0x00, 1)
check("Сегмент 0 -> физическая 1 (пусто)", bus3.read(0x0000), 0x00)

# Запись в физическую страницу 1
bus3.write(0x0000, 0xBB)
check("Запись в физическую 1", bus3.read(0x0000), 0xBB)

# Возврат на физическую страницу 0
bus3.io_write(0x00, 0)
check("Возврат на физическую 0", bus3.read(0x0000), 0xAA)

# Запись в сегмент 1 (независимо от сегмента 0)
bus3.write(0x4000, 0xCC)
check("Запись в сегмент 1", bus3.read(0x4000), 0xCC)
check("Сегмент 0 не изменился", bus3.read(0x0000), 0xAA)

# Переключаем сегмент 1 на физическую страницу 5
bus3.io_write(0x01, 5)
check("Сегмент 1 -> физическая 5 (пусто)", bus3.read(0x4000), 0x00)

# Возврат сегмента 1 на физическую страницу 1
bus3.io_write(0x01, 1)
check("Сегмент 1 -> физическая 1", bus3.read(0x4000), 0xCC)

# =============================================
# ТЕСТ 4: Сброс
# =============================================
print("\nТест 4: Сброс")
print("-" * 50)

paged.reset()
check("PagedRegion reset", paged.page_table, [0, 1, 2, 3])

segmented.reset()
check("SegmentedRegion reset", segmented.current_segment, 0)

seg_paged.reset()
check("SegmentedPagedRegion reset", seg_paged.segment_table, [0, 1, 2, 3])

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
