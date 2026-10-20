"""ЕХО: стартна точка.

main.py сега е „диригент“: го отвора прозорецот, го води главниот циклус
и менува ЕКРАНИ (сцени). Секоја сцена има три функции:
    handle_event(event)   → влез
    update(dt)            → логика
    draw(surface)         → цртање

Тек на екрани:
    Избор на јазик → Главно мени → Игра ⇄ Пауза → Крај на ниво
                          ↘ Упатство   ↘ Јазик

Слоеви на проектот:
    ui/, render/, audio/   presentation (што се гледа и слуша)
    game/, ai/             логика и вештачка интелигенција
    data/                  трајни податоци (SQLite меморија на чудовиштата)
"""

from pathlib import Path

import pygame

from audio.audio_manager import AudioManager
from data.memory import open_memory
from settings import FPS, LEVELS, MAX_DT, MEMORY_DB, SCREEN_HEIGHT, SCREEN_WIDTH
from ui import i18n
from ui.scenes.language import LanguageScene

BASE_DIR = Path(__file__).resolve().parent
FADE_TIME = 0.35


class App:
    def __init__(self):
        pygame.init()
        self.size = (SCREEN_WIDTH, SCREEN_HEIGHT)
        self.base_dir = BASE_DIR
        self.screen = pygame.display.set_mode(self.size)
        self.clock = pygame.time.Clock()
        self.running = True

        settings = i18n.load_settings()
        suggested, _ = i18n.initial_language()
        i18n.set_language(suggested)
        pygame.display.set_caption(i18n.tr("title"))

        self.audio = AudioManager()   # ги генерира звуците: трае околу секунда
        if settings.get("muted") and self.audio.enabled:
            self.audio.toggle_mute()

        # SQLite меморија на чудовиштата (data/memory.py). None = исклучена.
        self.memory = open_memory(BASE_DIR / MEMORY_DB)

        self.unlocked = max(1, min(len(LEVELS), int(settings.get("unlocked", 1))))
        self.level_index = self.unlocked - 1

        self.scene = LanguageScene(self)
        self.fade = 1.0                       # 1 = целосно затемнето, 0 = проѕирно
        self.fade_surface = pygame.Surface(self.size)
        self.fade_surface.fill((8, 6, 20))

    # ================= Услуги за сцените =================

    def go(self, scene, fade: bool = True) -> None:
        """Премин на друг екран, со кратко затемнување."""
        self.scene = scene
        if fade:
            self.fade = 1.0

    def quit(self) -> None:
        self.running = False

    def set_language(self, code: str) -> None:
        i18n.set_language(code)
        pygame.display.set_caption(i18n.tr("title"))

    def toggle_sound(self) -> None:
        self.audio.toggle_mute()
        i18n.save_settings({"muted": self.audio.muted})

    def unlock(self, next_index: int) -> None:
        """По победа се отклучува следното ниво (се памети меѓу стартувања)."""
        new = min(len(LEVELS), next_index + 1)
        if new > self.unlocked:
            self.unlocked = new
            i18n.save_settings({"unlocked": new})
        self.level_index = min(self.unlocked - 1, next_index)

    # ================= Главна јамка =================

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, MAX_DT)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.scene.handle_event(event)

            self.scene.update(dt)
            self.scene.draw(self.screen)

            if self.fade > 0:
                self.fade = max(0.0, self.fade - dt / FADE_TIME)
                self.fade_surface.set_alpha(int(255 * self.fade))
                self.screen.blit(self.fade_surface, (0, 0))

            pygame.display.flip()

        on_exit = getattr(self.scene, "on_exit", None)
        if on_exit:
            on_exit()
        if self.memory:
            self.memory.close()
        pygame.quit()


if __name__ == "__main__":
    App().run()
