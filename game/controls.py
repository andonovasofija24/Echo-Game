"""Контроли: физички копчиња → акции во играта.

ЗОШТО SCANCODE?
pygame (SDL2) има два начина да каже кое копче е притиснато:
  - event.key  = ЗНАКОТ што копчето го пишува. Зависи од јазикот на тастатурата!
                 На македонска тастатура копчето E пишува кирилско „е“, па
                 проверката `event.key == pygame.K_e` никогаш не е точна.
  - event.scancode = ФИЗИЧКАТА позиција на копчето, иста на секоја тастатура.
Затоа сите копчиња со букви (W A S D, E, R, M) ги читаме по scancode.
Копчињата без букви (стрелки, Space, Shift, Esc, F1) работат исто и по двата начина.

Шема на контроли:
  W A S D или стрелки   движење горе/доле/лево/десно
  Shift                 шуњање
  E                     камче во насоката во која е моментално свртен играчот
                        (играчот САМ постојано се врти, како сонар)
"""

import pygame

SC = pygame  # само за пократко пишување подолу

MOVE_UP = (SC.KSCAN_W, SC.KSCAN_UP)
MOVE_DOWN = (SC.KSCAN_S, SC.KSCAN_DOWN)
MOVE_LEFT = (SC.KSCAN_A, SC.KSCAN_LEFT)
MOVE_RIGHT = (SC.KSCAN_D, SC.KSCAN_RIGHT)
SNEAK = (SC.KSCAN_LSHIFT, SC.KSCAN_RSHIFT)

THROW = SC.KSCAN_E
RESTART = SC.KSCAN_R
MUTE = SC.KSCAN_M


def is_key(event, scancode: int) -> bool:
    """Дали KEYDOWN настанот е одредено ФИЗИЧКО копче (независно од јазикот на тастатурата)."""
    return event.type == pygame.KEYDOWN and getattr(event, "scancode", None) == scancode


class InputState:
    """Кои физички копчиња се моментално притиснати (според KEYDOWN/KEYUP настаните)."""

    def __init__(self):
        self.down: set[int] = set()

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            self.down.add(event.scancode)
        elif event.type == pygame.KEYUP:
            self.down.discard(event.scancode)
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.clear()   # ако прозорецот изгуби фокус, копчињата „не остануваат заглавени“

    def clear(self) -> None:
        self.down.clear()

    def any(self, codes) -> bool:
        return any(c in self.down for c in codes)

    def actions(self) -> "Actions":
        return Actions(
            move=pygame.Vector2(self.any(MOVE_RIGHT) - self.any(MOVE_LEFT),
                                self.any(MOVE_DOWN) - self.any(MOVE_UP)),
            sneak=self.any(SNEAK),
        )


class Actions:
    """Што сака играчот да направи во овој фрејм (логичко, не копчиња)."""

    def __init__(self, move=None, sneak: bool = False):
        self.move = move if move is not None else pygame.Vector2()
        self.sneak = sneak


NO_ACTIONS = Actions()
