"""Presentation слој: го црта СВЕТОТ на играта (без менија и HUD).

Renderer-от само ЧИТА од состојбата на играта и никогаш не ја менува.

Редослед на цртање (од позади кон напред):
  1. позадина (омбре + шари, кеширана) и прашина
  2. светлосен слој: брановите и откриените ѕидови, со bloom
  3. излез, камчиња, чудовишта, играч, нишан
  4. debug слој (F1)

Bloom техника:
  Светлото се црта на посебна црна површина, која потоа се намалува (blur),
  засилува и се додава на екранот со BLEND_ADD, заедно со острата верзија.
"""

import math

import pygame

from ai.monster import State
from settings import (
    COLOR_DEBUG_DIRECTOR,
    COLOR_DEBUG_HEAT,
    COLOR_DEBUG_PATH,
    COLOR_DEBUG_SOUND_MEMORY,
    COLOR_DEBUG_WALL,
    COLOR_EXIT,
    COLOR_MONSTER,
    COLOR_PLAYER,
    COLOR_STONE,
    COLOR_FLEE,
    COLOR_WAVE_CLAP,
    COLOR_WAVE_DEATH,
    COLOR_WAVE_MONSTER,
    COLOR_WAVE_SHRIEK,
    COLOR_WAVE_STEP,
    COLOR_WAVE_STONE,
    EXIT_GLOW_RADIUS,
    EXIT_PULSE_SPEED,
    PLAYER_GLOW_RADIUS,
    SOUND_FADE_TIME,
    SOUND_WAVE_SPEED,
    STONE_MAX_DISTANCE,
    STONE_RADIUS,
    TILE_SIZE,
)
from ui import theme
from ui.i18n import tr

# Бојата на бранот по вид звук, и колку таа боја „надвладува“ над бојата
# на омбрето. Твоите звуци се речиси целосно во тонот на пештерата
# (хармонично), а звуците на чудовиштата остануваат јасно црвени (опасност).
WAVE_STYLE = {
    "step": (COLOR_WAVE_STEP, 0.25),
    "clap": (COLOR_WAVE_CLAP, 0.15),
    "stone": (COLOR_WAVE_STONE, 0.55),
    "monster_step": (COLOR_WAVE_MONSTER, 0.75),
    "shriek": (COLOR_WAVE_SHRIEK, 0.8),
    "monster_death": (COLOR_WAVE_DEATH, 0.7),
}

BLOOM_DOWNSCALE = 4


def scale_color(color: tuple, k: float) -> tuple:
    k = max(0.0, min(1.0, k))
    return int(color[0] * k), int(color[1] * k), int(color[2] * k)


class WorldRenderer:
    def __init__(self, size: tuple[int, int]):
        self.size = size
        w, h = size
        self.light = pygame.Surface(size)
        self.bloom_small = (w // BLOOM_DOWNSCALE, h // BLOOM_DOWNSCALE)
        self.bloom_tiny = (w // (BLOOM_DOWNSCALE * 3), h // (BLOOM_DOWNSCALE * 3))

        self.player_glow = theme.glow_circle(PLAYER_GLOW_RADIUS, COLOR_PLAYER)
        self.exit_glow = theme.glow_circle(EXIT_GLOW_RADIUS, COLOR_EXIT)
        self.monster_glow = theme.glow_circle(45, COLOR_MONSTER)
        self.stone_glow = theme.glow_circle(24, COLOR_STONE, 0.9)
        self.motes = theme.Motes(size, count=55)
        self.background = theme.background(size, seed=1)
        self.debug_font = theme.font(14, "medium")

    def set_level(self, level_index: int) -> None:
        """Секое ниво има малку поинакви шари во позадината (различен seed)."""
        self.background = theme.background(self.size, seed=11 + level_index * 7)

    # ================= Главна функција =================

    def draw(self, surface: pygame.Surface, session, dt: float, mouse_pos, debug: bool,
             show_aim: bool = True) -> None:
        surface.blit(self.background, (0, 0))
        self.motes.update(dt)
        self.motes.draw(surface)

        if debug:
            self._draw_debug_heat(surface, session)
            self._draw_debug_walls(surface, session.level)

        self.light.fill((0, 0, 0))
        for event in session.sounds.events:
            self._draw_sound(event)
        self._apply_light(surface)

        self._draw_exit(surface, session.level, session.time)
        self._draw_effects(surface, session)
        for monster in session.monsters:
            self._draw_monster(surface, monster, session, debug)
        if show_aim and not session.game_over:
            self._draw_throw_guide(surface, session)
        self._draw_player(surface, session.player)
        self._draw_stones(surface, session.stones)
        if show_aim and not session.game_over:
            self._draw_aim(surface, session.player, mouse_pos)
            self._draw_monster_target(surface, session)

        if debug:
            self._draw_debug_director(surface, session)
            for monster in session.monsters:
                self._draw_debug_monster(surface, monster)
            self._draw_debug_text(surface, session)

    # ================= Ехо =================

    def _draw_sound(self, event) -> None:
        """Брановиот фронт и ѕидовите што ги допрел.

        За секој зрак ја знаеме далечината до ѕидот. Бранот на растојание r:
          - ако r < далечината: фронтот е уште во воздух на растојание r,
          - ако r >= далечината: бранот стигнал до ѕидот, тој дел свети и згаснува.
        Бојата на ѕидот = бојата на омбрето на тоа место, измешана со бојата на звукот.
        """
        wave_color, weight = WAVE_STYLE.get(event.kind, (COLOR_WAVE_STEP, 0.3))
        radius = event.wave_radius
        origin = event.pos
        rays = event.rays
        n = len(rays)
        angle_step = 2 * math.pi / n

        front_strength = 0.8 * (1 - radius / event.loudness) if radius < event.loudness else 0.0
        front_color = theme.lerp_color(theme.wall_tint(origin, self.size), wave_color, max(weight, 0.35))

        for i in range(n):
            a = rays[i]
            b = rays[(i + 1) % n]

            # --- 1) Осветлени ѕидови ---
            if a.hit_wall and b.hit_wall and radius >= a.distance and radius >= b.distance:
                pa = origin + a.direction * a.distance
                pb = origin + b.direction * b.distance

                if self._same_wall(pa, pb, a, b, angle_step):
                    since_hit = event.age - max(a.reveal_time, b.reveal_time)
                    fade = 1 - since_hit / SOUND_FADE_TIME
                    falloff = 1 - min(a.distance, b.distance) / event.loudness
                    flash = 0.6 if since_hit < 0.12 else 0.0      # блесок при удар
                    k = fade * (0.35 + 0.65 * falloff) + flash
                    if k > 0.02:
                        tint = theme.wall_tint(pa, self.size)
                        color = theme.lerp_color(tint, wave_color, weight)
                        pygame.draw.line(self.light, scale_color(color, k), pa, pb, 2)

            # --- 2) Бранов фронт во воздух ---
            if front_strength > 0.02 and radius < a.distance and radius < b.distance:
                pa = origin + a.direction * radius
                pb = origin + b.direction * radius
                pygame.draw.line(self.light, scale_color(front_color, front_strength), pa, pb, 2)

    @staticmethod
    def _same_wall(pa, pb, a, b, angle_step: float) -> bool:
        """Дали две соседни точки на удар се на исто лице од ѕид (смееме да ги споиме).

        Зраците удираат секогаш на граница меѓу плочки (x или y делив со TILE_SIZE).
        Точки на иста граница и поблиску од една плочка се на исто лице;
        отворите се широки најмалку една плочка, па нив не ги премостуваме.
        """
        gap = pa.distance_to(pb)
        on_same_x = abs(pa.x - pb.x) < 0.5 and abs(pa.x / TILE_SIZE - round(pa.x / TILE_SIZE)) < 0.01
        on_same_y = abs(pa.y - pb.y) < 0.5 and abs(pa.y / TILE_SIZE - round(pa.y / TILE_SIZE)) < 0.01
        if (on_same_x or on_same_y) and gap < TILE_SIZE * 0.9:
            return True
        return gap <= max(8.0, max(a.distance, b.distance) * angle_step * 1.5)

    def _apply_light(self, surface: pygame.Surface) -> None:
        small = pygame.transform.smoothscale(self.light, self.bloom_small)
        small.blit(small, (0, 0), special_flags=pygame.BLEND_ADD)   # x2
        small.blit(small, (0, 0), special_flags=pygame.BLEND_ADD)   # x4
        tiny = pygame.transform.smoothscale(small, self.bloom_tiny)
        tiny.blit(tiny, (0, 0), special_flags=pygame.BLEND_ADD)

        wide = pygame.transform.smoothscale(tiny, self.size)
        near = pygame.transform.smoothscale(small, self.size)
        surface.blit(wide, (0, 0), special_flags=pygame.BLEND_ADD)
        surface.blit(near, (0, 0), special_flags=pygame.BLEND_ADD)
        surface.blit(self.light, (0, 0), special_flags=pygame.BLEND_ADD)

    # ================= Објекти =================

    def _draw_player(self, surface, player) -> None:
        """Играчот е ротиран: тело (круг) + „нос“ во насоката на гледање + очи."""
        rect = self.player_glow.get_rect(center=(int(player.pos.x), int(player.pos.y)))
        surface.blit(self.player_glow, rect, special_flags=pygame.BLEND_ADD)
        core = COLOR_PLAYER if not player.is_sneaking else scale_color(COLOR_PLAYER, 0.55)
        f = player.facing
        side = pygame.Vector2(-f.y, f.x)
        r = player.radius

        # Нос (стрелка) што се врти заедно со играчот
        tip = player.pos + f * (r + 15)
        base = player.pos + f * (r - 2)
        pygame.draw.polygon(surface, core, [tip, base + side * 8, base - side * 8])
        pygame.draw.circle(surface, core, player.pos, r)
        # Две „очи“ напред: веднаш се гледа каде е свртен
        for k in (-1, 1):
            pygame.draw.circle(surface, (255, 255, 255), player.pos + f * 4 + side * (4 * k), 2.6)

    def _draw_throw_guide(self, surface, session) -> None:
        """Линија за нишанење: каде ТОЧНО ќе лета камчето ако притиснеш E (до ѕид или до дометот)."""
        player = session.player
        if player.stones <= 0:
            return
        target = session.aim_target
        direction = (target - player.pos).normalize() if target is not None else player.facing
        length, _ = session.level.raycast(player.pos, direction, STONE_MAX_DISTANCE)
        locked = target is not None
        col = COLOR_WAVE_STONE if locked else COLOR_STONE
        start = player.radius + 18
        dist = start
        i = 0
        while dist < length:
            k = 1 - (dist / max(length, 1)) * 0.75
            pygame.draw.circle(surface, scale_color(col, k * (0.9 if locked else 0.55)),
                               player.pos + direction * dist, 2 if i % 4 else 2.5)
            dist += 12
            i += 1
        # Крај на линијата: мал крст (каде камчето ќе падне ако не погоди ништо)
        end = player.pos + direction * length
        side = pygame.Vector2(-direction.y, direction.x) * 5
        pygame.draw.line(surface, scale_color(col, 0.5), end - side, end + side, 1)

    def _draw_exit(self, surface, level, time: float) -> None:
        """Излезот е единственото нешто што секогаш свети: тоа е целта."""
        if level.exit_rect is None:
            return
        pulse = 0.75 + 0.25 * math.sin(time * EXIT_PULSE_SPEED)
        size = int(self.exit_glow.get_width() * pulse)
        glow = pygame.transform.smoothscale(self.exit_glow, (size, size))
        surface.blit(glow, glow.get_rect(center=level.exit_rect.center), special_flags=pygame.BLEND_ADD)

        cx, cy = level.exit_rect.center
        r = 7 + 2 * pulse
        pygame.draw.polygon(surface, COLOR_EXIT, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], 2)

    def _draw_stones(self, surface, stones) -> None:
        """Камчето во лет: опашка, сјај и светло јадро, за јасно да се гледа."""
        for stone in stones:
            if stone.landed:
                continue
            n = len(stone.trail)
            for i, p in enumerate(stone.trail):
                k = (i + 1) / (n + 1)
                pygame.draw.circle(surface, scale_color(COLOR_STONE, k * 0.7), p, max(1, int((STONE_RADIUS + 2) * k)))
            surface.blit(self.stone_glow, self.stone_glow.get_rect(center=(int(stone.pos.x), int(stone.pos.y))),
                         special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(surface, COLOR_STONE, stone.pos, STONE_RADIUS + 3)   # бело топче

    @staticmethod
    def _draw_effects(surface, session) -> None:
        """Уништено чудовиште: парчиња што се распрскуваат и прстен што згаснува."""
        for pos, born in session.effects:
            age = session.time - born
            if age > 1.2:
                continue
            k = age / 1.2
            fade = 1 - k
            pygame.draw.circle(surface, scale_color(COLOR_MONSTER, fade), pos, 14 + 60 * k, 2)
            for i in range(10):
                a = i * math.tau / 10 + 0.3
                p = pos + pygame.Vector2(math.cos(a), math.sin(a)) * (10 + 70 * k)
                q = p + pygame.Vector2(math.cos(a), math.sin(a)) * 6
                pygame.draw.line(surface, scale_color(COLOR_WAVE_DEATH, fade), p, q, 2)

    @staticmethod
    def _draw_aim(surface, player, mouse_pos) -> None:
        """Мал нишан на курсорот, ограничен на дострелот на камчето."""
        if player.stones <= 0:
            return
        to_mouse = pygame.Vector2(mouse_pos) - player.pos
        if to_mouse.length() > STONE_MAX_DISTANCE:
            to_mouse.scale_to_length(STONE_MAX_DISTANCE)
        target = player.pos + to_mouse
        dim = scale_color(COLOR_WAVE_STONE, 0.6)
        pygame.draw.circle(surface, dim, target, 7, 1)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            pygame.draw.line(surface, dim, target + (dx * 9, dy * 9), target + (dx * 13, dy * 13))

    def _draw_monster_target(self, surface, session) -> None:
        """Портокалова цел: познато чудовиште во насоката во која гледаш (aim assist за E).
        Тоа е последната ПОЗНАТА позиција: чудовиштето можеби веќе мрднало."""
        if session.player.stones <= 0:
            return
        target = session.aim_target
        if target is None:
            return
        t = session.time
        r = 14 + 2 * math.sin(t * 5)
        col = scale_color(COLOR_WAVE_STONE, 0.85)
        for k in range(4):
            a = t * 1.5 + k * math.pi / 2
            p1 = target + pygame.Vector2(math.cos(a), math.sin(a)) * r
            p2 = target + pygame.Vector2(math.cos(a + 0.6), math.sin(a + 0.6)) * r
            pygame.draw.line(surface, col, p1, p2, 2)
        label = self.debug_font.render("E", True, col)
        surface.blit(label, (target.x + r + 4, target.y - r - 4))

    # ================= Чудовиште =================

    @staticmethod
    def _monster_visibility(monster, session) -> float:
        """Видливо е само кога ТУЃ бран поминал преку него (без ѕид меѓу нив),
        или кога е многу блиску до играчот. Потоа згаснува исто како ѕидовите."""
        best = 0.0
        for event in session.sounds.events:
            if event.source == "monster" and event.kind != "shriek":
                continue
            d = monster.pos.distance_to(event.pos)
            if d > event.loudness or event.wave_radius < d:
                continue
            if event.owner is not monster and not session.level.is_line_clear(event.pos, monster.pos):
                continue
            since = event.age - d / SOUND_WAVE_SPEED
            best = max(best, 1 - since / SOUND_FADE_TIME)
        near = session.player.pos.distance_to(monster.pos)
        best = max(best, 1 - near / 70)
        return max(0.0, min(1.0, best))

    def _draw_monster(self, surface, monster, session, debug: bool) -> None:
        vis = 1.0 if debug else self._monster_visibility(monster, session)
        if vis <= 0.02:
            return
        glow = self.monster_glow.copy()
        glow.fill(scale_color((255, 255, 255), vis), special_flags=pygame.BLEND_MULT)
        surface.blit(glow, glow.get_rect(center=(int(monster.pos.x), int(monster.pos.y))),
                     special_flags=pygame.BLEND_ADD)
        fleeing = monster.state == State.FLEE
        speed = 12 if fleeing else 6                         # што бега: трепери побрзо (паника)
        size = monster.radius * (0.8 if fleeing else 1.0)    # и се „собира“
        points = theme.monster_shape(monster.pos, size, session.time * speed + monster.uid)
        color = COLOR_FLEE if fleeing else COLOR_MONSTER
        pygame.draw.polygon(surface, scale_color(color, vis), points, 2)

    # ================= Debug =================

    @staticmethod
    def _draw_debug_walls(surface, level) -> None:
        for wall in level.walls:
            pygame.draw.rect(surface, COLOR_DEBUG_WALL, wall, 1)

    def _draw_debug_monster(self, surface, monster) -> None:
        """A* патека, последна позната позиција, состојба, сомнеж."""
        if monster.path:
            pts = [monster.pos] + monster.path
            pygame.draw.lines(surface, COLOR_DEBUG_PATH, False, pts, 1)
            for p in monster.path:
                pygame.draw.circle(surface, COLOR_DEBUG_PATH, p, 2)
        if monster.last_known is not None:
            lk = monster.last_known
            color = COLOR_WAVE_SHRIEK if monster.answering_shriek else COLOR_DEBUG_SOUND_MEMORY
            pygame.draw.line(surface, color, lk + (-6, -6), lk + (6, 6), 2)
            pygame.draw.line(surface, color, lk + (-6, 6), lk + (6, -6), 2)
            if monster.answering_shriek:
                pygame.draw.line(surface, scale_color(color, 0.5), monster.pos, lk, 1)

        colors = {State.PATROL: (170, 170, 190), State.INVESTIGATE: (255, 210, 60),
                  State.HUNT: (255, 70, 90), State.SEARCH: (255, 150, 40), State.FLEE: COLOR_FLEE}
        name = tr("state_" + monster.state.name.lower())
        label = f"{name}  {monster.suspicion:.2f}  A*:{monster.last_expanded}"
        surf = self.debug_font.render(label, True, colors[monster.state])
        surface.blit(surf, (monster.pos.x - surf.get_width() / 2, monster.pos.y - 36))

    def _draw_debug_heat(self, surface, session) -> None:
        """Меморијата од претходните игри: портокалово = места каде често си била."""
        heat = getattr(session, "memory_heat", None)
        if not heat:
            return
        top = max(heat.values())
        layer = pygame.Surface(self.size, pygame.SRCALPHA)
        for (c, r), w in heat.items():
            alpha = int(150 * (w / top) ** 0.6)
            if alpha > 6:
                layer.fill((*COLOR_DEBUG_HEAT, alpha), (c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        surface.blit(layer, (0, 0))

    def _draw_debug_director(self, surface, session) -> None:
        """Насоките на Директорот: зона (круг) и линија од чудовиштето до неа."""
        director = getattr(session, "director", None)
        if director is None:
            return
        layer = pygame.Surface(self.size, pygame.SRCALPHA)
        for hint in director.hints:
            r = hint.radius_tiles * TILE_SIZE
            pygame.draw.circle(layer, (*COLOR_DEBUG_DIRECTOR, 28), hint.center, r)
            pygame.draw.circle(layer, (*COLOR_DEBUG_DIRECTOR, 150), hint.center, r, 1)
            pygame.draw.line(layer, (*COLOR_DEBUG_DIRECTOR, 120), hint.monster.pos, hint.center, 1)
            label = self.debug_font.render(tr("hint_" + hint.kind), True, COLOR_DEBUG_DIRECTOR)
            layer.blit(label, (hint.center.x - label.get_width() / 2, hint.center.y - r - 18))
        surface.blit(layer, (0, 0))

    def _draw_debug_text(self, surface, session) -> None:
        p = session.player
        lines = [
            f"pos ({p.pos.x:.0f}, {p.pos.y:.0f})  tile ({int(p.pos.x // TILE_SIZE)}, {int(p.pos.y // TILE_SIZE)})",
            f"{tr('debug_sounds')}: {len(session.sounds.events)}   {tr('debug_monsters')}: {len(session.monsters)}",
            f"{tr('debug_memory')}: {len(getattr(session, 'memory_heat', {}))} / {len(getattr(session, 'new_heat', {}))}",
        ]
        for i, line in enumerate(lines):
            surface.blit(self.debug_font.render(line, True, (200, 200, 220)), (16, 60 + i * 18))

        director = getattr(session, "director", None)
        if director is None:
            return
        y = 60 + len(lines) * 18 + 8
        phase = tr("dir_" + director.phase.value)
        text = (f"{tr('dir_title')}: {phase}   {tr('dir_calm')} {director.calm_time:4.1f}"
                f" / {director.calm_before_nudge:.0f}s")
        surface.blit(self.debug_font.render(text, True, COLOR_DEBUG_DIRECTOR), (16, y))
        # Лента за напнатоста
        bar = pygame.Rect(16, y + 20, 180, 6)
        pygame.draw.rect(surface, (50, 40, 90), bar, border_radius=3)
        fill = bar.copy()
        fill.width = int(bar.width * director.tension)
        color = theme.lerp_color(COLOR_DEBUG_DIRECTOR, COLOR_MONSTER, director.tension)
        pygame.draw.rect(surface, color, fill, border_radius=3)
        surface.blit(self.debug_font.render(f"{tr('dir_tension')} {director.tension:.2f}", True, color),
                     (bar.right + 10, y + 14))
