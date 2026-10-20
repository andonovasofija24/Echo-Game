"""Директор: „мозок 1“ (инспирирано од Alien: Isolation и AI Director во Left 4 Dead).

Играта има ДВА AI слоја:
  - Мозок 2 = секое чудовиште (ai/monster.py): слепо, знае САМО што слушнало.
  - Мозок 1 = Директорот (овој модул): СЕКОГАШ знае каде е играчот, но тоа
    никогаш не им го кажува директно на чудовиштата. Им дава само нејасни
    „насоки“: „патролирај во оваа зона“. Чудовиштето сепак мора да те СЛУШНЕ
    за да почне да лови.

Зошто? Без директор, тивок играч може никогаш да не сретне чудовиште и
играта станува досадна. Со директор кој ЗНАЕ сè, а го кажува тоа, играта
станува нефер. Решението е среде: директорот ја води НАПНАТОСТА.

Напнатост (tension) 0..1:
  расте брзо кога чудовиште е блиску, истражува или лови,
  паѓа полека кога е мирно.

Фази (циклус, како во L4D):
  ГРАДЕЊЕ  мирно е → по некое време директорот праќа најблиското чудовиште
           да патролира ВО БЛИЗИНА на играчот. Колку подолго е мирно, толку
           насоката е попрецизна (зоната се стеснува).
           Ако играчот е близу до излезот, едно чудовиште се праќа да го „чува“.
  ВРВ      нешто се случува (лов, чудовиште до тебе) → директорот не се меша.
  ОДМОР    по врвот, директорот ги праќа чудовиштата ПОДАЛЕКУ од играчот
           неколку секунди, да може да здивне. Потоа повторно ГРАДЕЊЕ.

Правичност: насоката е секогаш поместена најмалку неколку плочки од играчот,
и важи само за чудовишта што патролираат (не ги прекинува ловот и истрагата).

Меморија: при избор на зона, директорот ги преферира местата каде играчот
најчесто минувал во претходните игри (SQLite, data/memory.py).
"""

import random
from enum import Enum

import pygame

from ai.monster import State
from settings import (
    DIRECTOR_CALM_PER_LEVEL,
    DIRECTOR_EXIT_GUARD_DISTANCE,
    DIRECTOR_HINT_DURATION,
    DIRECTOR_HINT_INTERVAL,
    DIRECTOR_HINT_MAX_TILES,
    DIRECTOR_HINT_MIN_TILES,
    DIRECTOR_RELAX_TIME,
)


class Phase(Enum):
    BUILD = "build"
    PEAK = "peak"
    RELAX = "relax"


TENSION_RISE = 1.6         # во секунда: колку брзо расте напнатоста
TENSION_FALL = 0.12        # во секунда: колку бавно паѓа
PEAK_ENTER = 0.75
PEAK_EXIT = 0.35
DANGER_RADIUS = 320        # чудовиште поблиску од ова = закана


class Hint:
    """Насока што директорот ја дал (се чува за debug приказ)."""

    def __init__(self, monster, center: pygame.Vector2, radius_tiles: int, kind: str, time: float):
        self.monster = monster
        self.center = center
        self.radius_tiles = radius_tiles
        self.kind = kind            # "pressure", "exit", "relax"
        self.time = time


class Director:
    def __init__(self, session, level_index: int, rng: random.Random | None = None):
        self.session = session
        self.rng = rng or random.Random()
        self.calm_before_nudge = DIRECTOR_CALM_PER_LEVEL[min(level_index, len(DIRECTOR_CALM_PER_LEVEL) - 1)]

        self.tension = 0.0
        self.phase = Phase.BUILD
        self.calm_time = 0.0          # колку секунди е мирно (напнатост под прагот)
        self.phase_time = 0.0
        self.hint_cooldown = 0.0
        self.hints: list[Hint] = []
        self.exit_guarded = False

    # ================= Главна јамка =================

    def update(self, dt: float) -> None:
        s = self.session
        if s.game_over or not s.monsters:
            return
        self.phase_time += dt
        self.hint_cooldown = max(0.0, self.hint_cooldown - dt)
        self.hints = [h for h in self.hints if s.time - h.time < DIRECTOR_HINT_DURATION]

        # 1) Мери: колку е опасно во моментот?
        menace = self._menace()
        rate = TENSION_RISE if menace > self.tension else TENSION_FALL
        self.tension += (menace - self.tension) * min(1.0, rate * dt)
        self.calm_time = self.calm_time + dt if self.tension < 0.25 else 0.0

        # 2) Фази
        if self.phase == Phase.BUILD:
            if self.tension >= PEAK_ENTER:
                self._set_phase(Phase.PEAK)
            else:
                self._build_up()
        elif self.phase == Phase.PEAK:
            if self.tension <= PEAK_EXIT:
                self._set_phase(Phase.RELAX)
                self._relax()
        elif self.phase == Phase.RELAX:
            if self.tension >= PEAK_ENTER:
                self._set_phase(Phase.PEAK)
            elif self.phase_time >= DIRECTOR_RELAX_TIME:
                self._set_phase(Phase.BUILD)

    def _set_phase(self, phase: Phase) -> None:
        self.phase = phase
        self.phase_time = 0.0

    def _menace(self) -> float:
        """Закана 0..1 од гледна точка на играчот (ова директорот го знае, чудовиштата не)."""
        player = self.session.player.pos
        m = 0.0
        for monster in self.session.monsters:
            closeness = max(0.0, 1 - player.distance_to(monster.pos) / DANGER_RADIUS)
            m = max(m, closeness)
            if monster.state == State.HUNT:
                m = max(m, 1.0)
            elif monster.state in (State.INVESTIGATE, State.SEARCH):
                m = max(m, 0.55)
        return m

    # ================= ГРАДЕЊЕ =================

    def _build_up(self) -> None:
        if self.hint_cooldown > 0:
            return
        s = self.session

        # Играчот е близу до излезот, а е мирно: едно чудовиште оди да го „чува“.
        if (not self.exit_guarded and s.level.exit_rect is not None and self.calm_time > 3.0
                and s.player.pos.distance_to(s.level.exit_rect.center) < DIRECTOR_EXIT_GUARD_DISTANCE):
            monster = self._free_monster(nearest_to=pygame.Vector2(s.level.exit_rect.center))
            if monster:
                self._give_hint(monster, pygame.Vector2(s.level.exit_rect.center), 3, "exit")
                self.exit_guarded = True
                return

        if self.calm_time < self.calm_before_nudge:
            return

        monster = self._free_monster(nearest_to=s.player.pos)
        if monster is None:
            return

        # Колку подолго е мирно, толку попрецизна насоката (зоната се стеснува).
        extra = self.calm_time - self.calm_before_nudge
        k = min(1.0, extra / 25.0)
        radius = round(DIRECTOR_HINT_MAX_TILES - (DIRECTOR_HINT_MAX_TILES - DIRECTOR_HINT_MIN_TILES) * k)
        center = self._fuzzy_point_near(s.player.pos, radius)
        if center is not None:
            self._give_hint(monster, center, radius, "pressure")

    def _fuzzy_point_near(self, target: pygame.Vector2, radius_tiles: int) -> pygame.Vector2 | None:
        """Случајна проодна плочка НА РАСТОЈАНИЕ од целта: никогаш точно на играчот."""
        level = self.session.level
        tc, tr = level.to_tile(target)
        min_d = max(2, radius_tiles // 2)
        candidates = [t for t in level.floor_tiles
                      if min_d <= max(abs(t[0] - tc), abs(t[1] - tr)) <= radius_tiles]
        if not candidates:
            return None
        # Меморијата од претходни игри: директорот преферира места каде играчот
        # често минувал (+1 за да имаат шанса и непознатите плочки).
        heat = self.session.memory_heat
        weights = [1.0 + heat.get(t, 0.0) for t in candidates]
        return level.tile_center(*self.rng.choices(candidates, weights=weights, k=1)[0])

    # ================= ОДМОР =================

    def _relax(self) -> None:
        """По лов: чудовиштата што патролираат се праќаат подалеку од играчот."""
        s = self.session
        level = s.level
        player = s.player.pos
        for monster in s.monsters:
            if monster.state not in (State.PATROL, State.SEARCH):
                continue
            sample = self.rng.sample(level.floor_tiles, min(40, len(level.floor_tiles)))
            far = max(sample, key=lambda t: player.distance_to(level.tile_center(*t)))
            self._give_hint(monster, level.tile_center(*far), 4, "relax", force=True)
        self.calm_time = 0.0

    # ================= Помошно =================

    def _free_monster(self, nearest_to: pygame.Vector2):
        """Најблиското чудовиште што само патролира (не прекинуваме лов или истрага)."""
        free = [m for m in self.session.monsters if m.state == State.PATROL]
        if not free:
            return None
        return min(free, key=lambda m: m.pos.distance_to(nearest_to))

    def _give_hint(self, monster, center: pygame.Vector2, radius_tiles: int, kind: str,
                   force: bool = False) -> None:
        monster.receive_hint(center, radius_tiles, DIRECTOR_HINT_DURATION, force=force)
        self.hints = [h for h in self.hints if h.monster is not monster]
        self.hints.append(Hint(monster, center, radius_tiles, kind, self.session.time))
        self.hint_cooldown = DIRECTOR_HINT_INTERVAL

