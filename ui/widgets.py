"""Елементи на интерфејсот: вертикално мени со анимирани копчиња.

Секое мени работи и со тастатура (↑ ↓ ← → Enter) и со глувче (hover + клик).
Анимациите се „мазни“: секое копче има вредност 0..1 што постепено се
приближува кон целта, наместо нагло да се менува.
"""

import math

import pygame

KEYS_UP = ((pygame.K_UP,), (pygame.KSCAN_W,))
KEYS_DOWN = ((pygame.K_DOWN,), (pygame.KSCAN_S,))
KEYS_LEFT = ((pygame.K_LEFT,), (pygame.KSCAN_A,))
KEYS_RIGHT = ((pygame.K_RIGHT,), (pygame.KSCAN_D,))


def key_is(event, keys) -> bool:
    """KEYDOWN за стрелка/копче (по знак) ИЛИ буква (по физичка позиција, за секој јазик на тастатура)."""
    codes, scans = keys
    return event.type == pygame.KEYDOWN and (event.key in codes or getattr(event, "scancode", None) in scans)

from ui import theme


class MenuItem:
    def __init__(self, label, action, on_left=None, on_right=None, detail=None, danger=False):
        self.label = label          # функција што враќа текст (за да се менува со јазикот)
        self.action = action
        self.on_left = on_left
        self.on_right = on_right
        self.detail = detail        # дополнителен текст десно (на пр. избор на ниво)
        self.danger = danger
        self.hover = 0.0            # анимација 0..1
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.left_rect = pygame.Rect(0, 0, 0, 0)
        self.right_rect = pygame.Rect(0, 0, 0, 0)


class Menu:
    def __init__(self, items: list[MenuItem], pos: tuple[int, int], size: int = 30,
                 spacing: int = 58, align: str = "left", sound=None):
        self.items = items
        self.pos = pos
        self.size = size
        self.spacing = spacing
        self.align = align
        self.focus = 0
        self.sound = sound          # функција sound(name) за UI звуци
        self.time = 0.0

    # ---------------- Влез ----------------

    def handle_event(self, event) -> bool:
        """Враќа True ако менито го обработило настанот."""
        if event.type == pygame.KEYDOWN:
            if key_is(event, KEYS_UP):
                self._move(-1)
                return True
            if key_is(event, KEYS_DOWN):
                self._move(1)
                return True
            item = self.items[self.focus]
            if key_is(event, KEYS_LEFT) and item.on_left:
                item.on_left()
                self._sound("move")
                return True
            if key_is(event, KEYS_RIGHT) and item.on_right:
                item.on_right()
                self._sound("move")
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._activate(item)
                return True

        elif event.type == pygame.MOUSEMOTION:
            for i, item in enumerate(self.items):
                if item.rect.collidepoint(event.pos) and i != self.focus:
                    self.focus = i
                    self._sound("move")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for item in self.items:
                # Клик на стрелките ‹ › менува вредност (на пр. ниво) без да го активира копчето.
                if item.on_left and item.left_rect.collidepoint(event.pos):
                    item.on_left()
                    self._sound("move")
                    return True
                if item.on_right and item.right_rect.collidepoint(event.pos):
                    item.on_right()
                    self._sound("move")
                    return True
                if item.rect.collidepoint(event.pos):
                    self._activate(item)
                    return True
        return False

    def _move(self, d: int) -> None:
        self.focus = (self.focus + d) % len(self.items)
        self._sound("move")

    def _activate(self, item: MenuItem) -> None:
        self._sound("select")
        item.action()

    def _sound(self, name: str) -> None:
        if self.sound:
            self.sound(name)

    # ---------------- Анимација и цртање ----------------

    def update(self, dt: float) -> None:
        self.time += dt
        for i, item in enumerate(self.items):
            target = 1.0 if i == self.focus else 0.0
            item.hover += (target - item.hover) * min(1.0, dt * 12)

    def draw(self, surface: pygame.Surface) -> None:
        x, y = self.pos
        for i, item in enumerate(self.items):
            h = item.hover
            color = theme.lerp_color(theme.TEXT_MUTED, theme.DANGER if item.danger else theme.ACCENT, h)
            weight = "semibold"
            label = item.label()

            offset = int(18 * h)                     # фокусираното копче лизга надесно
            ty = y + i * self.spacing
            if self.align == "center":
                f = theme.font(self.size, weight)
                w = f.size(label)[0]
                tx = x - w // 2
            else:
                tx = x + offset

            rect = theme.text(surface, label, self.size, color, (tx, ty), weight)
            hit = rect.inflate(60, 18)
            if self.align == "left":
                hit.width = 480
                hit.x = x - 30
            item.rect = hit

            if h > 0.02:
                self._draw_focus_marker(surface, rect, h, item)

            if item.detail:
                detail = item.detail()
                dcol = theme.lerp_color(theme.TEXT_DIM, theme.TEXT, h)
                dx = rect.right + 26
                arrow_col = theme.lerp_color(theme.TEXT_DIM, theme.ACCENT_2, h)
                lrect = theme.text(surface, "‹", self.size - 6, arrow_col, (dx, rect.centery), "medium", "midleft")
                drect = theme.text(surface, detail, self.size - 12, dcol, (dx + 22, rect.centery), "regular", "midleft")
                rrect = theme.text(surface, "›", self.size - 6, arrow_col, (drect.right + 10, rect.centery), "medium", "midleft")
                item.left_rect = lrect.inflate(20, 20)
                item.right_rect = rrect.inflate(20, 20)
                item.rect.width = rect.right + 10 - item.rect.x

    def _draw_focus_marker(self, surface, rect: pygame.Rect, h: float, item: MenuItem) -> None:
        """Мал „сонар“ лево од избраното копче: точка со бранови што се шират."""
        cx, cy = rect.left - 22, rect.centery
        base = theme.DANGER if item.danger else theme.ACCENT
        pygame.draw.circle(surface, theme.lerp_color(theme.PANEL, base, h), (cx, cy), 4)
        for k in range(2):
            phase = (self.time * 0.9 + k * 0.5) % 1.0
            r = 5 + phase * 16
            alpha = int(200 * (1 - phase) * h)
            ring = pygame.Surface((48, 48), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*base, alpha), (24, 24), r, 1)
            surface.blit(ring, (cx - 24, cy - 24))
        # Линија под текстот што се „отвора“ од лево.
        width = int(rect.width * h)
        pygame.draw.line(surface, theme.lerp_color(theme.PANEL, base, h * 0.8),
                         (rect.left, rect.bottom + 4), (rect.left + width, rect.bottom + 4), 2)


def keycap(surface: pygame.Surface, label: str, pos: tuple[int, int], size: int = 18,
           min_width: int = 38, color=None) -> pygame.Rect:
    """Нацртано копче од тастатура (за упатството)."""
    f = theme.font(size, "semibold")
    w = max(min_width, f.size(label)[0] + 20)
    rect = pygame.Rect(pos[0], pos[1], w, size + 18)
    shadow = rect.move(0, 3)
    pygame.draw.rect(surface, (10, 8, 24), shadow, border_radius=8)
    pygame.draw.rect(surface, (44, 36, 86), rect, border_radius=8)
    pygame.draw.rect(surface, color or theme.PANEL_BORDER, rect, 1, border_radius=8)
    theme.text(surface, label, size, theme.TEXT, rect.center, "semibold", "center")
    return rect


def page_dots(surface: pygame.Surface, count: int, active: float, center: tuple[int, int]) -> None:
    """Точки за страници; активната е издолжена (мазно по `active`)."""
    x0 = center[0] - (count - 1) * 14
    for i in range(count):
        k = max(0.0, 1 - abs(active - i))
        w = 8 + int(18 * k)
        rect = pygame.Rect(0, 0, w, 8)
        rect.center = (x0 + i * 28, center[1])
        pygame.draw.rect(surface, theme.lerp_color(theme.TEXT_DIM, theme.ACCENT, k), rect, border_radius=4)


def ring(surface: pygame.Surface, center, radius: float, color: tuple, alpha: int, width: int = 1) -> None:
    """Полупроѕирен круг (pygame.draw нема alpha директно, па цртаме на посебна површина)."""
    if radius <= 0 or alpha <= 0:
        return
    r = int(radius) + width + 1
    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (*color, max(0, min(255, alpha))), (r, r), int(radius), width)
    surface.blit(s, (center[0] - r, center[1] - r))


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def pulse(t: float, speed: float = 2.0) -> float:
    return 0.5 + 0.5 * math.sin(t * speed)
