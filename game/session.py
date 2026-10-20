"""Една партија (едно ниво): целата логика на играта, без прозорец и без цртање.

Порано ова беше дел од main.py. Сега е посебно, па истата партија може да ја
користат различни екрани (игра, пауза, крај), а main.py само ги менува екраните.
"""

import pygame

from collections import Counter

from settings import (
    AIM_ASSIST_ANGLE,
    MEMORY_SAMPLE_INTERVAL,
    MEMORY_SOUND_WEIGHT,
    SOUND_MONSTER_DEATH,
    STONE_COUNT,
    STONE_MAX_DISTANCE,
)
from ai.director import Director
from game.controls import NO_ACTIONS
from ai.monster import Monster
from game.awareness import PlayerAwareness
from game.level import Level
from game.player import Player
from game.sound import SoundSystem


class GameSession:
    def __init__(self, level_path, level_index: int, memory_heat: dict | None = None):
        self.level_index = level_index
        self.level = Level(level_path)
        self.player = Player(self.level.player_start.x, self.level.player_start.y)
        self.sounds = SoundSystem(self.level)
        self.stones = []
        self.monsters = [Monster(pos, self.level) for pos in self.level.monster_starts]
        self.director = Director(self, level_index)   # мозок 1: ја води напнатоста
        self.awareness = PlayerAwareness()             # што знае играчот за чудовиштата
        self.hits = 0
        self.effects: list[tuple] = []   # (позиција, време) на уништени чудовишта, за ефект на екранот

        # Меморија: она што чудовиштата го паметат од ПРЕТХОДНИТЕ игри (само за читање)...
        self.memory_heat = memory_heat or {}
        for m in self.monsters:
            m.memory_heat = self.memory_heat
        # ...и она што се снима во ОВАА игра (се запишува во базата на крајот).
        self.new_heat: Counter = Counter()
        self._sample_timer = 0.0
        self.time = 0.0
        self.won = False
        self.lost = False

        # Почетно плескање: играчот веднаш ја гледа собата каде се наоѓа.
        # Чудовиштата НЕ го слушаат (означено како веќе слушнато), за почетокот
        # да е фер: првиот звук што ќе го слушнат е твоја одлука.
        self.player.try_clap(self.sounds)
        for event in self.sounds.events:
            event.heard_by.update(m.uid for m in self.monsters)
        self.player.clap_cooldown = 0.0

    @property
    def game_over(self) -> bool:
        return self.won or self.lost

    # ================= Акции на играчот =================

    def clap(self) -> None:
        if not self.game_over:
            self.player.try_clap(self.sounds)

    def throw(self, target) -> None:
        """Фрли камче кон точка (глувче)."""
        if self.game_over:
            return
        stone = self.player.try_throw(target, self.level)
        if stone:
            self.stones.append(stone)

    def throw_at_monster(self) -> None:
        """Копче E: бело топче (камче) точно во насоката во која е ротиран играчот.
        Само ако познато чудовиште е речиси на линијата (±AIM_ASSIST_ANGLE), лета точно кон него."""
        target = self.aim_target
        direction = (target - self.player.pos).normalize() if target is not None else self.player.facing
        # Камчето лета ПРЕКУ целта (до максималниот дострел), за да може да погоди
        # и чудовиште што во меѓувреме мрднало по истата линија.
        self.throw(self.player.pos + direction * STONE_MAX_DISTANCE)

    @property
    def aim_target(self):
        """Познато чудовиште во насоката на гледање (за E и за маркерот на екранот), или None."""
        return self.awareness.target_in_cone(self.player.pos, self.player.facing,
                                             AIM_ASSIST_ANGLE, STONE_MAX_DISTANCE * 1.1)

    # ================= Еден фрејм =================

    def update(self, dt: float, actions=NO_ACTIONS) -> None:
        self.time += dt if not self.game_over else 0.0

        # Звуците секогаш стареат, па брановите завршуваат и по крајот.
        self.sounds.update(dt)

        for stone in self.stones:
            stone.update(dt, self.sounds, self.monsters)
            if stone.hit_monster is not None and stone.hit_monster.dead:
                self._monster_destroyed(stone.hit_monster)
                stone.hit_monster = None
        self.stones = [s for s in self.stones if not s.landed]

        if self.game_over:
            return

        self.player.update(dt, actions, self.level, self.sounds)

        # Чудовиштата се ажурираат ПОСЛЕ играчот, за да ги „слушнат“ неговите
        # звуци уште во истиот фрејм кога бранот ќе стигне до нив.
        for monster in self.monsters:
            monster.update(dt, self.sounds)
        for monster in self.monsters:
            monster.separate(self.monsters)
            if monster.touches(self.player.pos, self.player.radius):
                self.lost = True

        self.awareness.update(self)
        self._record_memory(dt)

        # Директорот гледа сè (вклучително каде е играчот) и одлучува дали
        # некое чудовиште треба да добие насока каде да патролира.
        self.director.update(dt)

        if not self.lost and self.level.is_on_exit(self.player.pos):
            self.won = True


    def _monster_destroyed(self, monster) -> None:
        """Погодено чудовиште: се отстранува, со ефект и звук (кој ги осветлува ѕидовите)."""
        self.hits += 1
        self.monsters = [m for m in self.monsters if m is not monster]
        self.effects.append((pygame.Vector2(monster.pos), self.time))
        # Другите чудовишта не реагираат на звуци од чудовишта (освен крик), па ова е само за играчот.
        self.sounds.emit(monster.pos, SOUND_MONSTER_DEATH, kind="monster_death", source="monster")

    # ================= Снимање за меморијата =================

    def _record_memory(self, dt: float) -> None:
        """Каде се движи играчот и каде прави бучава (за SQLite меморијата)."""
        self._sample_timer += dt
        if self._sample_timer >= MEMORY_SAMPLE_INTERVAL:
            self._sample_timer = 0.0
            self.new_heat[self.level.to_tile(self.player.pos)] += 1.0
        for event in self.sounds.recent:
            if event.source == "player":
                self.new_heat[self.level.to_tile(event.pos)] += MEMORY_SOUND_WEIGHT

    @property
    def stones_used(self) -> int:
        return STONE_COUNT - self.player.stones


def no_keys():
    """Без влез (за пауза и тестови)."""
    return NO_ACTIONS
