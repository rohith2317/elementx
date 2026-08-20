"""
utils/helpers.py
Small reusable helper functions shared across modules.
"""
from __future__ import annotations

import math
import random
from typing import Tuple

import pygame


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a value between min_value and max_value."""
    return max(min_value, min(max_value, value))


def lerp(a: float, b: float, t: float) -> float:
    """Linearly interpolate between a and b by factor t (0..1)."""
    return a + (b - a) * t


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def draw_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: Tuple[int, int, int],
    pos: Tuple[int, int],
    center: bool = False,
    shadow: bool = True,
) -> pygame.Rect:
    """Draw text with an optional drop shadow for readability."""
    if shadow:
        shadow_surf = font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_surf.get_rect()
        if center:
            shadow_rect.center = (pos[0] + 2, pos[1] + 2)
        else:
            shadow_rect.topleft = (pos[0] + 2, pos[1] + 2)
        surface.blit(shadow_surf, shadow_rect)

    text_surf = font.render(text, True, color)
    rect = text_surf.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(text_surf, rect)
    return rect


def draw_bar(
    surface: pygame.Surface,
    pos: Tuple[int, int],
    size: Tuple[int, int],
    ratio: float,
    fg_color: Tuple[int, int, int],
    bg_color: Tuple[int, int, int],
    border_radius: int = 6,
) -> None:
    """Draw a horizontal stat bar (HP/Energy) clamped to [0, 1] ratio."""
    ratio = clamp(ratio, 0.0, 1.0)
    x, y = pos
    w, h = size
    pygame.draw.rect(surface, bg_color, (x, y, w, h), border_radius=border_radius)
    if ratio > 0:
        pygame.draw.rect(
            surface, fg_color, (x, y, int(w * ratio), h), border_radius=border_radius
        )
    pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), width=2, border_radius=border_radius)


def random_offset(magnitude: float) -> Tuple[float, float]:
    """Return a random (dx, dy) offset within +/- magnitude, for shake/jitter FX."""
    return (random.uniform(-magnitude, magnitude), random.uniform(-magnitude, magnitude))


def ease_out_quad(t: float) -> float:
    """Simple easing function for smoother animations."""
    return 1 - (1 - t) * (1 - t)
