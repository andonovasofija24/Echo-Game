"""Чудовиште: слепо суштество што лови по слух.

Мозокот е машина на состојби (Finite State Machine). Во секој момент
чудовиштето е во ТОЧНО ЕДНА состојба, а секоја состојба има:
  - свое однесување (каде оди, колку брзо),
  - јасни услови за премин во друга состојба.

        слаб звук                  силен звук / доволно сомнеж
  PATROL ─────────► INVESTIGATE ──────────────────────────────► HUNT
    ▲                    │ стигнало, нема никој                  │ стигнало, нема никој
    │                    ▼                                       │
    └──── истекло ─── SEARCH ◄───────────────────────────────────┘
          време

  Камче што паѓа БЛИСКУ (промашување) → FLEE: бега во спротивен правец од
  оној што фрлил, не слуша додека бега, па се враќа на PATROL.
  Камче што го ПОГОДИ → чудовиштето е уништено (се отстранува од играта).

Тимска работа (инспирирано од The Last of Us):
  Кога чудовиште САМО ќе те слушне и ќе почне да лови, испушта КРИК.
  Крикот ја носи позицијата каде те слушнало. Другите чудовишта што ќе го
  слушнат крикот тргнуваат кон ТВОЈАТА позиција, не кон чудовиштето што вреска.
  Тие самите не врескаат, за да нема бескрајна верига од крикови.
"""

import itertools
import random
from enum import Enum

import pygame

from ai.hearing import listen
from ai.pathfinding import astar
from settings import (
    HEARING_HUNT_THRESHOLD,
    MONSTER_RADIUS,
    MONSTER_SEPARATION,
    MONSTER_SPEED_HUNT,
    MONSTER_SPEED_INVESTIGATE,
    MONSTER_SPEED_PATROL,
    MONSTER_STEP_INTERVAL_HUNT,
    MONSTER_STEP_INTERVAL_PATROL,
    MEMORY_VISIT_CHANCE,
    MONSTER_STEP_LOUDNESS,
    PATROL_RADIUS_TILES,
    REPATH_INTERVAL,
    SEARCH_DURATION,
    SEARCH_RADIUS_TILES,
    SHRIEK_COOLDOWN,
    SHRIEK_LOUDNESS,
    FLEE_DISTANCE_TILES,
    FLEE_TIME,
    MONSTER_SPEED_FLEE,
)


class State(Enum):
    PATROL = "ПАТРОЛА"
    INVESTIGATE = "ИСТРАЖУВА"
    HUNT = "ЛОВИ"
    SEARCH = "ПРЕБАРУВА"
    FLEE = "БЕГА"


SPEEDS = {
    State.PATROL: MONSTER_SPEED_PATROL,
    State.INVESTIGATE: MONSTER_SPEED_INVESTIGATE,
    State.HUNT: MONSTER_SPEED_HUNT,
    State.SEARCH: MONSTER_SPEED_INVESTIGATE,
    State.FLEE: MONSTER_SPEED_FLEE,
}

SUSPICION_DECAY = 0.12        # во секунда: сомнежот полека исчезнува
SUSPICION_TO_HUNT = 0.6       # повеќе слаби звуци еден по друг = сигурно е нешто таму
STUCK_TIME = 1.5

_ids = itertools.count(1)


class Monster:
    def __init__(self, pos: pygame.Vector2, level, rng: random.Random | None = None):
        self.uid = next(_ids)
        self.pos = pygame.Vector2(pos)
        self.radius = MONSTER_RADIUS
        self.level = level
        self.rng = rng or random.Random()

        self.state = State.PATROL
        self.state_time = 0.0
        self.suspicion = 0.0
        self.last_known: pygame.Vector2 | None = None   # каде последно слушнал нешто сомнително

        self.path: list[pygame.Vector2] = []
        self.goal: pygame.Vector2 | None = None
        self.last_expanded = 0                          # колку плочки разгледал A* (debug)
        self.repath_timer = 0.0
        self.step_timer = 0.0
        self.stuck_timer = 0.0

        self.shriek_cooldown = 0.0
        self.wants_to_shriek = False
        self.answering_shriek = False   # дали лови затоа што друг извикал (за debug)

        # Насока од Директорот: „патролирај во оваа зона“ (чудовиштето не знае зошто).
        self.hint_center: pygame.Vector2 | None = None
        self.hint_radius = PATROL_RADIUS_TILES
        self.hint_timer = 0.0

        self.flee_timer = 0.0
        self.flee_from: pygame.Vector2 | None = None
        self.dead = False

        # Меморија од претходни игри (SQLite): плочка → колку често играчот бил таму.
        self.memory_heat: dict[tuple[int, int], float] = {}

        self._new_patrol_goal()

    # ================= Главна јамка =================

    def update(self, dt: float, sounds) -> None:
        self.state_time += dt
        self.repath_timer = max(0.0, self.repath_timer - dt)
        self.suspicion = max(0.0, self.suspicion - SUSPICION_DECAY * dt)
        self.shriek_cooldown = max(0.0, self.shriek_cooldown - dt)
        if self.hint_timer > 0:
            self.hint_timer -= dt
            if self.hint_timer <= 0:
                self.hint_center = None   # насоката истече: пак слободна патрола

        if self.state == State.FLEE:
            self._update_flee(dt, sounds)
            return

        # 1) ПЕРЦЕПЦИЈА: што слушнав?
        for p in listen(self, sounds, self.level):
            self._on_hear(p)

        # Крикот се испушта ПОСЛЕ обработката на сите звуци од фрејмот.
        if self.wants_to_shriek:
            self.wants_to_shriek = False
            self.shriek_cooldown = SHRIEK_COOLDOWN
            sounds.emit(self.pos, SHRIEK_LOUDNESS, kind="shriek", source="monster",
                        owner=self, info=pygame.Vector2(self.last_known))

        # 2) ОДЛУКА: однесување според состојбата
        self._think()

        # 3) АКЦИЈА: движење по патеката и чекори
        self._move(dt)
        self._footsteps(dt, sounds)

    # ================= Камче: бегство и уништување =================

    def kill(self) -> None:
        """Погодено од камче: уништено. Сесијата го отстранува од играта."""
        self.dead = True
        self.path = []

    def scare(self, threat: pygame.Vector2) -> None:
        """Камче падна блиску: бега во СПРОТИВЕН правец од `threat` (од каде е фрлено).

        Бира проодна плочка во близина што е НАЈДАЛЕКУ од заканата, и до која има пат.
        """
        self._change_state(State.FLEE)
        self.flee_timer = FLEE_TIME
        self.flee_from = pygame.Vector2(threat)
        self.wants_to_shriek = False
        self.suspicion = 0.0
        self.last_known = None

        cc, cr = self.level.to_tile(self.pos)
        r = FLEE_DISTANCE_TILES
        candidates = [t for t in self.level.floor_tiles if abs(t[0] - cc) <= r and abs(t[1] - cr) <= r]
        candidates.sort(key=lambda t: self.level.tile_center(*t).distance_to(self.flee_from), reverse=True)
        for tile in candidates[:12]:
            goal = self.level.tile_center(*tile)
            # Само цели што се навистина „подалеку“ од заканата отколку сега.
            if goal.distance_to(self.flee_from) > self.pos.distance_to(self.flee_from) and self._set_goal(goal):
                return
        self.path = []

    def _update_flee(self, dt: float, sounds) -> None:
        listen(self, sounds, self.level)      # додека бега не обрнува внимание на звуци
        self.flee_timer -= dt
        self._move(dt)
        self._footsteps(dt, sounds)
        if self.flee_timer <= 0 or not self.path:
            self.flee_from = None
            self._change_state(State.PATROL)
            self._new_patrol_goal()

    # ================= Перцепција → премини =================

    def _on_hear(self, perception) -> None:
        self.suspicion += perception.strength
        self.last_known = perception.pos

        if perception.shared:
            # Друго чудовиште извикало. Доаѓам да помогнам, но не вреснувам и јас.
            if self.state != State.HUNT:
                self._change_state(State.HUNT if perception.strength >= 0.25 else State.INVESTIGATE)
                self.answering_shriek = True
            self._set_goal(perception.pos, throttle=True)
            return

        strong = perception.strength >= HEARING_HUNT_THRESHOLD
        if strong or self.suspicion >= SUSPICION_TO_HUNT or self.state == State.HUNT:
            if self.state != State.HUNT:
                self._change_state(State.HUNT)
                self.answering_shriek = False
                if self.shriek_cooldown <= 0:
                    self.wants_to_shriek = True
            self._set_goal(perception.pos, throttle=True)
        else:
            self._change_state(State.INVESTIGATE)
            self.answering_shriek = False
            self._set_goal(perception.pos)

    def _think(self) -> None:
        arrived = not self.path

        if self.state == State.PATROL:
            if arrived:
                self._new_patrol_goal()

        elif self.state in (State.INVESTIGATE, State.HUNT):
            if arrived:
                # Стигнав каде што го слушнав звукот, а нема никој.
                self._change_state(State.SEARCH)
                self._new_search_goal()

        elif self.state == State.SEARCH:
            if self.state_time >= SEARCH_DURATION:
                self.last_known = None
                self.answering_shriek = False
                self._change_state(State.PATROL)
                self._new_patrol_goal()
            elif arrived:
                self._new_search_goal()

    def _change_state(self, new_state: State) -> None:
        if new_state != self.state:
            self.state = new_state
            self.state_time = 0.0

    # ================= Цели =================

    def _new_patrol_goal(self) -> None:
        if self.hint_center is not None:
            self._random_goal_near(self.hint_center, self.hint_radius)
        elif self.memory_heat and self.rng.random() < MEMORY_VISIT_CHANCE:
            self._visit_remembered_place()
        else:
            self._random_goal_near(self.pos, PATROL_RADIUS_TILES)

    def _visit_remembered_place(self) -> None:
        """Оди да провери едно од „омилените места“ на играчот од претходните игри.

        Изборот е случаен, но тежински: колку почесто играчот бил на некоја
        плочка, толку е поголема шансата чудовиштето да ја провери.
        """
        tiles = list(self.memory_heat)
        weights = [self.memory_heat[t] for t in tiles]
        for tile in self.rng.choices(tiles, weights=weights, k=3):
            if not self.level.is_wall(*tile) and self._set_goal(self.level.tile_center(*tile)):
                return
        self._random_goal_near(self.pos, PATROL_RADIUS_TILES)

    def receive_hint(self, center: pygame.Vector2, radius_tiles: int, duration: float,
                     force: bool = False) -> None:
        """Директорот кажува каде да патролира. Важи само за патрола (и пребарување
        ако force=True): насоката никогаш не прекинува лов или истрага."""
        self.hint_center = pygame.Vector2(center)
        self.hint_radius = radius_tiles
        self.hint_timer = duration
        if self.state == State.SEARCH and force:
            self.last_known = None
            self.answering_shriek = False
            self._change_state(State.PATROL)
        if self.state == State.PATROL:
            self._new_patrol_goal()

    def _new_search_goal(self) -> None:
        center = self.last_known if self.last_known is not None else self.pos
        self._random_goal_near(center, SEARCH_RADIUS_TILES)

    def _random_goal_near(self, center: pygame.Vector2, radius_tiles: int) -> None:
        """Случајна проодна плочка во близина, до која навистина има пат."""
        cc, cr = self.level.to_tile(center)
        candidates = [t for t in self.level.floor_tiles
                      if abs(t[0] - cc) <= radius_tiles and abs(t[1] - cr) <= radius_tiles]
        self.rng.shuffle(candidates)
        for tile in candidates[:10]:
            if self._set_goal(self.level.tile_center(*tile)):
                return
        self.path = []   # нема каде да оди; ќе проба пак следниот фрејм

    def _set_goal(self, goal: pygame.Vector2, throttle: bool = False) -> bool:
        """Пресметува A* патека до целта. Враќа False ако нема пат."""
        if throttle and self.repath_timer > 0 and self.path:
            self.goal = pygame.Vector2(goal)   # ќе се пресмета наскоро
            return True
        self.repath_timer = REPATH_INTERVAL

        result = astar(self.level, self.level.to_tile(self.pos), self.level.to_tile(goal))
        self.last_expanded = result.expanded
        if not result.path:
            return False

        # Плочки → точки во светот. Последната точка е точната цел, не центарот на плочката.
        points = [self.level.tile_center(c, r) for c, r in result.path[1:]]
        if points:
            points[-1] = pygame.Vector2(goal)
        else:
            points = [pygame.Vector2(goal)]
        self.path = points
        self.goal = pygame.Vector2(goal)
        self.stuck_timer = 0.0
        return True

    # ================= Движење =================

    def _move(self, dt: float) -> None:
        # Одложено пресметување на патеката во лов (throttle).
        if self.state == State.HUNT and self.goal is not None and self.repath_timer <= 0:
            if self.path and self.path[-1].distance_to(self.goal) > 1:
                self._set_goal(self.goal)

        if not self.path:
            return

        self._smooth_path()

        target = self.path[0]
        to_target = target - self.pos
        dist = to_target.length()
        step = SPEEDS[self.state] * dt

        if dist <= step:
            self.pos = pygame.Vector2(target)
            self.path.pop(0)
        else:
            old = pygame.Vector2(self.pos)
            self.pos += to_target / dist * step
            for _ in range(2):
                self.pos = self.level.resolve_circle_collision(self.pos, self.radius)

            # Ако се заглави на агол подолго време, се откажува од оваа цел.
            moved = self.pos.distance_to(old)
            self.stuck_timer = self.stuck_timer + dt if moved < step * 0.3 else 0.0
            if self.stuck_timer > STUCK_TIME:
                self.path = []
                self.stuck_timer = 0.0

    def _smooth_path(self) -> None:
        """Ако следната-следна точка е директно видлива, прескокни ја следната.

        A* враќа патека по центри на плочки (цик-цак). Со ова „затегнување на
        конецот“ чудовиштето оди по прави линии, што изгледа многу поприродно.
        """
        while len(self.path) >= 2 and self._clear_corridor(self.pos, self.path[1]):
            self.path.pop(0)

    def _clear_corridor(self, a: pygame.Vector2, b: pygame.Vector2) -> bool:
        """Линија на видливост за ТЕЛО со радиус: проверуваме три паралелни линии."""
        direction = b - a
        if direction.length_squared() < 1e-6:
            return True
        side = pygame.Vector2(-direction.y, direction.x).normalize() * self.radius
        return all(self.level.is_line_clear(a + o, b + o) for o in (pygame.Vector2(), side, -side))

    def _footsteps(self, dt: float, sounds) -> None:
        """Чудовиштето е слепо, но не е тивко: неговите чекори го откриваат."""
        if not self.path:
            return
        fast = self.state in (State.HUNT, State.FLEE)
        interval = MONSTER_STEP_INTERVAL_HUNT if fast else MONSTER_STEP_INTERVAL_PATROL
        self.step_timer += dt
        if self.step_timer >= interval:
            self.step_timer = 0.0
            sounds.emit(self.pos, MONSTER_STEP_LOUDNESS, kind="monster_step",
                        source="monster", owner=self)

    # ================= Група =================

    def separate(self, others: list["Monster"]) -> None:
        """Чудовиштата не се преклопуваат: ако се преблиску, се туркаат настрана.

        Ова е „separation“ правилото од Boids (Craig Reynolds): едноставно, но
        доволно за да не изгледаат како едно чудовиште кога бркаат заедно.
        """
        min_dist = self.radius * MONSTER_SEPARATION
        for other in others:
            if other is self:
                continue
            offset = self.pos - other.pos
            dist = offset.length()
            if 0 < dist < min_dist:
                self.pos += offset / dist * (min_dist - dist) * 0.5
        self.pos = self.level.resolve_circle_collision(self.pos, self.radius)

    # ================= Помошно =================

    def touches(self, other_pos: pygame.Vector2, other_radius: float) -> bool:
        # Чудовиште што бега не напаѓа.
        if self.state == State.FLEE or self.dead:
            return False
        return self.pos.distance_to(other_pos) < self.radius + other_radius
