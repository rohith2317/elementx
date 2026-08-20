"""
game/collision.py
Simple, dependency-free collision helpers used by combat.py.
Kept separate so hit-testing logic is easy to unit test and reuse.
"""
from __future__ import annotations

from typing import Iterable, List

import pygame

from game.abilities import Projectile


def projectile_hits_rect(projectile: Projectile, rect: pygame.Rect) -> bool:
    return projectile.alive and projectile.rect().colliderect(rect)


def find_projectile_hits(projectiles: Iterable[Projectile], target_rect: pygame.Rect,
                          owner_filter: str) -> List[Projectile]:
    """Return all live projectiles owned by `owner_filter` that intersect target_rect."""
    return [p for p in projectiles if p.owner == owner_filter and projectile_hits_rect(p, target_rect)]


def melee_in_range(attacker_x: float, target_x: float, range_px: float = 140) -> bool:
    return abs(attacker_x - target_x) <= range_px
