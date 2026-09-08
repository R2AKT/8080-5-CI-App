"""
3D Тетрис на кубе 8×8×8 — работа через порты 8255.
Итерация 12.11: реальная игровая логика, отрисовка через 8255.

Особенности:
- Реальная генерация случайных фигур (поликубики ≤ 3×3×3)
- Фигуры падают вниз по оси Y
- ИИ размещает фигуры для заполнения плоскостей
- Заполненная плоскость удаляется (без вспышки)
- Отрисовка через порты 8255 (окно 8255 показывает активность)
- Без призраков и визуальных эффектов

Управление:
  api.mw._cube3d_timer.stop()   — остановить тетрис
"""
import random
from PySide6.QtCore import QTimer

# =============================================
# ШАГ 1: ПОИСК УСТРОЙСТВ И ОТКРЫТИЕ ВИДЖЕТА
# =============================================
ppi = None
cube_dev = None

for d in api.system.devices.values():
    cls = type(d).__name__
    if cls == 'I8255' and ppi is None:
        ppi = d
    elif cls == 'Cube3D' and cube_dev is None:
        cube_dev = d

if ppi is None:
    print("❌ 8255 не найден! Добавьте 8255 в профиль.")
    raise SystemExit

print(f"✅ 8255 @ 0x{ppi.base_port:02X}")
if cube_dev is not None:
    print(f"✅ Cube3D: {cube_dev.name}")

from ui.cube3d_widget import Cube3DWidget

if hasattr(api.mw, '_cube3d_widget') and api.mw._cube3d_widget is not None:
    cube_widget = api.mw._cube3d_widget
else:
    target = cube_dev if cube_dev is not None else ppi
    cube_widget = Cube3DWidget(target)
    cube_widget.setWindowTitle("3D Куб 8×8×8 — Тетрис")
    cube_widget.resize(640, 600)
    api.mw._cube3d_widget = cube_widget

cube_widget.show()
cube_widget.raise_()
cube_widget.activateWindow()

# Настройка для тетриса
cube_widget.set_persist(False)          # Без автозатухания
cube_widget.set_color(80, 200, 255)     # Голубой

# =============================================
# ШАГ 2: НАСТРОЙКА 8255
# =============================================
base = ppi.base_port
ppi.io_write(base + 3, 0x80)  # Все порты на выход
print(f"📡 8255 настроен: все порты на выход")

# =============================================
# ШАГ 3: ФИГУРЫ (поликубики в коробке 3×3×3)
# =============================================
PIECES = [
    [(0,0,0), (1,0,0), (2,0,0)],                                   # палка X
    [(0,0,0), (0,0,1), (0,0,2)],                                   # палка Z
    [(0,0,0), (1,0,0), (0,0,1)],                                   # малый уголок
    [(0,0,0), (1,0,0), (2,0,0), (2,0,1)],                          # L
    [(0,0,0), (1,0,0), (2,0,0), (0,0,1)],                          # обратная L
    [(0,0,0), (1,0,0), (2,0,0), (1,0,1)],                          # T
    [(0,0,0), (1,0,0), (0,0,1), (1,0,1)],                          # квадрат 2×2
    [(0,0,0), (1,0,0), (1,0,1), (2,0,1)],                          # S
    [(0,0,0), (1,0,0), (0,0,1), (0,1,0)],                          # 3D уголок
    [(1,0,0), (0,0,1), (1,0,1), (2,0,1), (1,0,2)],                 # крест
    [(0,0,0), (1,0,0), (2,0,0), (0,0,1), (1,0,1), (2,0,1)],        # пластина 2×3
]

def rotate_piece(cells):
    """Поворот на 90° вокруг вертикальной оси Y"""
    rotated = [(z, y, -x) for (x, y, z) in cells]
    min_x = min(c[0] for c in rotated)
    min_z = min(c[2] for c in rotated)
    return [(x - min_x, y, z - min_z) for (x, y, z) in rotated]

def all_rotations(cells):
    """Все уникальные повороты фигуры"""
    results = []
    seen = set()
    cur = list(cells)
    for _ in range(4):
        key = tuple(sorted(cur))
        if key not in seen:
            seen.add(key)
            results.append(list(cur))
        cur = rotate_piece(cur)
    return results

# =============================================
# ШАГ 4: ИГРОВОЙ ДВИЖОК
# =============================================
SIZE = 8

class Tetris3D:
    def __init__(self):
        self.reset()

    def reset(self):
        """Полный сброс игры"""
        self.field = [[[0]*SIZE for _ in range(SIZE)] for _ in range(SIZE)]
        self.score = 0
        self.planes_cleared = 0
        self.pieces_placed = 0
        self.current = None
        self.cur_pos = None
        self.target_y = None
        self.state = 'NEW_PIECE'

    # ---------- Коллизии ----------
    def collides(self, cells, px, py, pz):
        for (cx, cy, cz) in cells:
            x, y, z = px + cx, py + cy, pz + cz
            if x < 0 or x >= SIZE or z < 0 or z >= SIZE or y < 0 or y >= SIZE:
                return True
            if self.field[x][y][z]:
                return True
        return False

    def drop_y(self, cells, px, pz):
        max_cy = max(c[1] for c in cells)
        py = SIZE - 1 - max_cy
        if self.collides(cells, px, py, pz):
            return None
        while py > 0 and not self.collides(cells, px, py - 1, pz):
            py -= 1
        return py

    # ---------- ИИ: оценка размещения ----------
    def evaluate(self, cells, px, py, pz):
        placed = []
        for (cx, cy, cz) in cells:
            x, y, z = px + cx, py + cy, pz + cz
            self.field[x][y][z] = 1
            placed.append((x, y, z))

        score = 0
        # Бонус за заполненные плоскости
        for y in range(SIZE):
            if all(self.field[x][y][z] for x in range(SIZE) for z in range(SIZE)):
                score += 1000
        # Штраф за суммарную высоту
        agg = 0
        for x in range(SIZE):
            for z in range(SIZE):
                for y in range(SIZE - 1, -1, -1):
                    if self.field[x][y][z]:
                        agg += (y + 1)
                        break
        score -= agg * 3
        # Штраф за дырки
        holes = 0
        for x in range(SIZE):
            for z in range(SIZE):
                seen = False
                for y in range(SIZE - 1, -1, -1):
                    if self.field[x][y][z]:
                        seen = True
                    elif seen:
                        holes += 1
        score -= holes * 15

        for (x, y, z) in placed:
            self.field[x][y][z] = 0
        return score

    def find_best_placement(self, cells):
        best = None
        best_score = None
        for rot in all_rotations(cells):
            max_cx = max(c[0] for c in rot)
            max_cz = max(c[2] for c in rot)
            for px in range(SIZE - max_cx):
                for pz in range(SIZE - max_cz):
                    py = self.drop_y(rot, px, pz)
                    if py is None:
                        continue
                    s = self.evaluate(rot, px, py, pz)
                    if best_score is None or s > best_score:
                        best_score = s
                        best = {'cells': rot, 'x': px, 'y': py, 'z': pz}
        return best

    # ---------- Игровой шаг ----------
    def new_piece(self):
        cells = random.choice(PIECES)
        best = self.find_best_placement(cells)
        if best is None:
            print("🔄 Стек заполнен — начинаем заново")
            self.reset()
            return
        self.current = best['cells']
        max_cy = max(c[1] for c in self.current)
        self.cur_pos = (best['x'], SIZE - 1 - max_cy, best['z'])
        self.target_y = best['y']
        self.state = 'FALLING'

    def lock_piece(self):
        px, py, pz = self.cur_pos
        for (cx, cy, cz) in self.current:
            x, y, z = px + cx, py + cy, pz + cz
            if 0 <= x < SIZE and 0 <= y < SIZE and 0 <= z < SIZE:
                self.field[x][y][z] = 1
        self.score += len(self.current)
        self.pieces_placed += 1
        self.current = None
        self.cur_pos = None

    def plane_full(self, y):
        return all(self.field[x][y][z] for x in range(SIZE) for z in range(SIZE))

    def remove_planes(self, ys):
        ys = set(ys)
        new_field = [[[0]*SIZE for _ in range(SIZE)] for _ in range(SIZE)]
        for x in range(SIZE):
            for z in range(SIZE):
                write_y = 0
                for y in range(SIZE):
                    if y in ys:
                        continue
                    new_field[x][write_y][z] = self.field[x][y][z]
                    write_y += 1
        self.field = new_field
        n = len(ys)
        self.planes_cleared += n
        self.score += n * 100
        print(f"💥 Удалено плоскостей: {n} | Счёт: {self.score} | "
              f"Всего: {self.planes_cleared}")

    def clear_full_planes(self):
        """Сразу удалить заполненные плоскости (без вспышки)"""
        full = [y for y in range(SIZE) if self.plane_full(y)]
        if full:
            self.remove_planes(full)

    def step(self):
        if self.state == 'NEW_PIECE':
            self.new_piece()
        elif self.state == 'FALLING':
            px, py, pz = self.cur_pos
            if py > self.target_y:
                self.cur_pos = (px, py - 1, pz)
            if self.cur_pos[1] <= self.target_y:
                self.lock_piece()
                self.clear_full_planes()
                self.state = 'NEW_PIECE'

# =============================================
# ШАГ 5: ОТРИСОВКА ЧЕРЕЗ ПОРТЫ 8255
# =============================================
def render(game):
    """Отрисовать состояние игры через порты 8255"""
    # Очистка куба (напрямую, без вызова update)
    for z in range(SIZE):
        for y in range(SIZE):
            for x in range(SIZE):
                cube_widget.brightness[z][y][x] = 0.0

    # === Поле: рисуем через порты ===
    for x in range(SIZE):
        for y in range(SIZE):
            for z in range(SIZE):
                if game.field[x][y][z]:
                    ppi.io_write(base + 0, x)   # X
                    ppi.io_write(base + 1, y)   # Y
                    ppi.io_write(base + 2, z)   # Z (строб)

    # === Падающая фигура: рисуем через порты ===
    if game.state == 'FALLING' and game.current and game.cur_pos:
        px, py, pz = game.cur_pos
        for (cx, cy, cz) in game.current:
            x, y, z = px + cx, py + cy, pz + cz
            if 0 <= x < SIZE and 0 <= y < SIZE and 0 <= z < SIZE:
                ppi.io_write(base + 0, x)   # X
                ppi.io_write(base + 1, y)   # Y
                ppi.io_write(base + 2, z)   # Z (строб)

    cube_widget.update()

# =============================================
# ШАГ 6: АНИМАЦИОННЫЙ ЦИКЛ
# =============================================
TICK = 100  # мс на шаг
game = Tetris3D()

def tick():
    """Один тик игры"""
    game.step()
    render(game)
    timer = QTimer(api.mw)
    timer.setSingleShot(True)
    timer.timeout.connect(tick)
    timer.start(TICK)
    api.mw._cube3d_timer = timer

# =============================================
# ШАГ 7: ЗАПУСК
# =============================================
if hasattr(api.mw, '_cube3d_timer') and api.mw._cube3d_timer is not None:
    try:
        api.mw._cube3d_timer.stop()
    except Exception:
        pass

print("\n🧊 3D Тетрис запущен (отрисовка через порты 8255):")
print("   • Случайные фигуры (поликубики ≤ 3×3×3)")
print("   • Реальное падение и укладка")
print("   • ИИ размещает фигуры для заполнения плоскостей")
print("   • Заполненная плоскость удаляется")
print("   • Окно 8255 показывает активность при отрисовке")
print("\n📌 Управление:")
print("   • Вращайте куб мышью!")
print("\n⏹ Остановка тетриса:")
print("   api.mw._cube3d_timer.stop()")

tick()
