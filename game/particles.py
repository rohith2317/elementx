"""
game/particles.py
A lightweight, reusable particle system used for every elemental
effect in the game (fire, lightning, wind, energy, explosions,
shield, hit sparks) plus screen shake / flash helpers.

Kept dependency-light (pure Pygame + random/math) and capped in
particle count for performance.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple

import pygame

MAX_PARTICLES = 400


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: Tuple[int, int, int]
    radius: float
    gravity: float = 0.0
    fade: bool = True
    shrink: bool = True

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vy += self.gravity * dt * 60
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        t = max(self.life / self.max_life, 0.0)
        radius = max(1, self.radius * (t if self.shrink else 1.0))
        alpha = int(255 * t) if self.fade else 255
        alpha = max(0, min(255, alpha))
        size = int(radius * 2) + 2
        particle_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(
            particle_surf, (*self.color, alpha), (size // 2, size // 2), radius
        )
        surface.blit(particle_surf, (self.x - size / 2, self.y - size / 2))


class ParticleSystem:
    """Holds and updates all active particles; provides emit presets."""

    def __init__(self) -> None:
        self.particles: List[Particle] = []
        self.screen_shake_timer: float = 0.0
        self.screen_shake_magnitude: float = 0.0
        self.flash_timer: float = 0.0
        self.flash_color: Tuple[int, int, int] = (255, 255, 255)
        self.flash_alpha: int = 0

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.update(dt)]
        if self.screen_shake_timer > 0:
            self.screen_shake_timer = max(0.0, self.screen_shake_timer - dt)
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

    def draw(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            p.draw(surface)
        if self.flash_timer > 0:
            alpha = int(self.flash_alpha * (self.flash_timer / self.flash_duration))
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((*self.flash_color, max(0, min(255, alpha))))
            surface.blit(overlay, (0, 0))

    def get_shake_offset(self) -> Tuple[int, int]:
        if self.screen_shake_timer <= 0:
            return (0, 0)
        mag = self.screen_shake_magnitude
        return (random.randint(-int(mag), int(mag)), random.randint(-int(mag), int(mag)))

    # ------------------------------------------------------------------
    # Global FX
    # ------------------------------------------------------------------
    def shake(self, duration: float, magnitude: float) -> None:
        self.screen_shake_timer = duration
        self.screen_shake_magnitude = magnitude

    def flash(self, color: Tuple[int, int, int] = (255, 255, 255), duration: float = 0.15, alpha: int = 140) -> None:
        self.flash_timer = duration
        self.flash_duration = duration
        self.flash_color = color
        self.flash_alpha = alpha

    # ------------------------------------------------------------------
    # Emit presets
    # ------------------------------------------------------------------
    def _add(self, particle: Particle) -> None:
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(particle)

    def emit_fire(self, x: float, y: float, count: int = 14) -> None:
        for _ in range(count):
            angle = random.uniform(-0.6, 0.6) - math.pi / 2
            speed = random.uniform(2, 5)
            self._add(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                life=random.uniform(0.3, 0.6), max_life=0.6,
                color=random.choice([(255, 120, 30), (255, 180, 60), (255, 60, 20)]),
                radius=random.uniform(3, 7), gravity=-0.05,
            ))

    def emit_lightning(self, x: float, y: float, count: int = 10) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(4, 9)
            self._add(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                life=random.uniform(0.15, 0.3), max_life=0.3,
                color=random.choice([(255, 240, 90), (255, 255, 200)]),
                radius=random.uniform(2, 4), shrink=False,
            ))

    def emit_wind(self, x: float, y: float, count: int = 18) -> None:
        for i in range(count):
            angle = (i / count) * math.pi * 2
            speed = random.uniform(3, 6)
            self._add(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                life=random.uniform(0.4, 0.7), max_life=0.7,
                color=(150, 255, 210), radius=random.uniform(2, 5),
            ))

    def emit_energy(self, x: float, y: float, count: int = 14) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 4)
            self._add(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                life=random.uniform(0.3, 0.6), max_life=0.6,
                color=random.choice([(170, 90, 255), (120, 60, 220)]),
                radius=random.uniform(2, 5),
            ))

    def emit_explosion(self, x: float, y: float, count: int = 30, color=(255, 160, 60)) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 10)
            self._add(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                life=random.uniform(0.3, 0.8), max_life=0.8,
                color=color, radius=random.uniform(3, 8), gravity=0.05,
            ))

    def emit_shield(self, x: float, y: float, radius: float = 60, count: int = 20) -> None:
        for i in range(count):
            angle = (i / count) * math.pi * 2
            px = x + math.cos(angle) * radius
            py = y + math.sin(angle) * radius
            self._add(Particle(
                px, py, math.cos(angle) * 0.5, math.sin(angle) * 0.5,
                life=0.25, max_life=0.25, color=(90, 200, 255),
                radius=3, shrink=False,
            ))

    def emit_hit(self, x: float, y: float, count: int = 10) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 6)
            self._add(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                life=random.uniform(0.2, 0.4), max_life=0.4,
                color=(255, 255, 255), radius=random.uniform(2, 4),
            ))

    def emit_ultimate(self, x: float, y: float, count: int = 60) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(4, 14)
            self._add(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                life=random.uniform(0.5, 1.0), max_life=1.0,
                color=random.choice([(255, 80, 200), (170, 90, 255), (255, 255, 255)]),
                radius=random.uniform(3, 9),
            ))
        self.shake(0.4, 14)
        self.flash((255, 80, 200), 0.2, 120)

    def emit_heal(self, x: float, y: float, count: int = 12) -> None:
        for _ in range(count):
            angle = random.uniform(-0.4, 0.4) - math.pi / 2
            speed = random.uniform(1.5, 3.5)
            self._add(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                life=random.uniform(0.5, 0.9), max_life=0.9,
                color=(90, 255, 140), radius=random.uniform(2, 5), gravity=-0.03,
            ))
