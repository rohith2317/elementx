"""
game/level.py
Level progression: builds enemies for each stage, tracks difficulty
scaling, and reports completion/victory conditions.
"""
from __future__ import annotations

from typing import Optional

from config import LEVELS, SCREEN_WIDTH
from game.enemy import Enemy


class LevelManager:
    def __init__(self) -> None:
        self.index = 0  # 0-based into LEVELS

    @property
    def total_levels(self) -> int:
        return len(LEVELS)

    @property
    def current(self) -> dict:
        return LEVELS[self.index]

    @property
    def level_number(self) -> int:
        return self.current["id"]

    @property
    def level_name(self) -> str:
        return self.current["name"]

    @property
    def background_color(self):
        return self.current["bg"]

    def is_last_level(self) -> bool:
        return self.index >= len(LEVELS) - 1

    def spawn_enemy(self) -> Enemy:
        difficulty_scale = 1.0 + 0.12 * self.index
        enemy_type = self.current["enemy"]
        return Enemy(enemy_type, x=SCREEN_WIDTH - 220, y=470, difficulty_scale=difficulty_scale)

    def advance(self) -> bool:
        """Move to next level. Returns False if there is no next level."""
        if self.is_last_level():
            return False
        self.index += 1
        return True

    def reset(self) -> None:
        self.index = 0
