"""
game/abilities.py
Defines Projectile objects spawned by player/enemy abilities, plus the
ComboTracker which watches recent gesture history for the named combo
sequences declared in config.GESTURE_COMBOS.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple

import pygame

from config import (
    ABILITY_STATS,
    GESTURE_COMBOS,
    COMBO_SEQUENCE_WINDOW,
    COMBO_WINDOW_SECONDS,
    COMBO_DAMAGE_BONUS_PER_STAGE,
    COMBO_DAMAGE_BONUS_CAP,
)


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: int
    color: Tuple[int, int, int]
    ability: str
    owner: str  # "player" or "enemy"
    radius: int = 12
    alive: bool = True
    trail: Optional[List[Tuple[float, float]]] = None

    def __post_init__(self) -> None:
        if self.trail is None:
            self.trail = []

    def update(self, dt: float, bounds_w: int) -> None:
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        if self.x < -50 or self.x > bounds_w + 50:
            self.alive = False

    def draw(self, surface: pygame.Surface) -> None:
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(255 * (i / max(len(self.trail), 1)) * 0.5)
            trail_surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                trail_surf, (*self.color, alpha), (self.radius, self.radius), self.radius * (i / max(len(self.trail), 1))
            )
            surface.blit(trail_surf, (tx - self.radius, ty - self.radius))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), self.radius, width=2)

    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)


def make_player_projectile(ability: str, x: float, y: float, direction: int = 1) -> Projectile:
    """Factory for a player-owned projectile using config.ABILITY_STATS."""
    stats = ABILITY_STATS[ability]
    return Projectile(
        x=x, y=y, vx=stats["speed"] * direction, vy=0,
        damage=stats["damage"], color=stats["color"], ability=ability, owner="player",
        radius=10 if ability == "BASIC_PUNCH" else 14 if ability != "ULTIMATE" else 22,
    )


def make_enemy_projectile(x: float, y: float, damage: int, speed: float, direction: int = -1,
                           color: Tuple[int, int, int] = (200, 60, 80)) -> Projectile:
    return Projectile(x=x, y=y, vx=speed * direction, vy=0, damage=damage, color=color,
                       ability="ENEMY_BOLT", owner="enemy", radius=12)


class ComboTracker:
    """
    Tracks a rolling window of recently-triggered gestures and detects
    named combo sequences (config.GESTURE_COMBOS). Also tracks a hit
    streak (COMBO xN) used for score/damage multipliers.
    """

    def __init__(self) -> None:
        self._sequence: Deque[Tuple[str, float]] = deque(maxlen=6)
        self.hit_streak: int = 0
        self.last_hit_time: float = 0.0

    def register_gesture(self, gesture: str) -> Optional[str]:
        """Call whenever a new gesture triggers an action. Returns a combo
        name if a known sequence was just completed, else None."""
        now = time.time()
        self._sequence.append((gesture, now))
        # Drop entries outside the sequence window
        while self._sequence and now - self._sequence[0][1] > COMBO_SEQUENCE_WINDOW:
            self._sequence.popleft()

        recent = tuple(g for g, _ in self._sequence)
        for combo_seq, combo_name in GESTURE_COMBOS.items():
            n = len(combo_seq)
            if len(recent) >= n and recent[-n:] == combo_seq:
                return combo_name
        return None

    def register_hit(self) -> int:
        """Call whenever the player lands a hit on the enemy. Returns the
        new streak count."""
        now = time.time()
        if now - self.last_hit_time > COMBO_WINDOW_SECONDS:
            self.hit_streak = 0
        self.hit_streak += 1
        self.last_hit_time = now
        return self.hit_streak

    def check_expired(self) -> None:
        if self.hit_streak > 0 and time.time() - self.last_hit_time > COMBO_WINDOW_SECONDS:
            self.hit_streak = 0

    def damage_multiplier(self) -> float:
        bonus = min(self.hit_streak * COMBO_DAMAGE_BONUS_PER_STAGE, COMBO_DAMAGE_BONUS_CAP)
        return 1.0 + bonus
