"""A* pathfinding на мрежата од плочки.

A* ја наоѓа најкратката патека од старт до цел. За секоја плочка чува:
  g = вистинска цена од стартот до неа,
  h = проценка (хевристика) од неа до целта,
  f = g + h  →  секогаш прво се проширува плочката со најмало f.
Хевристиката е „октилно растојание“: точната цена на празна мрежа со 8 насоки,
па A* е и брз и гарантирано наоѓа најкраток пат.
"""

import heapq
import math

SQRT2 = math.sqrt(2)

# (dx, dy, цена): 4 прави и 4 дијагонални насоки.
NEIGHBORS = [
    (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
    (1, 1, SQRT2), (1, -1, SQRT2), (-1, 1, SQRT2), (-1, -1, SQRT2),
]


def octile(a: tuple[int, int], b: tuple[int, int]) -> float:
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return (dx + dy) + (SQRT2 - 2) * min(dx, dy)


class PathResult:
    def __init__(self, path: list[tuple[int, int]], expanded: int):
        self.path = path              # листа плочки од старт до цел (празна = нема пат)
        self.expanded = expanded      # колку плочки разгледал A* (за debug/одбрана)


def astar(level, start: tuple[int, int], goal: tuple[int, int]) -> PathResult:
    if level.is_wall(*goal) or level.is_wall(*start):
        return PathResult([], 0)
    if start == goal:
        return PathResult([start], 0)

    open_heap = [(octile(start, goal), 0.0, start)]   # (f, g, плочка)
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    best_g = {start: 0.0}
    closed = set()

    while open_heap:
        _, g, current = heapq.heappop(open_heap)
        if current in closed:
            continue          # стар запис во редот, веќе најдовме подобар пат
        if current == goal:
            return PathResult(_reconstruct(came_from, current), len(closed))
        closed.add(current)

        cx, cy = current
        for dx, dy, cost in NEIGHBORS:
            nx, ny = cx + dx, cy + dy
            if level.is_wall(nx, ny):
                continue
            # Дијагонала е дозволена само ако двете соседни прави плочки се слободни,
            # инаку чудовиштето би „сечело“ агол низ ѕидот.
            if dx != 0 and dy != 0 and (level.is_wall(cx + dx, cy) or level.is_wall(cx, cy + dy)):
                continue

            new_g = g + cost
            neighbor = (nx, ny)
            if new_g < best_g.get(neighbor, float("inf")):
                best_g[neighbor] = new_g
                came_from[neighbor] = current
                heapq.heappush(open_heap, (new_g + octile(neighbor, goal), new_g, neighbor))

    return PathResult([], len(closed))


def _reconstruct(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
