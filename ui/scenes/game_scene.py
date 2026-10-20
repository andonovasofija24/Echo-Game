"""Екран за играње: светот, HUD, пауза и крај на нивото.

Режими:
  play  → игра тече
  pause → Esc: светот застанува, се појавува мени
  end   → победа или пораз: мени со следно ниво / повторно / главно мени
"""

import math

import pygame

from game import controls
from game.controls import NO_ACTIONS, InputState
from game.session import GameSession
from render.renderer import WorldRenderer
from settings import CLAP_COOLDOWN, LEVELS, LEVELS_DIR, MEMORY_REMEMBER_THRESHOLD, STONE_COUNT
from ui import theme
from ui.i18n import tr
from ui.widgets import Menu, MenuItem, ease_out

INTRO_TIME = 2.6
END_DELAY = 0.9


class GameScene:
    def __init__(self, app, level_index: int):
        self.app = app
        self.world = WorldRenderer(app.size)
        self.debug = False
        self.dim = pygame.Surface(app.size, pygame.SRCALPHA)
        self.input = InputState()          # физички копчиња (работи и со македонска тастатура)
        self.session = None
        self.start_level(level_index)

    def start_level(self, index: int) -> None:
        self.save_memory("quit")          # ако претходната партија не е завршена
        self.level_index = index
        path = self.app.base_dir / LEVELS_DIR / LEVELS[index][0]
        memory = self.app.memory
        heat = memory.load_heat(index) if memory else {}
        self.remembered = sum(heat.values()) >= MEMORY_REMEMBER_THRESHOLD
        self.session = GameSession(path, index, memory_heat=heat)
        self.memory_saved = False
        if hasattr(self, "input"):
            self.input.clear()
        self.world.set_level(index)
        self.app.audio.reset()
        self.mode = "play"
        self.intro_t = 0.0
        self.end_t = 0.0
        self.overlay_k = 0.0
        self.end_menu: Menu | None = None
        self.pause_menu = self._make_pause_menu()

    # ================= Менија =================

    def _make_pause_menu(self) -> Menu:
        cx = self.app.size[0] // 2
        return Menu([
            MenuItem(lambda: tr("pause_resume"), self._resume),
            MenuItem(lambda: tr("pause_restart"), lambda: self.start_level(self.level_index)),
            MenuItem(lambda: tr("menu_howto"), self._howto),
            MenuItem(lambda: tr("menu_sound_off") if self.app.audio.muted else tr("menu_sound_on"),
                     self.app.toggle_sound),
            MenuItem(lambda: tr("pause_menu"), self._to_menu, danger=True),
        ], pos=(cx, 300), size=28, spacing=54, align="center", sound=self.app.audio.ui)

    def _make_end_menu(self) -> Menu:
        cx = self.app.size[0] // 2
        items = []
        if self.session.won and self.level_index + 1 < len(LEVELS):
            items.append(MenuItem(lambda: tr("win_next"), lambda: self.start_level(self.level_index + 1)))
        items.append(MenuItem(lambda: tr("retry"), lambda: self.start_level(self.level_index)))
        items.append(MenuItem(lambda: tr("pause_menu"), self._to_menu, danger=True))
        return Menu(items, pos=(cx, 420), size=28, spacing=54, align="center", sound=self.app.audio.ui)

    def _resume(self) -> None:
        self.mode = "play"
        self.input.clear()

    def _howto(self) -> None:
        from ui.scenes.howto import HowToScene
        # По упатството се враќаме во ОВАА партија, во пауза.
        self.app.go(HowToScene(self.app, back=lambda: self), fade=False)

    def _to_menu(self) -> None:
        from ui.scenes.menu import MenuScene
        self.save_memory("quit")
        self.app.go(MenuScene(self.app))

    def save_memory(self, result: str) -> None:
        """Ја запишува оваа партија во SQLite (еднаш по партија)."""
        s = self.session
        if s is None or self.memory_saved or self.app.memory is None:
            return
        if result == "quit" and s.time < 3:
            return                         # премногу кратко за да значи нешто
        self.app.memory.save_game(self.level_index, s.new_heat, result, s.time, s.stones_used, s.hits)
        self.memory_saved = True

    def on_exit(self) -> None:
        """Прозорецот се затвора додека трае играта."""
        self.save_memory("quit")

    # ================= Влез =================

    def handle_event(self, event) -> None:
        self.input.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                self.debug = not self.debug
                return
            if controls.is_key(event, controls.MUTE):
                self.app.toggle_sound()
                return

        if self.mode == "play":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.mode = "pause"
                    self.input.clear()
                    self.pause_menu.focus = 0
                    self.app.audio.ui("select")
                elif controls.is_key(event, controls.RESTART):
                    self.start_level(self.level_index)
                elif event.key == pygame.K_SPACE:
                    self.session.clap()
                elif controls.is_key(event, controls.THROW):
                    self.session.throw_at_monster()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.session.throw(event.pos)

        elif self.mode == "pause":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._resume()
                return
            self.pause_menu.handle_event(event)

        elif self.mode == "end" and self.end_menu:
            if controls.is_key(event, controls.RESTART):
                self.start_level(self.level_index)
                return
            self.end_menu.handle_event(event)

    # ================= Ажурирање =================

    def update(self, dt: float) -> None:
        self.dt = dt
        self.intro_t += dt
        target = 1.0 if self.mode in ("pause", "end") else 0.0
        self.overlay_k += (target - self.overlay_k) * min(1.0, dt * 8)

        if self.mode == "pause":
            self.pause_menu.update(dt)
            self.dt = 0.0
            return

        actions = self.input.actions() if self.mode == "play" else NO_ACTIONS
        self.session.update(dt, actions)
        self.app.audio.update(self.session, dt)

        if self.session.game_over:
            self.end_t += dt
            if self.mode == "play":
                self.mode = "end"
                self.save_memory("won" if self.session.won else "lost")
                if self.session.won:
                    self.app.unlock(self.level_index + 1)
            if self.end_menu is None and self.end_t > END_DELAY:
                self.end_menu = self._make_end_menu()
            if self.end_menu:
                self.end_menu.update(dt)

    # ================= Цртање =================

    def draw(self, surface: pygame.Surface) -> None:
        self.world.draw(surface, self.session, getattr(self, "dt", 0.0),
                        pygame.mouse.get_pos(), self.debug, show_aim=self.mode == "play")
        self._draw_hud(surface)
        if self.intro_t < INTRO_TIME and self.mode == "play":
            self._draw_intro(surface)
        if self.overlay_k > 0.01:
            self.dim.fill((8, 6, 20, int(170 * self.overlay_k)))
            surface.blit(self.dim, (0, 0))
        if self.mode == "pause":
            self._draw_pause(surface)
        elif self.mode == "end" and self.end_t > 0.25:
            self._draw_end(surface)

    def _draw_hud(self, surface) -> None:
        w, h = self.app.size
        s = self.session
        # Горе лево: ниво
        theme.text(surface, tr("level_label", n=self.level_index + 1), 13, theme.ACCENT_2, (24, 18), "semibold")
        theme.text(surface, tr(LEVELS[self.level_index][1]), 20, theme.TEXT, (24, 34), "semibold")
        # Горе десно: време и пауза
        mins, secs = divmod(int(s.time), 60)
        theme.text(surface, f"{mins:02d}:{secs:02d}", 20, theme.TEXT, (w - 24, 18), "semibold", "topright")
        theme.text(surface, tr("hud_pause"), 13, theme.TEXT_DIM, (w - 24, 46), "medium", "topright")
        if self.app.audio.muted:
            theme.text(surface, tr("menu_sound_off"), 13, theme.DANGER, (w - 24, 64), "medium", "topright")

        # Долу лево: камчиња
        x, y = 28, h - 40
        for i in range(STONE_COUNT):
            c = (x + i * 18, y)
            if i < s.player.stones:
                pygame.draw.circle(surface, (245, 245, 255), c, 5)
            else:
                pygame.draw.circle(surface, theme.TEXT_DIM, c, 5, 1)
        theme.text(surface, f"E · {tr('hud_stones')}", 13, theme.TEXT_MUTED, (x - 4, y + 12), "medium")

        # До нив: подготвеност на плескањето (кружен прогрес)
        cx, cy = 150, h - 40
        ready = 1 - s.player.clap_cooldown / CLAP_COOLDOWN
        pygame.draw.circle(surface, theme.TEXT_DIM, (cx, cy), 9, 1)
        if ready >= 1:
            pygame.draw.circle(surface, theme.ACCENT, (cx, cy), 6)
        else:
            rect = pygame.Rect(cx - 9, cy - 9, 18, 18)
            pygame.draw.arc(surface, theme.ACCENT, rect, math.pi / 2, math.pi / 2 + ready * math.tau, 2)
        theme.text(surface, f"Space · {tr('hud_clap')}", 13, theme.TEXT_MUTED, (cx - 10, cy + 12), "medium")

    def _draw_intro(self, surface) -> None:
        t = self.intro_t
        k = min(1.0, t / 0.4) * (1 - max(0.0, (t - INTRO_TIME + 0.8) / 0.8))
        if k <= 0:
            return
        w, h = self.app.size
        a = int(255 * k)
        y = h * 0.16 - 12 * (1 - ease_out(min(1.0, t / 0.6)))
        theme.text(surface, tr("level_label", n=self.level_index + 1), 18, theme.ACCENT_2, (w / 2, y),
                   "semibold", "center", alpha=a)
        theme.text(surface, tr(LEVELS[self.level_index][1]), 54, theme.TEXT, (w / 2, y + 48),
                   "black", "center", alpha=a)
        if self.remembered:
            # Меморијата од претходните игри: малку морничаво потсетување.
            theme.text(surface, tr("intro_remember"), 18, theme.DANGER, (w / 2, y + 100),
                       "medium", "center", alpha=int(a * 0.85))

    def _draw_pause(self, surface) -> None:
        w, h = self.app.size
        rect = pygame.Rect(0, 0, 440, 430)
        rect.center = (w // 2, h // 2 + 10)
        theme.panel(surface, rect, alpha=210, radius=24)
        theme.text(surface, tr("pause_title"), 36, theme.TEXT, (w // 2, rect.y + 52), "black", "center")
        self.pause_menu.draw(surface)

    def _draw_end(self, surface) -> None:
        w, h = self.app.size
        won = self.session.won
        k = ease_out(min(1.0, (self.end_t - 0.25) / 0.6))
        color = theme.ACCENT if won else theme.DANGER
        y = 230 - 20 * (1 - k)
        theme.text(surface, tr("win_title" if won else "lose_title"), 64, color, (w / 2, y),
                   "black", "center", alpha=int(255 * k))
        if won:
            mins, secs = divmod(int(self.session.time), 60)
            sub = tr("win_time", time=f"{mins:02d}:{secs:02d}")
            if self.level_index + 1 >= len(LEVELS):
                sub += "   ·   " + tr("win_all")
        else:
            sub = tr("lose_sub")
        theme.text(surface, sub, 22, theme.TEXT_MUTED, (w / 2, y + 60), "regular", "center", alpha=int(255 * k))
        if self.end_menu:
            self.end_menu.draw(surface)

