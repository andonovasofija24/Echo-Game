"""Визуелна тема: бои, фонтови, омбре позадина и дискретни шари.

Идеја на дизајнот: „мапа на подземна пештера“.
  - Позадината е дијагонално омбре од длабоко индиго (горе лево) преку
    виолетова до темно петролеј-сина (долу десно). Темна, но не црна.
  - Преку неа има топографски изолинии, како на геолошка мапа. Тие се
    едвај видливи (низок alpha), за да не го одвлекуваат вниманието.
  - Ѕидовите што ги открива ехото ја земаат бојата од ИСТОТО омбре, само
    многу посветла, па сè е хармонично: горе лево виолетови, долу десно тиркизни.
  - Играчот (цијан), излезот (нане) и чудовиштата (црвено-розова) се единствените
    заситени бои на екранот, за фокусот да остане на нив.

Сè се генерира со код при стартување и се кешира.
"""

import math
import random
from functools import lru_cache
from pathlib import Path

import pygame

BASE_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = BASE_DIR / "assets" / "fonts"

# ================= Палета =================

# Омбре: три точки по дијагоналата (горе лево → средина → долу десно).
OMBRE = [(12, 10, 30), (34, 22, 70), (20, 78, 96)]

# Светли верзии на истото омбре: бојата на откриените ѕидови.
WALL_TINT = [(165, 140, 255), (215, 150, 255), (110, 240, 225)]

# Бои на интерфејсот.
TEXT = (232, 232, 248)
TEXT_MUTED = (160, 156, 200)
TEXT_DIM = (110, 104, 150)
ACCENT = (110, 240, 225)        # тиркиз
ACCENT_2 = (190, 150, 255)      # лаванда
DANGER = (255, 70, 100)
PANEL = (20, 16, 44)
PANEL_BORDER = (90, 80, 150)

FONT_FILES = {
    "light": "InterDisplay-Light.otf",
    "regular": "Inter-Regular.otf",
    "medium": "Inter-Medium.otf",
    "semibold": "Inter-SemiBold.otf",
    "bold": "Inter-Bold.otf",
    "black": "InterDisplay-Black.otf",
}


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    t = max(0.0, min(1.0, t))
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))


def ombre_at(stops: list[tuple], t: float) -> tuple:
    """Боја на позиција t ∈ [0, 1] по омбре со повеќе точки."""
    t = max(0.0, min(1.0, t))
    seg = t * (len(stops) - 1)
    i = min(int(seg), len(stops) - 2)
    return lerp_color(stops[i], stops[i + 1], seg - i)


def diagonal_t(x: float, y: float, w: float, h: float) -> float:
    """Позиција по дијагоналата: 0 горе лево, 1 долу десно."""
    return (x / w * 0.6 + y / h * 0.4)


# ================= Фонтови =================

@lru_cache(maxsize=64)
def font(size: int, weight: str = "regular") -> pygame.font.Font:
    path = FONT_DIR / FONT_FILES.get(weight, FONT_FILES["regular"])
    try:
        return pygame.font.Font(str(path), size)
    except (FileNotFoundError, OSError):
        # Ако фонтот недостасува, систем фонт што поддржува кирилица.
        return pygame.font.SysFont("segoeui,arial,dejavusans", size, bold=weight in ("bold", "black"))


def text(surface: pygame.Surface, msg: str, size: int, color: tuple, pos: tuple,
         weight: str = "regular", anchor: str = "topleft", alpha: int = 255) -> pygame.Rect:
    """Помошна функција: исцртај текст со дадено сидро (center, midtop, ...)."""
    surf = font(size, weight).render(msg, True, color)
    if alpha < 255:
        surf.set_alpha(alpha)
    rect = surf.get_rect(**{anchor: pos})
    surface.blit(surf, rect)
    return rect


def wrap(msg: str, size: int, width: int, weight: str = "regular") -> list[str]:
    """Прелома текст во редови што собираат во дадена ширина (за сите јазици)."""
    f = font(size, weight)
    lines = []
    for paragraph in msg.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            test = f"{line} {word}".strip()
            if f.size(test)[0] <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


# ================= Омбре и шари =================

def _gradient(size: tuple[int, int], stops: list[tuple]) -> pygame.Surface:
    """Мазно омбре: пресметуваме мала слика пиксел по пиксел, па ја зголемуваме.

    smoothscale ги интерполира боите, па добиваме совршено мазен преод
    за дел од времето што би требало за секој пиксел од 1280x720.
    """
    sw, sh = 64, 36
    small = pygame.Surface((sw, sh))
    for y in range(sh):
        for x in range(sw):
            small.set_at((x, y), ombre_at(stops, diagonal_t(x, y, sw - 1, sh - 1)))
    return pygame.transform.smoothscale(small, size)


def _value_noise(w: int, h: int, rng: random.Random, octaves: int = 3) -> list[list[float]]:
    """Мазен шум (value noise): случајни вредности на решетка, мазно интерполирани.

    Неколку „октави“ (сè погусти решетки со сè помала тежина) даваат природен
    изглед, како релјеф на терен.
    """
    field = [[0.0] * w for _ in range(h)]
    amp_total = 0.0
    for o in range(octaves):
        cells = 3 * (2 ** o)
        amp = 0.5 ** o
        amp_total += amp
        gw, gh = cells + 2, int(cells * h / w) + 2
        grid = [[rng.random() for _ in range(gw)] for _ in range(gh)]
        for y in range(h):
            gy = y / h * (gh - 2)
            y0 = int(gy)
            ty = gy - y0
            ty = ty * ty * (3 - 2 * ty)            # smoothstep
            for x in range(w):
                gx = x / w * (gw - 2)
                x0 = int(gx)
                tx = gx - x0
                tx = tx * tx * (3 - 2 * tx)
                top = lerp(grid[y0][x0], grid[y0][x0 + 1], tx)
                bot = lerp(grid[y0 + 1][x0], grid[y0 + 1][x0 + 1], tx)
                field[y][x] += lerp(top, bot, ty) * amp
    return [[v / amp_total for v in row] for row in field]


def _contours(field: list[list[float]], level: float) -> list[tuple]:
    """Marching squares: ги наоѓа линиите каде полето е точно `level`.

    За секое квадратче од решетката гледаме кои од 4-те агли се над нивото.
    Тоа дава еден од 16 случаи, и за секој знаеме низ кои рабови минува линијата.
    """
    h, w = len(field), len(field[0])
    segs = []

    def interp(p1, p2, v1, v2):
        t = (level - v1) / (v2 - v1) if v2 != v1 else 0.5
        return (lerp(p1[0], p2[0], t), lerp(p1[1], p2[1], t))

    for y in range(h - 1):
        for x in range(w - 1):
            a, b = field[y][x], field[y][x + 1]
            c, d = field[y + 1][x + 1], field[y + 1][x]
            idx = (a > level) | ((b > level) << 1) | ((c > level) << 2) | ((d > level) << 3)
            if idx in (0, 15):
                continue
            top = interp((x, y), (x + 1, y), a, b)
            right = interp((x + 1, y), (x + 1, y + 1), b, c)
            bottom = interp((x, y + 1), (x + 1, y + 1), d, c)
            left = interp((x, y), (x, y + 1), a, d)
            table = {
                1: [(left, top)], 2: [(top, right)], 3: [(left, right)], 4: [(right, bottom)],
                5: [(left, top), (right, bottom)], 6: [(top, bottom)], 7: [(left, bottom)],
                8: [(bottom, left)], 9: [(bottom, top)], 10: [(top, right), (bottom, left)],
                11: [(bottom, right)], 12: [(right, left)], 13: [(right, top)], 14: [(top, left)],
            }
            segs.extend(table[idx])
    return segs


@lru_cache(maxsize=8)
def background(size: tuple[int, int], seed: int = 1, intensity: float = 1.0) -> pygame.Surface:
    """Целосна позадина: омбре + топографски линии + сонарни лаци + честички + вињета."""
    w, h = size
    rng = random.Random(seed)
    surf = _gradient(size, OMBRE)

    deco = pygame.Surface(size, pygame.SRCALPHA)

    # --- Топографски линии ---
    gw, gh = 96, 54
    field = _value_noise(gw, gh, rng)
    sx, sy = w / (gw - 1), h / (gh - 1)
    levels = [0.30 + i * 0.05 for i in range(9)]
    for i, lv in enumerate(levels):
        strong = i % 4 == 0                       # секоја 4-та линија е малку појака
        alpha = int((46 if strong else 24) * intensity)
        for (x1, y1), (x2, y2) in _contours(field, lv):
            px1, py1, px2, py2 = x1 * sx, y1 * sy, x2 * sx, y2 * sy
            tint = ombre_at(WALL_TINT, diagonal_t(px1, py1, w, h))
            pygame.draw.line(deco, (*tint, alpha), (px1, py1), (px2, py2), 1)

    # --- Сонарни лаци од аголот (тематски: ехо) ---
    cx, cy = w * 1.05, h * 1.1
    for r in range(120, int(w * 1.6), 70):
        pygame.draw.circle(deco, (*ACCENT, int(9 * intensity)), (cx, cy), r, 1)

    # --- Ситни „спори“ ---
    for _ in range(140):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        tint = ombre_at(WALL_TINT, diagonal_t(x, y, w, h))
        pygame.draw.circle(deco, (*tint, rng.randint(15, 45)), (x, y), rng.choice((1, 1, 1, 2)))

    surf.blit(deco, (0, 0))

    # --- Вињета: рабовите малку потемни, фокус кон средината ---
    vw, vh = 32, 18
    vig = pygame.Surface((vw, vh), pygame.SRCALPHA)
    for y in range(vh):
        for x in range(vw):
            dx, dy = (x - vw / 2 + 0.5) / (vw / 2), (y - vh / 2 + 0.5) / (vh / 2)
            d = min(1.0, math.sqrt(dx * dx + dy * dy))
            vig.set_at((x, y), (4, 2, 12, int(120 * d ** 3)))
    surf.blit(pygame.transform.smoothscale(vig, size), (0, 0))
    return surf.convert() if pygame.display.get_surface() else surf


@lru_cache(maxsize=1)
def wall_tint_map(size: tuple[int, int]) -> pygame.Surface:
    """Мала слика од која ја читаме бојата на ѕидот за која било позиција."""
    return _gradient((64, 36), WALL_TINT)


def wall_tint(pos, size: tuple[int, int]) -> tuple:
    m = wall_tint_map(size)
    x = int(max(0, min(63, pos[0] / size[0] * 64)))
    y = int(max(0, min(35, pos[1] / size[1] * 36)))
    c = m.get_at((x, y))
    return c.r, c.g, c.b


# ================= Анимирани честички =================

class Motes:
    """Ситна прашина што полека лебди нагоре. Дава живот без да одвлекува."""

    def __init__(self, size: tuple[int, int], count: int = 70, seed: int = 3):
        self.w, self.h = size
        rng = random.Random(seed)
        self.items = [[rng.uniform(0, self.w), rng.uniform(0, self.h),
                       rng.uniform(4, 14), rng.uniform(0, math.tau), rng.uniform(0.25, 0.9)]
                      for _ in range(count)]

    def update(self, dt: float) -> None:
        for m in self.items:
            m[1] -= m[2] * dt
            m[3] += dt * 0.7
            if m[1] < -5:
                m[1] = self.h + 5

    def draw(self, surface: pygame.Surface) -> None:
        for x, y, _, phase, bright in self.items:
            px = x + math.sin(phase) * 6
            tint = ombre_at(WALL_TINT, diagonal_t(px, y, self.w, self.h))
            k = bright * (0.55 + 0.45 * math.sin(phase * 1.3))
            surface.fill(lerp_color((0, 0, 0), tint, k * 0.35), (px, y, 2, 2),
                         special_flags=pygame.BLEND_ADD)


# ================= Помошни облици =================

def glow_circle(radius: int, color: tuple, strength: float = 0.6) -> pygame.Surface:
    """Мек сјај за BLEND_ADD (исто како кај играчот)."""
    size = radius * 2
    surface = pygame.Surface((size, size))
    surface.fill((0, 0, 0))
    for i in range(radius, 0, -1):
        k = (1 - i / radius) ** 2 * strength
        pygame.draw.circle(surface, lerp_color((0, 0, 0), color, k), (radius, radius), i)
    return surface


def panel(surface: pygame.Surface, rect: pygame.Rect, alpha: int = 190, radius: int = 18,
          border: tuple = PANEL_BORDER) -> None:
    """Полупроѕирен „стаклен“ панел со тенка рамка."""
    p = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(p, (*PANEL, alpha), p.get_rect(), border_radius=radius)
    pygame.draw.rect(p, (*border, 140), p.get_rect(), 1, border_radius=radius)
    surface.blit(p, rect)


def monster_shape(center: pygame.Vector2, radius: float, t: float) -> list:
    """Назабената силуета на чудовиштето (се користи и во играта и во менијата)."""
    pts = []
    spikes = 9
    for i in range(spikes * 2):
        a = math.pi * i / spikes
        r = radius * (1.25 if i % 2 == 0 else 0.7) * (1 + 0.12 * math.sin(t + i * 1.7))
        pts.append(center + pygame.Vector2(math.cos(a), math.sin(a)) * r)
    return pts
