"""Што ЗНАЕ играчот за чудовиштата.

Камчето со копчето E лета во насоката во која гледа играчот. Ако во тој
правец има чудовиште за кое играчот ЗНАЕ, камчето малку се закачува на него
(aim assist). Невидливите чудовишта не се нишанат, бидејќи тоа би било мамење.

Играчот дознава за чудовиште на два начини (исти правила како другаде):
  1. го СЛУШНАЛ: чекор или крик на чудовиштето, кога бранот ќе стигне до
     играчот, а не е предалеку или зад премногу ѕидови,
  2. го ВИДЕЛ: негов бран (чекор, плескање, камче) поминал преку чудовиштето
     без ѕид помеѓу нив, или чудовиштето е многу блиску.

За секое чудовиште се памети ПОСЛЕДНАТА позната позиција (не вистинската!)
и кога е дознаена. По неколку секунди знаењето застарува.
"""

import pygame

from settings import AWARENESS_MEMORY, HEARING_WALL_PENALTY

LISTENER = "player_awareness"


class Sighting:
    def __init__(self, monster, pos: pygame.Vector2, time: float):
        self.monster = monster
        self.pos = pygame.Vector2(pos)
        self.time = time


class PlayerAwareness:
    def __init__(self):
        self.known: dict[int, Sighting] = {}     # uid на чудовиште → последно видување

    def update(self, session) -> None:
        player = session.player.pos
        level = session.level
        now = session.time

        for event in session.sounds.events:
            # 1) Слушнал звук од чудовиште
            if event.source == "monster" and LISTENER not in event.heard_by:
                d = player.distance_to(event.pos)
                if event.wave_radius >= d:
                    event.heard_by.add(LISTENER)
                    walls = level.count_walls_between(event.pos, player)
                    if event.loudness * 1.5 - d - walls * HEARING_WALL_PENALTY > 0 and event.owner is not None:
                        self._remember(event.owner, event.pos, now)
                elif event.wave_radius >= event.loudness * 1.5:
                    event.heard_by.add(LISTENER)

            # 2) Твој бран (или камче) го допрел чудовиштето
            elif event.source in ("player", "stone"):
                r = event.wave_radius
                for m in session.monsters:
                    d = m.pos.distance_to(event.pos)
                    if d <= event.loudness and abs(r - d) < 40 and level.is_line_clear(event.pos, m.pos):
                        self._remember(m, m.pos, now)

        # 3) Многу блиску: го „чувствуваш“
        for m in session.monsters:
            if m.pos.distance_to(player) < 70:
                self._remember(m, m.pos, now)

        # Застарено знаење (и уништени чудовишта) се заборава
        alive = {m.uid for m in session.monsters}
        self.known = {uid: s for uid, s in self.known.items()
                      if now - s.time < AWARENESS_MEMORY and uid in alive}

    def _remember(self, monster, pos, now: float) -> None:
        self.known[monster.uid] = Sighting(monster, pos, now)

    def target_in_cone(self, player_pos: pygame.Vector2, facing: pygame.Vector2,
                       max_angle: float, max_dist: float) -> pygame.Vector2 | None:
        """Aim assist за E: најблиското ПОЗНАТО чудовиште во конус околу насоката на играчот.

        Камчето секогаш оди таму каде гледаш. Само ако во тој правец (±max_angle)
        има чудовиште за кое знаеш, малку се „закачува“ на него.
        """
        best, best_d = None, max_dist
        for s in self.known.values():
            offset = s.pos - player_pos
            d = offset.length()
            if d < 1 or d > best_d:
                continue
            angle = abs((facing.angle_to(offset) + 180) % 360 - 180)   # агол меѓу -180 и 180
            if angle <= max_angle:
                best, best_d = s.pos, d
        return pygame.Vector2(best) if best is not None else None
