"""Екран за избор на јазик: првиот екран во играта.

Дизајн: СОНАР. Центарот е „изворот на звук“, а четирите јазици се цели на
радарот. Сонарната линија се врти и застанува кратко на секој јазик.
Јазикот кон кој е НАСОЧЕНА линијата е избраниот: Enter го отвора.

  - сама: линијата ги обиколува јазиците (брзо се врти, па застанува),
  - ← →: линијата скока на соседниот јазик и подолго останува таму,
  - глувче: линијата се врти кон јазикот под курсорот и ОСТАНУВА насочена
    додека курсорот е таму; клик веднаш го отвора.

Со потврда, од избраниот јазик тргнува голем бран (премин кон менито).

UX правила: имињата на јазиците се на самиот јазик, без знамиња,
а јазикот на системот се предлага и е означен.
"""

import math

import pygame

MOVE_TIME = 0.55        # колку трае вртењето од еден до друг јазик
DWELL_AUTO = 1.4        # колку застанува на секој јазик кога се врти сама
DWELL_KEYS = 3.5        # колку останува по ← →
SWEEP_RX, SWEEP_RY = 560, 272

from ui import i18n, theme
from ui.widgets import KEYS_DOWN, KEYS_LEFT, KEYS_RIGHT, KEYS_UP, ease_out, key_is, ring


class LanguageScene:
    def __init__(self, app, back=None):
        self.app = app
        self.back = back                      # ако е отворен од менито: каде да се врати
        self.codes = [c for c, _, _ in i18n.LANGUAGES]
        suggested, self.detected = i18n.initial_language()
        start = i18n.current() if back else suggested
        self.focus = self.codes.index(start) if start in self.codes else 0

        w, h = app.size
        self.center = pygame.Vector2(w / 2, h / 2 + 4)
        # Две колони (лево/десно), два реда: доволно простор за името и ознаките под секој јазик.
        cx, cy = self.center
        self.nodes = [pygame.Vector2(cx - 390, cy - 128), pygame.Vector2(cx + 390, cy - 128),
                      pygame.Vector2(cx + 390, cy + 118), pygame.Vector2(cx - 390, cy + 118)]
        self.node_angles = [math.atan2(n.y - self.center.y, n.x - self.center.x) for n in self.nodes]

        self.t = 0.0
        self.focus_anim = [0.0] * 4
        self.ping = [0.0] * 4                  # засветлување кога сонарот ќе застане на јазик
        self.wave_t = 0.0                      # време од последната промена на фокус
        self.confirm_t: float | None = None

        # --- Сонарна линија ---
        self.sweep = self.node_angles[self.focus]   # агол во радијани (не се враќа на 0..2π)
        self.target = self.focus
        self.phase = "dwell"                   # "move" (се врти) или "dwell" (застанала)
        self.move_from = self.move_to = self.sweep
        self.move_t = 0.0
        self.dwell_t = 0.0
        self.dwell_len = 2.2                   # на почеток подолго на предложениот јазик
        self.hold = False                      # глувчето е над јазик: линијата чека
        self.direction = 1
        self.trail = 0.3                       # колку е долга опашката (зависи од брзината)

        self.bg = theme.background(app.size, seed=5, intensity=1.25)
        self.overlay = pygame.Surface(app.size, pygame.SRCALPHA)
        self.motes = theme.Motes(app.size, count=40, seed=9)
        # Сјаевите се пресметуваат еднаш; во секој фрејм само се затемнуваат по потреба.
        self.center_glow = theme.glow_circle(130, theme.ACCENT_2, 0.35)
        self.node_glow = {"a": theme.glow_circle(114, theme.ACCENT, 0.6),
                          "b": theme.glow_circle(114, theme.ACCENT_2, 0.6)}

    # ================= Влез =================

    def handle_event(self, event) -> None:
        if self.confirm_t is not None:
            return
        if event.type == pygame.KEYDOWN:
            if key_is(event, KEYS_LEFT) or key_is(event, KEYS_UP):
                self._aim((self.target - 1) % 4, -1, DWELL_KEYS)
            elif key_is(event, KEYS_RIGHT) or key_is(event, KEYS_DOWN) or event.key == pygame.K_TAB:
                self._aim((self.target + 1) % 4, 1, DWELL_KEYS)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._confirm()                # го отвора јазикот кон кој е насочена линијата
            elif event.key == pygame.K_ESCAPE and self.back:
                self.app.audio.ui("select")
                self.app.go(self.back())
        elif event.type == pygame.MOUSEMOTION:
            hit = self._node_at(event.pos)
            if hit is not None:
                self.hold = True
                if hit != self.target:
                    self._aim(hit, self._shortest_dir(hit), float("inf"))
            elif self.hold:
                # Курсорот замина: линијата уште малку чека, па продолжува сама.
                self.hold = False
                self.dwell_t = 0.0
                self.dwell_len = DWELL_AUTO
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = self._node_at(event.pos)
            if hit is not None:
                self._point_at(hit)
                self._confirm()

    def _node_at(self, pos) -> int | None:
        for i, n in enumerate(self.nodes):
            if n.distance_to(pos) < 75:
                return i
        return None

    def _shortest_dir(self, i: int) -> int:
        delta = (self.node_angles[i] - self.sweep) % math.tau
        return 1 if delta <= math.pi else -1

    def _aim(self, i: int, direction: int, dwell: float) -> None:
        """Ја врти сонарната линија кон јазикот i (1 = во насока на часовник, -1 = обратно)."""
        self.target = i
        self.direction = direction
        if direction > 0:
            delta = (self.node_angles[i] - self.sweep) % math.tau
        else:
            delta = -((self.sweep - self.node_angles[i]) % math.tau)
        self.move_from = self.sweep
        self.move_to = self.sweep + delta
        self.move_t = 0.0
        self.phase = "move" if abs(delta) > 1e-3 else "dwell"
        self.dwell_t = 0.0
        self.dwell_len = dwell

    def _point_at(self, i: int) -> None:
        """Веднаш насочи кон јазикот i (за клик со глувче)."""
        self.target = i
        self.sweep = self.node_angles[i]
        self.phase = "dwell"
        self._update_focus()

    def _confirm(self) -> None:
        self.confirm_t = 0.0
        self.app.audio.ui("select")
        self.app.set_language(self.codes[self.focus])

    # ================= Ажурирање =================

    def update(self, dt: float) -> None:
        self.t += dt
        self.wave_t += dt
        self.motes.update(dt)

        if self.confirm_t is None:
            self._update_sweep(dt)
        self._update_focus()

        for i in range(4):
            target = 1.0 if i == self.focus else 0.0
            self.focus_anim[i] += (target - self.focus_anim[i]) * min(1.0, dt * 10)
            self.ping[i] = max(0.0, self.ping[i] - dt * 1.4)

        if self.confirm_t is not None:
            self.confirm_t += dt
            if self.confirm_t > 0.75:
                from ui.scenes.menu import MenuScene
                self.app.go(self.back() if self.back else MenuScene(self.app))

    def _update_sweep(self, dt: float) -> None:
        if self.phase == "move":
            self.move_t += dt / MOVE_TIME
            k = self.move_t
            k = k * k * (3 - 2 * k) if k < 1 else 1.0          # мазно забрзување и сопирање
            self.sweep = self.move_from + (self.move_to - self.move_from) * k
            self.trail = min(1.0, self.trail + dt * 6)
            if self.move_t >= 1:
                self.phase = "dwell"
                self.dwell_t = 0.0
                self.ping[self.target] = 1.0
        else:
            self.trail = max(0.25, self.trail - dt * 2)
            if not self.hold:
                self.dwell_t += dt
                if self.dwell_t >= self.dwell_len:
                    self._aim((self.target + 1) % 4, 1, DWELL_AUTO)

    def _update_focus(self) -> None:
        """Избран е јазикот кон кој линијата е НАЈБЛИСКУ насочена."""
        def ang_dist(a, b):
            d = (a - b) % math.tau
            return min(d, math.tau - d)
        nearest = min(range(4), key=lambda i: ang_dist(self.sweep, self.node_angles[i]))
        if nearest != self.focus:
            self.focus = nearest
            self.wave_t = 0.0
            self.app.audio.ui("move")

    # ================= Цртање =================

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.bg, (0, 0))
        self.motes.draw(surface)
        ov = self.overlay
        ov.fill((0, 0, 0, 0))
        c = self.center
        code = self.codes[self.focus]

        # --- Концентрични кругови на радарот ---
        for r in range(120, 640, 74):
            pygame.draw.ellipse(ov, (*theme.ACCENT_2, 22), self._ellipse(r), 1)

        # --- Сонарна линија со опашка (опашката е подолга додека се врти) ---
        steps = 26
        for k in range(steps):
            a = self.sweep - self.direction * k * 0.03 * self.trail
            d = pygame.Vector2(math.cos(a), math.sin(a))
            length = 1 / math.sqrt((d.x / SWEEP_RX) ** 2 + (d.y / SWEEP_RY) ** 2)
            alpha = int(110 * (1 - k / steps) ** 2 * (0.4 + 0.6 * self.trail if k else 1))
            pygame.draw.line(ov, (*theme.ACCENT, alpha), c, c + d * length, 3 if k == 0 else 2)

        # --- Линии кон јазиците + бран кон избраниот ---
        for i, n in enumerate(self.nodes):
            k = self.focus_anim[i]
            col = theme.lerp_color(theme.TEXT_DIM, theme.ACCENT, k)
            pygame.draw.line(ov, (*col, int(40 + 90 * k)), c, n, 1)
        target = self.nodes[self.focus]
        for j in range(3):
            phase = ((self.wave_t * 1.6) - j * 0.33) % 1.0
            p = c.lerp(target, ease_out(phase))
            pygame.draw.circle(ov, (*theme.ACCENT, int(220 * (1 - phase))), p, 4 - j)

        surface.blit(ov, (0, 0))

        # --- Центар: наслов на играта на избраниот јазик ---
        surface.blit(self.center_glow, self.center_glow.get_rect(center=c), special_flags=pygame.BLEND_ADD)
        theme.panel(surface, pygame.Rect(c.x - 92, c.y - 92, 184, 184), alpha=210, radius=92,
                    border=theme.ACCENT_2)
        theme.text(surface, i18n.tr_in(code, "title"), 40, theme.TEXT, (c.x, c.y - 8), "black", "center")
        theme.text(surface, i18n.tr_in(code, "lang_welcome"), 16, theme.TEXT_MUTED, (c.x, c.y + 30),
                   "regular", "center")

        # --- Јазиците ---
        for i, (lcode, name, short) in enumerate(i18n.LANGUAGES):
            self._draw_node(surface, i, lcode, name, short)

        # --- Наслов горе: „Избери јазик“ на сите јазици, избраниот е светол ---
        parts = [i18n.tr_in(lc, "lang_title") for lc in self.codes]
        f = theme.font(22, "semibold")
        sep = "   ·   "
        total = sum(f.size(p)[0] for p in parts) + f.size(sep)[0] * 3
        x = self.app.size[0] / 2 - total / 2
        for i, p in enumerate(parts):
            col = theme.lerp_color(theme.TEXT_DIM, theme.TEXT, self.focus_anim[i])
            r = theme.text(surface, p, 22, col, (x, 70), "semibold")
            x = r.right
            if i < 3:
                r = theme.text(surface, sep, 22, theme.TEXT_DIM, (x, 70), "regular")
                x = r.right
        pygame.draw.line(surface, (60, 50, 110), (self.app.size[0] / 2 - 60, 112),
                         (self.app.size[0] / 2 + 60, 112), 1)

        theme.text(surface, i18n.tr_in(code, "lang_hint"), 16, theme.TEXT_DIM,
                   (self.app.size[0] / 2, self.app.size[1] - 40), "medium", "center")

        # --- Потврда: голем бран од избраниот јазик ---
        if self.confirm_t is not None:
            k = ease_out(self.confirm_t / 0.75)
            for j in range(3):
                ring(surface, target, k * (900 + j * 120), theme.ACCENT, int(200 * (1 - k)), 3)

    def _ellipse(self, r: float) -> pygame.Rect:
        rx, ry = r * 1.0, r * 0.5
        return pygame.Rect(self.center.x - rx, self.center.y - ry, rx * 2, ry * 2)

    def _draw_node(self, surface, i: int, code: str, name: str, short: str) -> None:
        n = self.nodes[i]
        k = self.focus_anim[i]
        ping = self.ping[i]
        radius = 52 + 8 * k

        light = min(1.0, 0.35 + 0.65 * k + 0.4 * ping)
        glow = self.node_glow["a" if k > 0.5 else "b"].copy()
        g = int(255 * (0.4 + 0.6 * light))
        glow.fill((g, g, g), special_flags=pygame.BLEND_MULT)
        surface.blit(glow, glow.get_rect(center=n), special_flags=pygame.BLEND_ADD)

        theme.panel(surface, pygame.Rect(n.x - radius, n.y - radius, radius * 2, radius * 2),
                    alpha=220, radius=int(radius), border=theme.lerp_color(theme.PANEL_BORDER, theme.ACCENT, k))
        if ping > 0:
            ring(surface, n, radius + 18 * (1 - ping), theme.ACCENT_2, int(160 * ping), 1)
        if k > 0.05:
            ring(surface, n, radius + 10, theme.ACCENT, int(200 * k), 2)

        theme.text(surface, short, 30, theme.lerp_color(theme.TEXT_MUTED, theme.TEXT, k), n, "black", "center")

        below = n.y + radius + 22
        theme.text(surface, name, 26, theme.lerp_color(theme.TEXT_MUTED, theme.TEXT, k),
                   (n.x, below), "semibold", "center")
        theme.text(surface, i18n.tr_in(code, "lang_welcome"), 16, theme.TEXT_DIM,
                   (n.x, below + 28), "regular", "center")
        if code == self.detected:
            theme.text(surface, "● " + i18n.tr_in(code, "lang_detected"), 13, theme.ACCENT_2,
                       (n.x, below + 52), "medium", "center")
