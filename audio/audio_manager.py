"""Аудио слој: ги „слуша“ настаните во играта и ги пушта соодветните звуци.

Ова е дел од Presentation слојот, исто како renderer-от: само ЧИТА од
состојбата на играта и ништо не менува.

Играчот слуша по истите правила како чудовиштата:
  - звукот го слушаш дури кога бранот ќе стигне до тебе,
  - потивок е со растојание и зад ѕидови,
  - доаѓа од лево или десно според тоа каде се случил (stereo panning).
"""

import random

import pygame

from audio.synth import SAMPLE_RATE, build_all
from settings import (
    AUDIO_HEARTBEAT_DISTANCE,
    AUDIO_MASTER_VOLUME,
    AUDIO_PAN_WIDTH,
    AUDIO_WALL_DAMPING,
)

LISTENER_ID = "player_ears"   # се додава во event.heard_by, исто како uid на чудовиште

# Базна гласност по вид на звук (0..1).
BASE_VOLUME = {
    "step": 0.35,
    "clap": 0.9,
    "stone": 0.7,
    "monster_step": 0.9,
    "shriek": 1.0,   # крикот: предупредување дека некое чудовиште те слушнало
    "monster_death": 1.0,
}


class AudioManager:
    def __init__(self):
        self.enabled = False
        self.muted = False
        try:
            # pygame.init() веќе го стартувал mixer-от со свои поставки (44100 Hz).
            # Нашите звуци се генерирани на 22050 Hz, па го рестартираме со точните
            # поставки, инаку сè би свирело двојно побрзо и повисоко.
            pygame.mixer.quit()
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(24)
            self.enabled = True
        except pygame.error as e:
            # Компјутер без аудио уред: играта мора да работи и без звук.
            print(f"[audio] исклучено: {e}")
            return

        self.rng = random.Random()
        self.sounds = {name: [pygame.mixer.Sound(buffer=b) for b in variants]
                       for name, variants in build_all().items()}

        self.ambient_channel = self.sounds["ambient"][0].play(loops=-1)
        self.heartbeat_timer = 0.0
        self.prev_game_over = False
        self._apply_master()

    # ================= Јавни функции =================

    def toggle_mute(self) -> None:
        self.muted = not self.muted
        self._apply_master()

    def ui(self, name: str) -> None:
        """Звуци за менијата: „move“ и „select“."""
        if self.enabled and not self.muted:
            self._play("ui_" + name, 0.45, 0)

    def play(self, name: str, volume: float, dx: float = 0.0) -> None:
        """Пушта звук директно (за демо во упатството). dx: позиција лево/десно во пиксели."""
        if self.enabled and not self.muted:
            self._play(name, volume, dx)

    def reset(self) -> None:
        """При рестарт на нивото."""
        self.prev_game_over = False

    def update(self, game, dt: float) -> None:
        if not self.enabled or self.muted:
            return
        listener = game.player.pos

        self._world_sounds(game, listener)
        self._ambient_tension(game)
        self._heartbeat(game, listener, dt)
        self._game_over(game)

    # ================= Звуци од светот =================

    def _world_sounds(self, game, listener: pygame.Vector2) -> None:
        for event in game.sounds.events:
            if LISTENER_ID in event.heard_by:
                continue
            distance = listener.distance_to(event.pos)

            # Сопствените звуци ги слушаш веднаш; туѓите кога бранот ќе стигне.
            own = event.source == "player"
            if not own and event.wave_radius < distance:
                if event.wave_radius >= event.loudness * 1.5:
                    event.heard_by.add(LISTENER_ID)
                continue
            event.heard_by.add(LISTENER_ID)

            volume = BASE_VOLUME.get(event.kind, 0.5)
            if not own:
                # Играчот има подобар слух од гласноста на бранот: ги слуша и звуците
                # малку надвор од видливиот бран (×1.5), за да има време да реагира.
                volume *= max(0.0, 1 - distance / (event.loudness * 1.5))
                walls = game.level.count_walls_between(event.pos, listener)
                volume *= AUDIO_WALL_DAMPING ** walls
            elif event.kind == "step" and game.player.is_sneaking:
                volume *= 0.4

            if volume > 0.02:
                self._play(event.kind, volume, event.pos.x - listener.x)

    def _ambient_tension(self, game) -> None:
        """Амбиентот на пештерата е погласен кога Директорот мери поголема напнатост."""
        director = getattr(game, "director", None)
        if director is None or not self.ambient_channel:
            return
        self.ambient_channel.set_volume((0.25 + 0.35 * director.tension) * AUDIO_MASTER_VOLUME)

    def _heartbeat(self, game, listener: pygame.Vector2, dt: float) -> None:
        """Срцето чука побрзо и погласно колку е поблиску најблиското чудовиште."""
        if game.game_over or not game.monsters:
            return
        nearest = min(listener.distance_to(m.pos) for m in game.monsters)
        if nearest > AUDIO_HEARTBEAT_DISTANCE:
            self.heartbeat_timer = 0.0
            return

        closeness = 1 - nearest / AUDIO_HEARTBEAT_DISTANCE         # 0 далеку … 1 до тебе
        interval = 1.1 - 0.7 * closeness                           # 1.1 s → 0.4 s
        self.heartbeat_timer -= dt
        if self.heartbeat_timer <= 0:
            self.heartbeat_timer = interval
            self._play("heartbeat", 0.25 + 0.65 * closeness, 0)

    def _game_over(self, game) -> None:
        if game.game_over and not self.prev_game_over:
            self._play("win" if game.won else "lose", 0.9, 0)
        self.prev_game_over = game.game_over

    # ================= Помошно =================

    def _play(self, name: str, volume: float, dx: float) -> None:
        """Пушта звук со гласност и позиција лево/десно.

        dx < 0: звукот е лево од играчот → посилен во левиот звучник.
        """
        variants = self.sounds.get(name)
        if not variants:
            return
        channel = self.rng.choice(variants).play()
        if channel is None:
            return   # сите канали се зафатени; прескокни
        pan = max(-1.0, min(1.0, dx / AUDIO_PAN_WIDTH))
        left = volume * min(1.0, 1 - pan)
        right = volume * min(1.0, 1 + pan)
        channel.set_volume(left * AUDIO_MASTER_VOLUME, right * AUDIO_MASTER_VOLUME)

    def _apply_master(self) -> None:
        if self.enabled and self.ambient_channel:
            self.ambient_channel.set_volume(0 if self.muted else 0.35 * AUDIO_MASTER_VOLUME)
