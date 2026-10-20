"""Систем за звук: секој звук е НАСТАН во светот на играта.

Ова е најважниот модул во играта, бидејќи ги поврзува двете главни механики:
  - render слојот ги користи звуците за да ги „види“ ѕидовите (ехо),
  - AI слојот (од фаза 4) ќе ги користи истите звуци за да го „слушне“ играчот.

Ова е игровен звук (логика), а не аудио. Вистинските звучни ефекти можат да се
додадат подоцна, но не се потребни за механиката.
"""

import math
from dataclasses import dataclass, field

import pygame

from settings import SOUND_FADE_TIME, SOUND_RAY_COUNT, SOUND_WAVE_SPEED

# Насоките на зраците се исти за секој звук, па ги пресметуваме само еднаш.
RAY_DIRECTIONS = [
    pygame.Vector2(math.cos(a), math.sin(a))
    for a in (2 * math.pi * i / SOUND_RAY_COUNT for i in range(SOUND_RAY_COUNT))
]


@dataclass
class Ray:
    direction: pygame.Vector2
    distance: float      # до каде стигнува зракот
    hit_wall: bool       # дали завршил во ѕид или само ја изгубил јачината

    @property
    def reveal_time(self) -> float:
        """Во која секунда (од почетокот на звукот) бранот стигнува до крајот на зракот."""
        return self.distance / SOUND_WAVE_SPEED


@dataclass
class SoundEvent:
    pos: pygame.Vector2
    loudness: float      # максимален дострел во пиксели
    kind: str            # "step", "clap", "stone", "monster_step", "shriek"
    source: str          # "player", "stone", "monster": AI знае кој го направил
    rays: list[Ray] = field(default_factory=list)
    age: float = 0.0
    owner: object = None                                # конкретниот објект што го испуштил
    heard_by: set = field(default_factory=set)          # кој веќе го обработил звукот
    info: pygame.Vector2 | None = None                  # крик: споделена позиција на играчот

    @property
    def wave_radius(self) -> float:
        return self.age * SOUND_WAVE_SPEED

    @property
    def lifetime(self) -> float:
        """Бранот се шири до својот максимум, а потоа ѕидовите уште згаснуваат."""
        return self.loudness / SOUND_WAVE_SPEED + SOUND_FADE_TIME

    @property
    def is_expired(self) -> bool:
        return self.age >= self.lifetime


class SoundSystem:
    def __init__(self, level):
        self.level = level
        self.events: list[SoundEvent] = []
        self.recent: list[SoundEvent] = []   # звуци настанати во овој фрејм

    def emit(self, pos: pygame.Vector2, loudness: float, kind: str, source: str,
             owner: object = None, info: pygame.Vector2 | None = None) -> SoundEvent:
        """Создава звук и веднаш ги пресметува зраците (геометријата не се менува)."""
        origin = pygame.Vector2(pos)
        rays = []
        for direction in RAY_DIRECTIONS:
            distance, hit = self.level.raycast(origin, direction, loudness)
            rays.append(Ray(direction, distance, hit))

        event = SoundEvent(origin, loudness, kind, source, rays, owner=owner, info=info)
        self.events.append(event)
        self.recent.append(event)
        return event

    def update(self, dt: float) -> None:
        """Се повикува на ПОЧЕТОК на секој фрејм, пред некој да емитува нови звуци."""
        self.recent.clear()
        for event in self.events:
            event.age += dt
        self.events = [e for e in self.events if not e.is_expired]
