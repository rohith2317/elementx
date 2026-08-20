"""
game/states.py
Defines the finite set of game states and a small manager to
transition between them cleanly.
"""
from __future__ import annotations

from enum import Enum, auto


class GameState(Enum):
    MAIN_MENU = auto()
    HOW_TO_PLAY = auto()
    SETTINGS = auto()
    COUNTDOWN = auto()
    PLAYING = auto()
    PAUSED = auto()
    ROUND_COMPLETE = auto()
    UPGRADE = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class StateManager:
    """Tiny wrapper around the current GameState with change tracking."""

    def __init__(self, initial: GameState = GameState.MAIN_MENU) -> None:
        self._state = initial
        self._previous: GameState | None = None

    @property
    def current(self) -> GameState:
        return self._state

    @property
    def previous(self) -> GameState | None:
        return self._previous

    def set(self, new_state: GameState) -> None:
        if new_state != self._state:
            self._previous = self._state
            self._state = new_state

    def is_(self, state: GameState) -> bool:
        return self._state == state
