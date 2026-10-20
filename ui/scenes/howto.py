"""Упатство: три страници со текст лево и жива илустрација десно.

  1. Цел + контроли (нацртани копчиња од тастатура)
  2. Звукот ти е очи: анимација на бранови што откриваат ѕидови, и камче
  3. Чудовиштата: живо демо на секоја состојба (патрола, истражува, лови,
     пребарува) со вистинските звуци; ↑ ↓ или клик избира состојба

Илустрациите се цртаат со код, со истите правила како во играта.
"""

import math

import pygame

from ui import theme
from ui.i18n import tr
from ui.state_demo import STATE_COLORS, STATES, StateDemo
from ui.widgets import KEYS_DOWN, KEYS_LEFT, KEYS_RIGHT, KEYS_UP, key_is, keycap, page_dots, ring

PAGES = 3


class HowToScene:
    def __init__(self, app, back):
        self.app = app
        self.back = back          # функција што го враќа претходниот екран
        self.page = 0
        self.page_anim = 0.0
        self.t = 0.0
        self.bg = theme.background(app.size, seed=3)
        self.motes = theme.Motes(app.size, count=40, seed=6)
        self.player_glow = theme.glow_circle(36, (120, 225, 255), 0.6)
        w, h = app.size
        self.text_rect = pygame.Rect(90, 170, 470, 440)
        self.art_rect = pygame.Rect(610, 150, 580, 470)
        self.arrow_left = pygame.Rect(0, 0, 44, 44)
        self.arrow_right = pygame.Rect(0, 0, 44, 44)

        # Демо на состојбите (страница 3): арена горе, листа на состојби долу.
        r = self.art_rect
        self.demo = StateDemo(pygame.Rect(r.x + 20, r.y + 20, r.width - 40, 196), app.audio)
        self.state_rows = [pygame.Rect(r.x + 20, r.y + 232 + i * 50, r.width - 40, 44) for i in range(4)]

    # ================= Влез =================

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if key_is(event, KEYS_RIGHT) or event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.page < PAGES - 1:
                    self._goto(self.page + 1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._leave()
            elif key_is(event, KEYS_LEFT):
                self._goto(self.page - 1)
            elif event.key == pygame.K_ESCAPE:
                self._leave()
        if self.page == 2:
            if key_is(event, KEYS_UP):
                self.demo.select(self.demo.index - 1)
                return
            if key_is(event, KEYS_DOWN):
                self.demo.select(self.demo.index + 1)
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, row in enumerate(self.state_rows):
                    if row.collidepoint(event.pos):
                        self.demo.select(i)
                        return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.arrow_left.collidepoint(event.pos):
                self._goto(self.page - 1)
            elif self.arrow_right.collidepoint(event.pos):
                self._goto(self.page + 1)
        elif event.type == pygame.MOUSEWHEEL:
            self._goto(self.page - event.y)

    def _goto(self, page: int) -> None:
        page = max(0, min(PAGES - 1, page))
        if page != self.page:
            self.page = page
            self.app.audio.ui("move")
            if page == 2:
                self.demo.auto = True
                self.demo.start(0)

    def _leave(self) -> None:
        self.app.audio.ui("select")
        self.app.go(self.back())

    # ================= Ажурирање и цртање =================

    def update(self, dt: float) -> None:
        self.t += dt
        self.motes.update(dt)
        self.page_anim += (self.page - self.page_anim) * min(1.0, dt * 10)
        if self.page == 2:
            self.demo.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        w, h = self.app.size
        surface.blit(self.bg, (0, 0))
        self.motes.draw(surface)

        theme.text(surface, tr("howto_title").upper(), 15, theme.ACCENT_2, (92, 70), "semibold")
        title = tr(f"p{self.page + 1}_title")
        theme.text(surface, title, 44, theme.TEXT, (90, 92), "black")

        # Навигација: стрелки и точки
        dots_center = (w - 170, 110)
        page_dots(surface, PAGES, self.page_anim, dots_center)
        self.arrow_left.center = (dots_center[0] - 72, dots_center[1])
        self.arrow_right.center = (dots_center[0] + 72, dots_center[1])
        for rect, glyph, enabled in ((self.arrow_left, "‹", self.page > 0),
                                     (self.arrow_right, "›", self.page < PAGES - 1)):
            col = theme.ACCENT if enabled else theme.TEXT_DIM
            theme.text(surface, glyph, 36, col, rect.center, "medium", "center")

        # Текст лево
        y = self.text_rect.y
        for line in theme.wrap(tr(f"p{self.page + 1}_text"), 21, self.text_rect.width):
            theme.text(surface, line, 21, theme.TEXT_MUTED, (self.text_rect.x, y))
            y += 32
        if self.page == 2:
            y += 18
            tip = theme.wrap(tr("p3_tip"), 18, self.text_rect.width - 20, "medium")
            pygame.draw.line(surface, theme.ACCENT_2, (self.text_rect.x, y), (self.text_rect.x, y + len(tip) * 27), 2)
            for line in tip:
                theme.text(surface, line, 18, theme.ACCENT_2, (self.text_rect.x + 16, y))
                y += 27

        # Илустрација десно
        theme.panel(surface, self.art_rect, alpha=150, radius=22)
        clip = surface.get_clip()
        surface.set_clip(self.art_rect.inflate(-4, -4))
        [self._art_controls, self._art_sound, self._art_monsters][self.page](surface)
        surface.set_clip(clip)

        theme.text(surface, tr("howto_pages"), 15, theme.TEXT_DIM, (90, h - 46), "medium")

    # ================= Илустрации =================

    def _art_controls(self, surface) -> None:
        r = self.art_rect
        x0, y = r.x + 36, r.y + 22
        rows = [
            (["W", "A", "S", "D"], "ctl_move"),
            (["←", "↑", "↓", "→"], "ctl_move_arrows"),
            (["Shift"], "ctl_sneak"),
            (["Space"], "ctl_clap"),
            (["E"], "ctl_stone"),
            (["🖱"], "ctl_stone_aim"),
            (["M"], "ctl_mute"),
            (["Esc"], "ctl_pause"),
            (["F1"], "ctl_debug"),
        ]
        for keys, label in rows:
            x = x0
            for k in keys:
                if k == "🖱":
                    rect = self._mouse_icon(surface, (x, y - 4))
                else:
                    rect = keycap(surface, k, (x, y))
                x = rect.right + 8
            theme.text(surface, tr(label), 20, theme.TEXT, (r.x + 250, y + 18), "medium", "midleft")
            y += 47

    @staticmethod
    def _mouse_icon(surface, pos) -> pygame.Rect:
        rect = pygame.Rect(pos[0], pos[1], 30, 44)
        pygame.draw.rect(surface, (44, 36, 86), rect, border_radius=15)
        pygame.draw.rect(surface, theme.PANEL_BORDER, rect, 1, border_radius=15)
        left = pygame.Rect(rect.x + 2, rect.y + 2, 13, 18)
        pygame.draw.rect(surface, theme.ACCENT, left, border_top_left_radius=13)
        pygame.draw.line(surface, theme.PANEL_BORDER, (rect.centerx, rect.y + 2), (rect.centerx, rect.y + 20))
        return rect

    def _art_sound(self, surface) -> None:
        """Играч плеска, бранот ги открива ѕидовите; камче лета и прави свој бран."""
        r = self.art_rect
        src = pygame.Vector2(r.x + 170, r.y + 300)
        walls = [
            ((r.x + 60, r.y + 120), (r.x + 330, r.y + 120)),
            ((r.x + 330, r.y + 120), (r.x + 330, r.y + 230)),
            ((r.x + 60, r.y + 120), (r.x + 60, r.y + 420)),
            ((r.x + 60, r.y + 420), (r.x + 520, r.y + 420)),
            ((r.x + 420, r.y + 200), (r.x + 520, r.y + 200)),
            ((r.x + 420, r.y + 200), (r.x + 420, r.y + 300)),
        ]
        cycle = 3.2
        t = self.t % cycle
        stone_land = pygame.Vector2(r.x + 470, r.y + 340)

        # Бран на плескањето (сина/лаванда)
        self._wave(surface, src, t * 260, walls, theme.ACCENT, 520)
        # Камчето лета по лак, па прави портокалов бран
        fly = 0.9
        if 1.2 < t < 1.2 + fly:
            k = (t - 1.2) / fly
            p = src.lerp(stone_land, k) + (0, -math.sin(k * math.pi) * 90)
            pygame.draw.circle(surface, (255, 170, 80), p, 4)
        elif t >= 1.2 + fly:
            self._wave(surface, stone_land, (t - 1.2 - fly) * 260, walls, (255, 170, 80), 300)
            pygame.draw.circle(surface, (255, 170, 80), stone_land, 3)

        surface.blit(self.player_glow, self.player_glow.get_rect(center=src), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surface, (120, 225, 255), src, 9)

    def _wave(self, surface, center, radius, walls, color, max_r) -> None:
        if radius <= 0:
            return
        k = max(0.0, 1 - radius / max_r)
        ring(surface, center, radius, color, int(170 * k), 2)
        # Ѕидови: точките на ѕидот поблиску од радиусот засветлуваат.
        for a, b in walls:
            a, b = pygame.Vector2(a), pygame.Vector2(b)
            steps = int(a.distance_to(b) // 8) + 1
            for i in range(steps):
                p = a.lerp(b, i / steps)
                q = a.lerp(b, (i + 1) / steps)
                d = center.distance_to(p)
                if d <= radius and d <= max_r:
                    since = (radius - d) / 260
                    v = max(0.0, 1 - since / 1.6) * (1 - d / max_r * 0.6)
                    if v > 0.03:
                        tint = theme.lerp_color(theme.wall_tint(p, self.app.size), color, 0.3)
                        pygame.draw.line(surface, theme.lerp_color(theme.PANEL, tint, v), p, q, 3)

    def _art_monsters(self, surface) -> None:
        """Живо демо на избраната состојба + листа на сите четири (клик или ↑ ↓)."""
        self.demo.draw(surface, self.t)
        current = self.demo.index
        for i, (key, row) in enumerate(zip(STATES, self.state_rows)):
            col = STATE_COLORS[key]
            active = i == current
            if active:
                theme.panel(surface, row, alpha=130, radius=12, border=col)
                # Лента што покажува колку од демото поминало.
                progress = min(1.0, self.demo.t / 5.0)
                pygame.draw.line(surface, col, (row.x + 12, row.bottom - 4),
                                 (row.x + 12 + (row.width - 24) * progress, row.bottom - 4), 2)
            pygame.draw.circle(surface, col, (row.x + 24, row.centery), 7 if active else 5)
            theme.text(surface, tr("state_" + key), 20, theme.TEXT if active else theme.TEXT_MUTED,
                       (row.x + 46, row.centery), "semibold", "midleft")
            theme.text(surface, tr("state_" + key + "_d"), 16, theme.TEXT_MUTED if active else theme.TEXT_DIM,
                       (row.x + 230, row.centery), "regular", "midleft")
        theme.text(surface, tr("p3_demo_hint"), 14, theme.TEXT_DIM,
                   (self.art_rect.centerx, self.art_rect.bottom - 18), "medium", "center")
