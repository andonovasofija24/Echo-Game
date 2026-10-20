"""Логика на играчот: позиција, движење, звуци што ги прави.

Овој модул НЕ црта ништо. Цртањето е одговорност на render слојот.
"""

import pygame

from game.controls import NO_ACTIONS, Actions
from game.stone import Stone
from settings import (
    PLAYER_AUTO_ROTATE,
    CLAP_COOLDOWN,
    PLAYER_RADIUS,
    PLAYER_SPEED_SNEAK,
    PLAYER_SPEED_WALK,
    SOUND_CLAP,
    SOUND_STEP_SNEAK,
    SOUND_STEP_WALK,
    STEP_INTERVAL_SNEAK,
    STEP_INTERVAL_WALK,
    STONE_COUNT,
)


class Player:
    def __init__(self, x: float, y: float):
        self.pos = pygame.Vector2(x, y)
        self.radius = PLAYER_RADIUS
        self.is_moving = False
        self.is_sneaking = False

        self.step_timer = 0.0
        self.clap_cooldown = 0.0
        self.stones = STONE_COUNT
        # Ротација: агол во степени (0 = десно, 90 = долу, бидејќи y оската оди надолу).
        # Играчот САМ постојано се врти, како сонар; E фрла во моменталната насока.
        self.angle = 0.0

    @property
    def facing(self) -> pygame.Vector2:
        """Единечен вектор во насоката во која е свртен играчот."""
        return pygame.Vector2(1, 0).rotate(self.angle)

    def update(self, dt: float, actions: Actions, level, sounds) -> None:
        """Го ажурира играчот за еден фрејм. dt е времето од претходниот фрејм во секунди."""
        actions = actions or NO_ACTIONS
        self.angle = (self.angle + PLAYER_AUTO_ROTATE * dt) % 360   # постојано вртење

        direction = pygame.Vector2(actions.move)
        if direction.length_squared() > 0:
            direction = direction.normalize()   # дијагонално не смее да е побрзо
        self.is_sneaking = actions.sneak
        self.is_moving = direction.length_squared() > 0

        speed = PLAYER_SPEED_SNEAK if self.is_sneaking else PLAYER_SPEED_WALK
        self.pos += direction * speed * dt

        # Два поминувања: во агол играчот може да допира два ѕида одеднаш,
        # а туркањето од едниот може да го втурне во другиот.
        for _ in range(2):
            self.pos = level.resolve_circle_collision(self.pos, self.radius)

        self._update_footsteps(dt, sounds)
        self.clap_cooldown = max(0.0, self.clap_cooldown - dt)

    def _update_footsteps(self, dt: float, sounds) -> None:
        """Додека се движи, играчот прави чекор на секои неколку десетинки од секунда.

        Ова е главната дилема на играта: чекорите ти покажуваат каде се ѕидовите,
        но истовремено ја откриваат твојата позиција.
        """
        if not self.is_moving:
            # Првиот чекор по стоење се слуша веднаш, без чекање.
            self.step_timer = STEP_INTERVAL_SNEAK if self.is_sneaking else STEP_INTERVAL_WALK
            return

        interval = STEP_INTERVAL_SNEAK if self.is_sneaking else STEP_INTERVAL_WALK
        loudness = SOUND_STEP_SNEAK if self.is_sneaking else SOUND_STEP_WALK

        self.step_timer += dt
        if self.step_timer >= interval:
            self.step_timer = 0.0
            sounds.emit(self.pos, loudness, kind="step", source="player")

    def try_clap(self, sounds) -> bool:
        """Плескање (Space): многу гласно, открива голем дел од пештерата."""
        if self.clap_cooldown > 0:
            return False
        self.clap_cooldown = CLAP_COOLDOWN
        sounds.emit(self.pos, SOUND_CLAP, kind="clap", source="player")
        return True

    def try_throw(self, target, level):
        """Фрла камче кон target ако има уште. Враќа Stone или None."""
        if self.stones <= 0:
            return None
        self.stones -= 1
        return Stone(self.pos, target, level)
