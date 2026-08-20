"""
game/round_manager.py
Manages round/wave progression with multiple enemies per round,
difficulty scaling, and XP/reward tracking.
"""
from __future__ import annotations

from typing import Optional

from config import ROUNDS, SCREEN_WIDTH
from game.enemy import Enemy


class RoundManager:
    """Manages round progression with sequential enemy spawning."""

    def __init__(self) -> None:
        self.round_index = 0  # 0-based into ROUNDS
        self.enemies_spawned_in_round = 0
        self.enemies_killed_in_round = 0
        self.round_start_time = 0.0

    @property
    def total_rounds(self) -> int:
        return len(ROUNDS)

    @property
    def current(self) -> dict:
        if self.round_index >= len(ROUNDS):
            return ROUNDS[-1]  # fallback to last round
        return ROUNDS[self.round_index]

    @property
    def round_number(self) -> int:
        return self.current["id"]

    @property
    def round_name(self) -> str:
        return self.current["name"]

    @property
    def background_color(self):
        return self.current["bg"]

    def is_final_round(self) -> bool:
        return self.round_index >= len(ROUNDS) - 1

    def is_round_complete(self) -> bool:
        """Returns True if all enemies for this round have been killed."""
        enemy_count = self.current["enemy_count"]
        return self.enemies_killed_in_round >= enemy_count

    def spawn_next_enemy(self) -> Optional[Enemy]:
        """Spawn the next enemy in the current round if available."""
        enemy_count = self.current["enemy_count"]
        if self.enemies_spawned_in_round >= enemy_count:
            return None  # No more enemies to spawn this round

        difficulty_scale = self.current["difficulty_multiplier"]
        enemy_type = self.current["enemy_type"]
        
        enemy = Enemy(
            enemy_type,
            x=SCREEN_WIDTH - 220,
            y=470,
            difficulty_scale=difficulty_scale,
        )
        
        self.enemies_spawned_in_round += 1
        return enemy

    def register_enemy_kill(self) -> None:
        """Call when an enemy is defeated."""
        self.enemies_killed_in_round += 1

    def advance_round(self) -> bool:
        """Move to the next round. Returns False if no next round exists."""
        if self.is_final_round():
            return False
        self.round_index += 1
        self._reset_round_state()
        return True

    def _reset_round_state(self) -> None:
        """Reset state for a new round."""
        self.enemies_spawned_in_round = 0
        self.enemies_killed_in_round = 0

    def reset(self) -> None:
        """Reset to the beginning."""
        self.round_index = 0
        self._reset_round_state()

    def get_reward_xp(self, is_round_complete: bool = False) -> int:
        """Get XP reward for defeating an enemy or completing a round."""
        from config import PLAYER_XP_PER_ENEMY, PLAYER_XP_PER_ROUND_BONUS
        
        if is_round_complete:
            return PLAYER_XP_PER_ROUND_BONUS
        return PLAYER_XP_PER_ENEMY
