"""Тест Специалиста 384×256: геометрические фигуры (монохром)"""
import math

dev = None
bus = api.system.bus
for d in api.system.devices.values():
    if type(d).__name__ == 'BitmapVideo':
        dev = d
        break

if dev is None:
    print("❌ BitmapVideo не найден!")
    raise SystemExit

W = dev.width      # 384
H = dev.height     # 256
bpl = dev.bytes_per_line()   # 48
ADDR = dev.video_addr
BIT0_LEFT = dev.bit0_left
print(f"✅ BitmapVideo: {W}×{H}, адрес 0x{ADDR:04X}, байт/строку {bpl}")

def set_pixel(x, y, on=True):
    if 0 <= x < W and 0 <= y < H:
        byte_off = y * bpl + x // 8
        bit = x % 8
        mask = (1 << bit) if BIT0_LEFT else (1 << (7 - bit))
        old = bus.read(ADDR + byte_off)
        bus.write(ADDR + byte_off, (old | mask) if on else (old & ~mask))

def clear_screen():
    for i in range(bpl * H):
        bus.write(ADDR + i, 0x00)

def draw_line(x0, y0, x1, y1):
    dx, dy = abs(x1-x0), -abs(y1-y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        set_pixel(x0, y0)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy

def draw_rect(x, y, w, h):
    draw_line(x, y, x+w, y); draw_line(x+w, y, x+w, y+h)
    draw_line(x+w, y+h, x, y+h); draw_line(x, y+h, x, y)

def draw_triangle(x0, y0, x1, y1, x2, y2):
    draw_line(x0, y0, x1, y1); draw_line(x1, y1, x2, y2); draw_line(x2, y2, x0, y0)

def draw_circle(cx, cy, r):
    x, y, d = 0, r, 3 - 2*r
    while x <= y:
        for px, py in [(cx+x,cy+y),(cx-x,cy+y),(cx+x,cy-y),(cx-x,cy-y),
                       (cx+y,cy+x),(cx-y,cy+x),(cx+y,cy-x),(cx-y,cy-x)]:
            set_pixel(px, py)
        if d < 0:
            d += 4*x + 6
        else:
            d += 4*(x-y) + 10; y -= 1
        x += 1

clear_screen()
draw_rect(0, 0, W-1, H-1)            # рамка экрана

# Верхний ряд
draw_rect(25, 20, 70, 70)            # квадрат
draw_triangle(150, 90, 190, 20, 230, 90)   # треугольник
draw_circle(310, 55, 35)             # окружность

# Синусоида
for x in range(20, 364):
    y = int(125 + 20 * math.sin((x-20) * 2 * math.pi / 68))
    set_pixel(x, y)

# Меандр
y_top, y_bot, period = 160, 190, 34
x, level = 20, 0
while x < 364:
    seg_end = min(x + period//2, 364)
    y = y_top if level == 0 else y_bot
    for xx in range(x, seg_end):
        set_pixel(xx, y)
    if seg_end < 364:
        draw_line(seg_end-1, y_top, seg_end-1, y_bot)
    x = seg_end
    level = 1 - level

# Треугольный сигнал
y_base, amp, period = 240, 25, 44
for x in range(20, 364):
    phase = (x - 20) % period
    half = period // 2
    if phase < half:
        y = y_base - int(phase * amp / half)
    else:
        y = y_base - int((period - phase) * amp / half)
    set_pixel(x, y)

print("\n✅ Нарисовано на экране 384×256:")
print("   квадрат, треугольник, окружность (верх)")
print("   синусоида, меандр, треугольный сигнал (низ)")
print("   📺 Откройте окно Video из Диспетчера устройств")