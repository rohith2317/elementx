"""
game/enemy.py
Enemy entity + AI. Supports the four enemy archetypes declared in
config.ENEMY_STATS (Training Bot, Shadow Beast, Element Guardian,
Final Boss). The boss additionally supports phases and dodging.
All visuals are drawn with Pygame primitives — original designs.
"""
from __future__ import annotations

import math
import random
import time
from typing import Optional

import pygame

from config import ENEMY_STATS, SCREEN_WIDTH
from utils.helpers import clamp


class Enemy:
    ANIM_IDLE = "idle"
    ANIM_ATTACK = "attack"
    ANIM_HIT = "hit"
    ANIM_DEATH = "death"
    ANIM_DODGE = "dodge"

    def __init__(self, enemy_type: str, x: float, y: float, difficulty_scale: float = 1.0) -> None:
        self.enemy_type = enemy_type
        stats = ENEMY_STATS[enemy_type]
        self.name = stats["name"]
        self.max_hp = int(stats["hp"] * difficulty_scale)
        self.hp = self.max_hp
        self.attack_damage = int(stats["attack"] * difficulty_scale)
        self.attack_cooldown = stats["attack_cd"]
        self.speed = stats["speed"]
        self.color = stats["color"]
        self.ranged = stats.get("ranged", False)
        self.can_dodge = stats.get("can_dodge", False)
        self.total_phases = stats.get("phases", 1)
        self.phase = 1

        self.x = x
        self.y = y
        self.width, self.height = 100, 150
        self.alive = True
        self.anim_state = Enemy.ANIM_IDLE
        self.anim_timer = 0.0
        self._idle_phase = random.uniform(0, 6.28)

        self._last_attack_time = time.time()
        self.pending_attack = False  # set True for one frame when attack fires
        self.is_dodging = False

    # ------------------------------------------------------------------
    def update(self, dt: float, player_x: float, player_y: float) -> None:
        self._idle_phase += dt * 2.0
        self.pending_attack = False

        if self.anim_timer > 0:
            self.anim_timer = max(0.0, self.anim_timer - dt)
            if self.anim_timer == 0 and self.anim_state not in (Enemy.ANIM_DEATH,):
                self.anim_state = Enemy.ANIM_IDLE

        if not self.alive:
            return

        # Update boss phase based on remaining HP
        if self.total_phases > 1:
            hp_ratio = self.hp / self.max_hp
            new_phase = self.total_phases - int(hp_ratio * self.total_phases)
            self.phase = clamp(max(1, new_phase), 1, self.total_phases)

        # Move toward a comfortable engagement distance
        target_x = player_x + 260
        target_x = clamp(target_x, SCREEN_WIDTH * 0.55 + 40, SCREEN_WIDTH - 100)
        if abs(self.x - target_x) > 4:
            direction = 1 if target_x > self.x else -1
            self.x += direction * self.speed * (1 + 0.15 * (self.phase - 1))

        # Attack on cooldown
        now = time.time()
        cd = self.attack_cooldown / (1 + 0.2 * (self.phase - 1))
        if now - self._last_attack_time >= cd and self.anim_state != Enemy.ANIM_DEATH:
            self._last_attack_time = now
            self.pending_attack = True
            self.trigger_animation(Enemy.ANIM_ATTACK, 0.3)

    def trigger_animation(self, state: str, duration: float) -> None:
        if self.anim_state == Enemy.ANIM_DEATH:
            return
        self.anim_state = state
        self.anim_timer = duration

    def take_damage(self, amount: int) -> bool:
        """Returns True if the hit actually landed (not dodged)."""
        if not self.alive:
            return False
        if self.can_dodge and random.random() < 0.15 + 0.05 * (self.phase - 1):
            self.is_dodging = True
            self.trigger_animation(Enemy.ANIM_DODGE, 0.2)
            return False
        self.hp = clamp(self.hp - amount, 0, self.max_hp)
        self.trigger_animation(Enemy.ANIM_HIT, 0.15)
        if self.hp <= 0:
            self.alive = False
            self.trigger_animation(Enemy.ANIM_DEATH, 999)
        return True

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        bob = math.sin(self._idle_phase) * 3
        cx, cy = int(self.x), int(self.y + bob)

        if self.anim_state == Enemy.ANIM_DEATH:
            alpha = clamp(int(255 * (self.anim_timer / 0.6)), 0, 255) if self.anim_timer else 0
            self._draw_body(surface, cx, cy, alpha=180)
            return

        flash = self.anim_state == Enemy.ANIM_HIT
        self._draw_body(surface, cx, cy, flash=flash)

    def _draw_body(self, surface: pygame.Surface, cx: int, cy: int, alpha: int = 255, flash: bool = False) -> None:
        base_color = self.color if not flash else (255, 255, 255)

        # Silhouette body — original monster/robot design per type
        if self.enemy_type == "TRAINING_BOT":
            pygame.draw.rect(surface, base_color, (cx - 30, cy - 40, 60, 80), border_radius=10)
            pygame.draw.rect(surface, (90, 90, 100), (cx - 20, cy - 60, 40, 26), border_radius=6)
            pygame.draw.circle(surface, (255, 60, 60), (cx, cy - 48), 5)
        elif self.enemy_type == "SHADOW_BEAST":
            pygame.draw.ellipse(surface, base_color, (cx - 36, cy - 50, 72, 100))
            for i in range(4):
                ang = -0.6 + i * 0.4
                ex = cx + math.cos(ang) * 40
                ey = cy - 20 + math.sin(ang) * 40
                pygame.draw.line(surface, (30, 10, 40), (cx, cy - 10), (ex, ey), 4)
            pygame.draw.circle(surface, (255, 220, 60), (cx - 10, cy - 20), 4)
            pygame.draw.circle(surface, (255, 220, 60), (cx + 10, cy - 20), 4)
        elif self.enemy_type == "ELEMENT_GUARDIAN":
            pygame.draw.polygon(surface, base_color, [
                (cx, cy - 70), (cx + 40, cy + 20), (cx + 20, cy + 60),
                (cx - 20, cy + 60), (cx - 40, cy + 20)
            ])
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy - 20), 10, width=2)
        else:  # FINAL_BOSS
            pulse = 1.0 + 0.05 * math.sin(self._idle_phase * 2)
            w, h = int(90 * pulse), int(130 * pulse)
            pygame.draw.ellipse(surface, base_color, (cx - w // 2, cy - h // 2, w, h))
            for i in range(6):
                ang = (i / 6) * math.pi * 2 + self._idle_phase
                ex = cx + math.cos(ang) * 60
                ey = cy + math.sin(ang) * 60
                pygame.draw.line(surface, (255, 40, 80), (cx, cy), (ex, ey), 3)
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 14, width=2)
            phase_color = [(255, 220, 60), (255, 140, 40), (255, 40, 40)][min(self.phase - 1, 2)]
            pygame.draw.circle(surface, phase_color, (cx, cy), 8)

    def get_projectile_origin(self):
        return (self.x - 30, self.y - 10)

    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)
