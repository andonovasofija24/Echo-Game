"""Главно мени.

Лево: наслов со „ехо“ копии зад него, мото и копчиња.
Десно: живо мини-демо на главната механика. Од една точка тргнуваат
бранови, ги откриваат контурите на пештерата и за момент ја осветлуваат
сенката на чудовиште што чека во темнината.
"""

import math
import random

import pygame

from settings import LEVELS
from ui import theme
from ui.i18n import tr
from ui.widgets import Menu, MenuItem, ring

WAVE_SPEED = 260
WAVE_EVERY = 2.4
FADE = 1.8


class MenuScene:
    def __init__(self, app):
        self.app = app
        self.t = 0.0
        self.bg = theme.background(app.size, seed=2)
        self.motes = theme.Motes(app.size, count=60, seed=4)
        self.light = pygame.Surface(app.size)

        self.menu = Menu([
            MenuItem(lambda: tr("menu_play"), self._play,
                     on_left=lambda: self._change_level(-1), on_right=lambda: self._change_level(1),
                     detail=self._level_text),
            MenuItem(lambda: tr("menu_howto"), self._howto),
            MenuItem(lambda: tr("menu_language"), self._language),
            MenuItem(lambda: tr("menu_sound_off") if app.audio.muted else tr("menu_sound_on"),
                     app.toggle_sound),
            MenuItem(lambda: tr("menu_quit"), app.quit, danger=True),
        ], pos=(150, 372), size=30, spacing=56, sound=app.audio.ui)

        # --- Мини-демо десно ---
        self.source = pygame.Vector2(app.size[0] * 0.72, app.size[1] * 0.52)
        self.monster = self.source + pygame.Vector2(170, -95)
        self.segments = self._build_cave(random.Random(21))
        self.waves = [0.4]   # возраст на секој бран
        self.src_glow = theme.glow_circle(40, (120, 225, 255), 0.6)

    # ================= Акции =================

    def _level_text(self) -> str:
        i = self.app.level_index
        return tr("menu_level", n=i + 1, name=tr(LEVELS[i][1]))

    def _change_level(self, d: int) -> None:
        self.app.level_index = max(0, min(self.app.unlocked - 1, self.app.level_index + d))

    def _play(self) -> None:
        from ui.scenes.game_scene import GameScene
        self.app.go(GameScene(self.app, self.app.level_index))

    def _howto(self) -> None:
        from ui.scenes.howto import HowToScene
        self.app.go(HowToScene(self.app, back=lambda: MenuScene(self.app)))

    def _language(self) -> None:
        from ui.scenes.language import LanguageScene
        self.app.go(LanguageScene(self.app, back=lambda: MenuScene(self.app)))

    # ================= Влез / ажурирање =================

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return
        self.menu.handle_event(event)

    def update(self, dt: float) -> None:
        self.t += dt
        self.motes.update(dt)
        self.menu.update(dt)
        self.waves = [a + dt for a in self.waves if a < 3.6]
        if not self.waves or self.waves[-1] > WAVE_EVERY:
            self.waves.append(0.0)

    # ================= Цртање =================

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.bg, (0, 0))
        self.motes.draw(surface)
        self._draw_demo(surface)
        self._draw_title(surface)
        self.menu.draw(surface)
        theme.text(surface, tr("hint_nav"), 15, theme.TEXT_DIM, (150, self.app.size[1] - 46), "medium")

    def _draw_title(self, surface: pygame.Surface) -> None:
        title = tr("title")
        # Големината се прилагодува за насловот да не влезе во демото десно.
        size = 132
        while size > 70 and theme.font(size, "black").size(title)[0] > 420:
            size -= 4
        x, y = 140, 110
        # Ехо копии: истиот наслов поместен надесно, сè побледо (како одекнување).
        echo = theme.font(size, "black").render(title, True, theme.ACCENT_2)
        for k in (3, 2, 1):
            shift = k * (16 + 5 * math.sin(self.t * 1.3 + k))
            echo.set_alpha(int(70 / (k * k)))
            surface.blit(echo, (x + shift, y))
        theme.text(surface, title, size, theme.TEXT, (x, y), "black")
        theme.text(surface, tr("tagline"), 22, theme.TEXT_MUTED, (x + 6, y + size + 14), "light")

    def _draw_demo(self, surface: pygame.Surface) -> None:
        """Бранови од изворот откриваат делови од пештерата (исто правило како во играта)."""
        self.light.fill((0, 0, 0))
        src = self.source
        for age in self.waves:
            r = age * WAVE_SPEED
            # Фронт на бранот
            if r < 520:
                k = 1 - r / 520
                pygame.draw.circle(self.light, theme.lerp_color((0, 0, 0), theme.ACCENT, k * 0.35), src, r, 2)
            # Ѕидови што бранот ги допрел
            for a, b, d in self.segments:
                if r >= d:
                    since = (r - d) / WAVE_SPEED
                    k = 1 - since / FADE
                    if k > 0:
                        flash = 0.5 if since < 0.1 else 0.0
                        tint = theme.wall_tint(a, self.app.size)
                        pygame.draw.line(self.light, theme.lerp_color((0, 0, 0), tint, min(1, k * 0.8 + flash)), a, b, 2)

        small = pygame.transform.smoothscale(self.light, (self.app.size[0] // 4, self.app.size[1] // 4))
        small.blit(small, (0, 0), special_flags=pygame.BLEND_ADD)
        blur = pygame.transform.smoothscale(small, self.app.size)
        surface.blit(blur, (0, 0), special_flags=pygame.BLEND_ADD)
        surface.blit(self.light, (0, 0), special_flags=pygame.BLEND_ADD)

        # Изворот (како играчот)
        surface.blit(self.src_glow, self.src_glow.get_rect(center=src), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surface, (120, 225, 255), src, 8)

        # Чудовиштето: се гледа само кога бранот ќе го допре.
        d = src.distance_to(self.monster)
        vis = 0.0
        for age in self.waves:
            r = age * WAVE_SPEED
            if r >= d:
                vis = max(vis, 1 - (r - d) / WAVE_SPEED / FADE)
        if vis > 0.02:
            col = theme.lerp_color((0, 0, 0), theme.DANGER, vis)
            pygame.draw.polygon(surface, col, theme.monster_shape(self.monster, 15, self.t * 6), 2)
            ring(surface, self.monster, 26, theme.DANGER, int(90 * vis), 1)

    def _build_cave(self, rng: random.Random) -> list:
        """Неправилни контури на пештера околу изворот: надворешен ѕид + неколку карпи."""
        src = self.source
        segs = []

        def add_loop(center, radius, jitter, count, start=0.0, span=math.tau):
            pts = []
            for i in range(count + 1):
                a = start + span * i / count
                r = radius * (1 + rng.uniform(-jitter, jitter))
                pts.append(center + pygame.Vector2(math.cos(a) * r, math.sin(a) * r * 0.8))
            for p, q in zip(pts, pts[1:]):
                segs.append((p, q, src.distance_to((p + q) / 2)))

        add_loop(src, 330, 0.12, 46, start=-2.6, span=5.0)        # надворешен ѕид со отвор
        add_loop(src + (-150, 90), 38, 0.25, 9)                   # карпи
        add_loop(src + (120, 120), 30, 0.25, 8)
        add_loop(src + (60, -160), 26, 0.3, 8)
        add_loop(src + (-200, -80), 22, 0.3, 7)
        return segs
