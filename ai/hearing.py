"""Перцепција: како чудовиштето слуша.

Чудовиштата се слепи. Единствената информација што ја добиваат за светот се
звуците, и тоа на ист начин како што ги гледа играчот:
  - звукот стигнува до увото дури кога БРАНОТ ќе стигне таму (не веднаш),
  - јачината опаѓа со растојанието,
  - ѕидовите меѓу звукот и увото дополнително го придушуваат.
"""

from dataclasses import dataclass

import pygame

from settings import HEARING_WALL_PENALTY


@dataclass
class Perception:
    pos: pygame.Vector2     # каде се случил звукот
    strength: float         # 0..1: колку јасно е слушнат
    kind: str
    source: str
    shared: bool = False    # True = позицијата е споделена од друго чудовиште (крик)


def listen(monster, sounds, level) -> list[Perception]:
    """Ги враќа сите звуци што ова чудовиште ги слушнало ВО ОВОЈ ФРЕЈМ."""
    heard = []
    for event in sounds.events:
        if monster.uid in event.heard_by:
            continue
        # Чудовиштата не реагираат на сопствените звуци ниту на туѓите чекори.
        # Единствен исклучок е КРИКОТ на друго чудовиште.
        if event.owner is monster or (event.source == "monster" and event.kind != "shriek"):
            event.heard_by.add(monster.uid)
            continue

        distance = monster.pos.distance_to(event.pos)

        if event.wave_radius < distance:
            if event.wave_radius >= event.loudness:
                event.heard_by.add(monster.uid)   # бранот замрел пред да стигне
            continue                              # бранот уште не стигнал до увото

        event.heard_by.add(monster.uid)

        walls = level.count_walls_between(event.pos, monster.pos)
        perceived = event.loudness - distance - walls * HEARING_WALL_PENALTY
        if perceived <= 0:
            continue

        if event.kind == "shriek" and event.info is not None:
            # Крикот не значи „дојди кај мене“, туку „ПЛЕНОТ Е ТАМУ“:
            # слушателот добива позиција што самиот никогаш не ја слушнал.
            heard.append(Perception(pygame.Vector2(event.info), perceived / event.loudness,
                                    event.kind, event.source, shared=True))
        else:
            heard.append(Perception(pygame.Vector2(event.pos), perceived / event.loudness,
                                    event.kind, event.source))
    return heard
