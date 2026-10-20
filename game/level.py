"""Мапа на нивото: вчитување од текстуална датотека и проверка на судири.

Нивото е мрежа (grid) од плочки. Истата мрежа подоцна ќе ја користи
A* алгоритмот за наоѓање патека, затоа ја чуваме и како 2D листа.
"""

from pathlib import Path

import pygame

from settings import TILE_EXIT, TILE_MONSTER, TILE_PLAYER, TILE_SIZE, TILE_WALL


class Level:
    def __init__(self, path: str | Path):
        self.grid: list[list[bool]] = []      # True = ѕид
        self.walls: list[pygame.Rect] = []
        self.player_start = pygame.Vector2(TILE_SIZE * 1.5, TILE_SIZE * 1.5)
        self.exit_rect: pygame.Rect | None = None
        self.monster_starts: list[pygame.Vector2] = []
        self.floor_tiles: list[tuple[int, int]] = []   # сите проодни плочки (за патрола)
        self._load(Path(path))

    # ---------- Вчитување ----------

    def _load(self, path: Path) -> None:
        lines = [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines()]
        lines = [line for line in lines if line]          # игнорирај празни редови

        self.rows = len(lines)
        self.cols = max(len(line) for line in lines)

        for row, line in enumerate(lines):
            grid_row = []
            for col in range(self.cols):
                ch = line[col] if col < len(line) else TILE_WALL   # пократок ред = ѕид
                is_wall = ch == TILE_WALL
                grid_row.append(is_wall)

                rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if is_wall:
                    self.walls.append(rect)
                    continue
                self.floor_tiles.append((col, row))
                if ch == TILE_PLAYER:
                    self.player_start = pygame.Vector2(rect.center)
                elif ch == TILE_EXIT:
                    self.exit_rect = rect
                elif ch == TILE_MONSTER:
                    self.monster_starts.append(pygame.Vector2(rect.center))
            self.grid.append(grid_row)

    # ---------- Помошни функции ----------

    def is_wall(self, col: int, row: int) -> bool:
        """Надвор од мапата се смета за ѕид."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.grid[row][col]
        return True

    @staticmethod
    def to_tile(pos: pygame.Vector2) -> tuple[int, int]:
        return int(pos.x // TILE_SIZE), int(pos.y // TILE_SIZE)

    @staticmethod
    def tile_center(col: int, row: int) -> pygame.Vector2:
        return pygame.Vector2(col * TILE_SIZE + TILE_SIZE / 2, row * TILE_SIZE + TILE_SIZE / 2)

    def walls_near(self, pos: pygame.Vector2, radius: float) -> list[pygame.Rect]:
        """Ги враќа само ѕидовите околу дадена точка.

        Наместо да проверуваме судир со сите ~200 ѕида, гледаме само
        плочките околу играчот. Ова е едноставна просторна оптимизација.
        """
        min_col = int((pos.x - radius) // TILE_SIZE)
        max_col = int((pos.x + radius) // TILE_SIZE)
        min_row = int((pos.y - radius) // TILE_SIZE)
        max_row = int((pos.y + radius) // TILE_SIZE)

        nearby = []
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                if self.is_wall(col, row):
                    nearby.append(pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        return nearby

    def resolve_circle_collision(self, pos: pygame.Vector2, radius: float) -> pygame.Vector2:
        """Го турка кругот надвор од секој ѕид што го допира.

        За секој ѕид: најдиме ја најблиската точка од правоаголникот до центарот
        на кругот. Ако е поблиску од радиусот, има судир, па кругот го туркаме
        по линијата од таа точка кон центарот. Резултатот е „лизгање“ по ѕидот
        наместо целосно запирање, што е многу поприродно.
        """
        for wall in self.walls_near(pos, radius):
            closest_x = max(wall.left, min(pos.x, wall.right))
            closest_y = max(wall.top, min(pos.y, wall.bottom))
            offset = pygame.Vector2(pos.x - closest_x, pos.y - closest_y)
            dist_sq = offset.length_squared()

            if dist_sq < radius * radius:
                if dist_sq == 0:
                    # Центарот е точно на работ/внатре; турни нагоре (ретко се случува).
                    offset = pygame.Vector2(0, -1)
                    dist = 0.0
                else:
                    dist = dist_sq ** 0.5
                    offset /= dist
                pos += offset * (radius - dist)
        return pos

    def raycast(self, origin: pygame.Vector2, direction: pygame.Vector2,
                max_dist: float) -> tuple[float, bool]:
        """Испушта зрак низ мрежата и враќа (растојание, дали удрил во ѕид).

        Користи DDA алгоритам (Amanatides & Woo): наместо да оди пиксел по пиксел,
        скока директно од граница на плочка до следната граница. Така еден зрак
        чини само неколку чекори, па можеме да испуштиме стотици во фрејм.
        """
        tile = TILE_SIZE
        col = int(origin.x // tile)
        row = int(origin.y // tile)
        if self.is_wall(col, row):
            return 0.0, True

        dx, dy = direction.x, direction.y
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1

        # Колку растојание по зракот треба за да се помине една цела плочка по x / y.
        t_delta_x = abs(tile / dx) if dx != 0 else float("inf")
        t_delta_y = abs(tile / dy) if dy != 0 else float("inf")

        # Растојание до ПРВАТА граница по x / y.
        if dx > 0:
            t_max_x = ((col + 1) * tile - origin.x) / dx
        elif dx < 0:
            t_max_x = (origin.x - col * tile) / -dx
        else:
            t_max_x = float("inf")
        if dy > 0:
            t_max_y = ((row + 1) * tile - origin.y) / dy
        elif dy < 0:
            t_max_y = (origin.y - row * tile) / -dy
        else:
            t_max_y = float("inf")

        while True:
            if t_max_x < t_max_y:
                t = t_max_x
                t_max_x += t_delta_x
                col += step_x
            else:
                t = t_max_y
                t_max_y += t_delta_y
                row += step_y

            if t > max_dist:
                return max_dist, False
            if self.is_wall(col, row):
                return t, True

    def is_line_clear(self, a: pygame.Vector2, b: pygame.Vector2) -> bool:
        """Дали меѓу две точки нема ѕид (линија на видливост)."""
        offset = pygame.Vector2(b) - a
        dist = offset.length()
        if dist < 1e-6:
            return True
        _, hit = self.raycast(pygame.Vector2(a), offset / dist, dist)
        return not hit

    def count_walls_between(self, a: pygame.Vector2, b: pygame.Vector2) -> int:
        """Колку ѕидни плочки пресекува права линија од a до b.

        Го користи слухот: звук зад два ѕида е многу потивок од звук зад еден.
        Земаме примероци на секоја половина плочка и броиме различни ѕидни плочки.
        """
        offset = pygame.Vector2(b) - a
        dist = offset.length()
        if dist < 1e-6:
            return 0
        steps = int(dist / (TILE_SIZE / 2)) + 1
        seen = set()
        for i in range(1, steps):
            p = pygame.Vector2(a) + offset * (i / steps)
            tile = self.to_tile(p)
            if self.is_wall(*tile):
                seen.add(tile)
        return len(seen)

    def is_on_exit(self, pos: pygame.Vector2) -> bool:
        return self.exit_rect is not None and self.exit_rect.collidepoint(pos)
