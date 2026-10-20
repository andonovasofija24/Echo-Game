"""Камче: се фрла (кон курсорот или со E кон познато чудовиште) и прави
гласен звук каде ќе падне.

Три исходи:
  - одвлекување: падне далеку од чудовиштата → тие одат кон звукот,
  - промашување блиску: падне до чудовиште (без ѕид меѓу нив) → тоа се плаши
    и БЕГА во спротивен правец од тебе,
  - погодок: удри во чудовиште → чудовиштето е УНИШТЕНО.
"""

import pygame

from settings import SOUND_STONE, STONE_HIT_RADIUS, STONE_MAX_DISTANCE, STONE_SCARE_RADIUS, STONE_SPEED


class Stone:
    def __init__(self, start: pygame.Vector2, target: pygame.Vector2, level):
        self.pos = pygame.Vector2(start)
        self.origin = pygame.Vector2(start)     # од каде е фрлено (чудовиштето ќе го запомни)
        self.landed = False
        self.hit_monster = None
        self.scared: list = []
        self.level = level
        self.trail: list[pygame.Vector2] = []   # последните позиции (за опашката на екранот)

        to_target = pygame.Vector2(target) - self.pos
        wanted = min(to_target.length(), STONE_MAX_DISTANCE)
        self.direction = to_target.normalize() if wanted > 0 else pygame.Vector2(1, 0)

        # Однапред проверуваме дали на патот има ѕид. Ако има, камчето паѓа
        # малку пред него, наместо да лета низ ѕидот.
        free_dist, hit = level.raycast(self.pos, self.direction, wanted)
        self.distance_left = max(0.0, free_dist - 6) if hit else wanted

    def update(self, dt: float, sounds, monsters=()) -> None:
        if self.landed:
            return
        self.trail.append(pygame.Vector2(self.pos))
        self.trail = self.trail[-8:]
        step = min(STONE_SPEED * dt, self.distance_left)
        self.pos += self.direction * step
        self.distance_left -= step

        # Погодок: камчето удри во чудовиште на патот → уништено.
        for monster in monsters:
            if not monster.dead and self.pos.distance_to(monster.pos) < monster.radius + STONE_HIT_RADIUS:
                self.hit_monster = monster
                monster.kill()
                self.landed = True          # звукот на уништувањето го прави сесијата
                return

        if self.distance_left <= 0:
            self._land(sounds, monsters)

    def _land(self, sounds, monsters) -> None:
        self.landed = True
        event = sounds.emit(self.pos, SOUND_STONE, kind="stone", source="stone")
        # Промашување блиску: чудовиштата што го „видоа“ падот бегаат. Тие не го
        # третираат како звук за истражување (означено како веќе слушнато).
        for monster in monsters:
            if (not monster.dead and self.pos.distance_to(monster.pos) < STONE_SCARE_RADIUS
                    and self.level.is_line_clear(self.pos, monster.pos)):
                monster.scare(self.origin)
                event.heard_by.add(monster.uid)
                self.scared.append(monster)
