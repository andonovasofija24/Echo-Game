"""Демо на состојбите на чудовиштето (за упатството).

Мала „сцена“ во која чудовиштето се однесува како во играта, со вистинските
звуци, за секоја од четирите состојби на машината на состојби (FSM):

  ПАТРОЛА    бавно шета меѓу две точки, ретки и тивки чекори
  ИСТРАЖУВА  паѓа камче → чудовиштето оди кон звукот, почести чекори
  ЛОВИ       крик → трча кон играчот, брзи гласни чекори, срцето чука сè побрзо
  ПРЕБАРУВА  кружи околу последното место каде слушнало нешто, застанува, ослушнува

Ова е сценарио (скрипта), не вистинската AI: така секоја состојба се гледа
јасно и секогаш исто, без да зависи од случајноста.
"""

import math

import pygame

from ui import theme
from ui.widgets import ring

STATES = ["patrol", "investigate", "hunt", "search"]
STATE_COLORS = {
    "patrol": (170, 170, 190),
    "investigate": (255, 210, 60),
    "hunt": (255, 70, 90),
    "search": (255, 150, 40),
}
DEMO_LENGTH = 5.0          # секунди по состојба кога се менуваат сами

STONE = (255, 170, 80)
SHRIEK = (255, 70, 190)
PLAYER = (120, 225, 255)


class StateDemo:
    def __init__(self, arena: pygame.Rect, audio):
        self.arena = arena
        self.audio = audio
        self.index = 0
        self.auto = True
        self.glow = theme.glow_circle(30, PLAYER, 0.6)
        self.start(0)

    # ================= Контрола =================

    @property
    def state(self) -> str:
        return STATES[self.index]

    def select(self, index: int, manual: bool = True) -> None:
        if manual:
            self.auto = False
            self.manual_t = 0.0
        self.start(index % len(STATES))

    def start(self, index: int) -> None:
        a = self.arena
        self.index = index
        self.t = 0.0
        self.rings = []                          # (центар, време на раѓање, боја, макс. радиус, дебелина)
        self.next_step = 0.4
        self.next_beat = 0.0
        self.events_done = set()
        self.marker = None
        self.manual_t = getattr(self, "manual_t", 0.0)

        self.left = pygame.Vector2(a.x + 70, a.centery + 20)
        self.right = pygame.Vector2(a.x + a.width * 0.55, a.centery + 20)
        self.player = pygame.Vector2(a.right - 60, a.centery - 15)
        self.stone_at = pygame.Vector2(a.x + a.width * 0.58, a.centery - 30)
        self.search_center = pygame.Vector2(a.x + a.width * 0.45, a.centery)

        self.monster = {
            "patrol": pygame.Vector2(self.left),
            "investigate": pygame.Vector2(self.left),
            "hunt": pygame.Vector2(a.x + 80, a.centery),
            "search": self.search_center + (55, 0),
        }[self.state]
        self.moving = False

    # ================= Ажурирање =================

    def update(self, dt: float) -> None:
        self.t += dt
        if self.auto and self.t >= DEMO_LENGTH:
            self.start((self.index + 1) % len(STATES))
        elif not self.auto:
            self.manual_t += dt
            if self.t >= DEMO_LENGTH:
                self.start(self.index)                   # рачно избрана: повторувај ја
            if self.manual_t > DEMO_LENGTH * 2.2:
                self.auto = True                          # по некое време пак сама

        getattr(self, "_" + self.state)(dt)
        self.rings = [r for r in self.rings if self.t - r[1] < 2.0]

    def _once(self, name: str, at: float) -> bool:
        """True точно еднаш, кога времето ќе помине `at` секунди."""
        if self.t >= at and name not in self.events_done:
            self.events_done.add(name)
            return True
        return False

    def _move_towards(self, target: pygame.Vector2, speed: float, dt: float, stop: float = 2.0) -> None:
        offset = target - self.monster
        dist = offset.length()
        self.moving = dist > stop
        if self.moving:
            self.monster += offset / dist * min(speed * dt, dist - stop)

    def _steps(self, interval: float, volume: float, loudness: float) -> None:
        """Чекори на чудовиштето: црвен бран + звук од соодветната страна."""
        if self.moving and self.t >= self.next_step:
            self.next_step = self.t + interval
            self.rings.append((pygame.Vector2(self.monster), self.t, (200, 40, 60), loudness, 2))
            self.audio.play("monster_step", volume, self._dx(self.monster))

    def _dx(self, pos: pygame.Vector2) -> float:
        return (pos.x - self.arena.centerx) * 3

    # ---------------- Четирите состојби ----------------

    def _patrol(self, dt: float) -> None:
        # Бавно лево-десно меѓу две точки.
        target = self.right if int(self.t / 2.5) % 2 == 0 else self.left
        self._move_towards(target, 48, dt)
        self.moving = True
        self._steps(0.9, 0.35, 70)

    def _investigate(self, dt: float) -> None:
        if self._once("stone", 0.4):
            self.rings.append((pygame.Vector2(self.stone_at), self.t, STONE, 150, 2))
            self.audio.play("stone", 0.7, self._dx(self.stone_at))
            self.marker = pygame.Vector2(self.stone_at)
        if self.t > 0.9:
            self._move_towards(self.stone_at, 90, dt, stop=4)
            self._steps(0.6, 0.5, 85)
        else:
            self.moving = False

    def _hunt(self, dt: float) -> None:
        if self._once("shriek", 0.25):
            self.rings.append((pygame.Vector2(self.monster), self.t, SHRIEK, 260, 3))
            self.rings.append((pygame.Vector2(self.monster), self.t + 0.15, SHRIEK, 200, 1))
            self.audio.play("shriek", 0.9, self._dx(self.monster))
            self.marker = pygame.Vector2(self.player)
        if self.t > 0.9:
            self._move_towards(self.player, 170, dt, stop=32)
            self._steps(0.33, 0.75, 100)
        else:
            self.moving = False
        # Срце: сè побрзо како што се приближува.
        closeness = 1 - min(1.0, self.monster.distance_to(self.player) / 380)
        if self.t > 0.6 and self.t >= self.next_beat:
            self.next_beat = self.t + (0.95 - 0.6 * closeness)
            self.audio.play("heartbeat", 0.35 + 0.5 * closeness, 0)

    def _search(self, dt: float) -> None:
        # Кружи околу последното место, застанува да ослушне, па продолжува.
        self.marker = self.search_center
        cycle = self.t % 2.2
        if cycle < 1.4:
            angle = self.t * 1.6
            target = self.search_center + pygame.Vector2(math.cos(angle) * 60, math.sin(angle) * 34)
            self._move_towards(target, 75, dt, stop=1)
            self.moving = True
            self._steps(0.75, 0.4, 70)
        else:
            self.moving = False          # ослушнува

    # ================= Цртање =================

    def draw(self, surface: pygame.Surface, t_global: float) -> None:
        a = self.arena
        theme.panel(surface, a, alpha=120, radius=16, border=STATE_COLORS[self.state])
        clip = surface.get_clip()
        surface.set_clip(a.inflate(-2, -2))

        # Ознака на последната позната позиција (жолт/портокалов крст)
        if self.marker is not None:
            col = STATE_COLORS[self.state] if self.state != "hunt" else SHRIEK
            m = self.marker
            pygame.draw.line(surface, col, m + (-6, -6), m + (6, 6), 2)
            pygame.draw.line(surface, col, m + (-6, 6), m + (6, -6), 2)

        for center, born, color, max_r, width in self.rings:
            age = self.t - born
            if age < 0:
                continue
            r = age * 260
            if r < max_r:
                ring(surface, center, r, color, int(200 * (1 - r / max_r)), width)

        # Играч (во лов: целта)
        surface.blit(self.glow, self.glow.get_rect(center=self.player), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surface, PLAYER, self.player, 7)

        # Чудовиште
        col = STATE_COLORS[self.state] if self.state != "patrol" else (255, 60, 95)
        listening = self.state == "search" and not self.moving
        size = 15 + (2 * math.sin(t_global * 10) if listening else 0)
        pygame.draw.polygon(surface, col, theme.monster_shape(self.monster, size, t_global * 6), 2)
        if listening:
            # „Ослушнува“: мали лакови како уши.
            for side in (-1, 1):
                rect = pygame.Rect(0, 0, 44, 44)
                rect.center = self.monster
                start = math.pi * (0.75 if side < 0 else -0.25)
                pygame.draw.arc(surface, col, rect.inflate(10, 10), start, start + 0.5, 1)

        surface.set_clip(clip)
