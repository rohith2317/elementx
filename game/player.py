"""
game/player.py
Original stylized anime-inspired player character, rendered entirely
with Pygame primitives/gradients (no external image assets required).
Handles HP/energy, animation state, and movement.
"""
from __future__ import annotations

import math
import time
from typing import Tuple

import pygame

from config import (
    PLAYER_MAX_HP, PLAYER_MAX_ENERGY, PLAYER_ENERGY_REGEN_PER_SEC,
    PLAYER_MOVE_SPEED, PLAYER_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT,
)
from utils.helpers import clamp


class Player:
    ANIM_IDLE = "idle"
    ANIM_ATTACK = "attack"
    ANIM_SHIELD = "shield"
    ANIM_HIT = "hit"
    ANIM_DEFEAT = "defeat"

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.width, self.height = PLAYER_SIZE
        self.hp = PLAYER_MAX_HP
        self.max_hp = PLAYER_MAX_HP
        self.energy = PLAYER_MAX_ENERGY
        self.max_energy = PLAYER_MAX_ENERGY

        self.anim_state = Player.ANIM_IDLE
        self.anim_timer = 0.0
        self.anim_duration = 0.25
        self.facing = 1  # 1 = right, -1 = left
        self.is_shielding = False
        self.alive = True
        self._idle_phase = 0.0

        # Progression system
        self.level = 1
        self.xp = 0
        self.xp_to_next_level = 100
        self.upgrade_counts = {}  # tracks how many times each upgrade has been purchased

        # Stat multipliers (1.0 = base stats)
        self.stat_multipliers = {
            "max_health": 1.0,
            "attack_damage": 1.0,
            "movement_speed": 1.0,
            "energy_regen": 1.0,
            "defense": 1.0,
        }

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self._idle_phase += dt * 2.5
        if self.anim_timer > 0:
            self.anim_timer = max(0.0, self.anim_timer - dt)
            if self.anim_timer == 0 and self.anim_state != Player.ANIM_DEFEAT:
                self.anim_state = Player.ANIM_SHIELD if self.is_shielding else Player.ANIM_IDLE

        if self.energy < self.max_energy:
            self.energy = clamp(self.energy + PLAYER_ENERGY_REGEN_PER_SEC * dt, 0, self.max_energy)

        if self.hp <= 0 and self.alive:
            self.alive = False
            self.anim_state = Player.ANIM_DEFEAT

    def move(self, dx: float) -> None:
        if self.anim_state == Player.ANIM_DEFEAT:
            return
        self.x = clamp(self.x + dx, 60, SCREEN_WIDTH * 0.55)
        if dx != 0:
            self.facing = 1 if dx > 0 else -1

    def set_position_from_ratio(self, ratio: float) -> None:
        """Map a normalized (0..1) hand-x position to player x within its
        movement bounds. ratio near 0 = left, near 1 = right (screen space,
        already mirrored by the vision module)."""
        min_x, max_x = 60, SCREEN_WIDTH * 0.55
        target = min_x + ratio * (max_x - min_x)
        # Smooth toward target rather than snapping
        self.x += (target - self.x) * 0.25

    def trigger_animation(self, state: str, duration: float = 0.25) -> None:
        if self.anim_state == Player.ANIM_DEFEAT:
            return
        self.anim_state = state
        self.anim_timer = duration
        self.anim_duration = duration

    def start_shield(self) -> None:
        self.is_shielding = True
        self.trigger_animation(Player.ANIM_SHIELD, 999)

    def stop_shield(self) -> None:
        self.is_shielding = False
        if self.anim_state == Player.ANIM_SHIELD:
            self.trigger_animation(Player.ANIM_IDLE, 0.1)

    def take_damage(self, amount: int) -> int:
        if self.is_shielding:
            amount = max(0, int(amount * 0.15))
        self.hp = clamp(self.hp - amount, 0, self.max_hp)
        if amount > 0:
            self.trigger_animation(Player.ANIM_HIT, 0.2)
        return amount

    def heal(self, amount: int) -> None:
        self.hp = clamp(self.hp + amount, 0, self.max_hp)

    def spend_energy(self, amount: int) -> bool:
        if self.energy >= amount:
            self.energy -= amount
            return True
        return False

    # ------------------------------------------------------------------
    # Progression / Upgrades
    # ------------------------------------------------------------------
    def add_xp(self, amount: int) -> bool:
        """Add XP and return True if player leveled up."""
        self.xp += amount
        if self.xp >= self.xp_to_next_level:
            self.level_up()
            return True
        return False

    def level_up(self) -> None:
        """Handle level up."""
        self.xp = max(0, self.xp - self.xp_to_next_level)
        self.level += 1
        self.xp_to_next_level = int(100 * (1.1 ** (self.level - 1)))

    def apply_upgrade(self, upgrade_key: str) -> None:
        """Apply an upgrade to the player."""
        self.upgrade_counts[upgrade_key] = self.upgrade_counts.get(upgrade_key, 0) + 1

        # Apply the upgrade's effect to the stat multiplier
        if upgrade_key == "max_health":
            # Increase max health and restore some
            new_max = int(PLAYER_MAX_HP * self.stat_multipliers["max_health"] * 1.15)
            health_gain = new_max - self.max_hp
            self.max_hp = new_max
            self.hp = min(self.hp + health_gain, self.max_hp)
            self.stat_multipliers["max_health"] *= 1.15

        elif upgrade_key == "attack_damage":
            self.stat_multipliers["attack_damage"] *= 1.12

        elif upgrade_key == "movement_speed":
            self.stat_multipliers["movement_speed"] *= 1.1

        elif upgrade_key == "energy_regen":
            self.stat_multipliers["energy_regen"] *= 1.25

        elif upgrade_key == "defense":
            self.stat_multipliers["defense"] *= 1.08

    def get_stat_value(self, stat_key: str) -> float:
        """Get a stat value with upgrade multipliers applied."""
        if stat_key == "max_health":
            return int(PLAYER_MAX_HP * self.stat_multipliers["max_health"])
        elif stat_key == "attack_damage":
            return self.stat_multipliers["attack_damage"]
        elif stat_key == "movement_speed":
            return PLAYER_MOVE_SPEED * self.stat_multipliers["movement_speed"]
        elif stat_key == "energy_regen":
            return PLAYER_ENERGY_REGEN_PER_SEC * self.stat_multipliers["energy_regen"]
        elif stat_key == "defense":
            return self.stat_multipliers["defense"]
        return 1.0

    # ------------------------------------------------------------------
    # Rendering — original stylized character, no external art needed
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        bob = math.sin(self._idle_phase) * 4 if self.anim_state == Player.ANIM_IDLE else 0
        cx, cy = int(self.x), int(self.y + bob)

        body_color = (70, 130, 220)
        accent_color = (255, 210, 80)
        cloak_color = (40, 60, 110)

        if self.anim_state == Player.ANIM_DEFEAT:
            self._draw_defeated(surface, cx, cy)
            return

        # Cloak / cape
        cape_points = [
            (cx - 20 * self.facing, cy - 40),
            (cx - 34 * self.facing, cy + 50),
            (cx - 6 * self.facing, cy + 55),
        ]
        pygame.draw.polygon(surface, cloak_color, cape_points)

        # Legs
        pygame.draw.rect(surface, (30, 34, 48), (cx - 16, cy + 30, 12, 34), border_radius=4)
        pygame.draw.rect(surface, (30, 34, 48), (cx + 4, cy + 30, 12, 34), border_radius=4)

        # Torso
        torso_rect = pygame.Rect(cx - 20, cy - 20, 40, 55)
        pygame.draw.rect(surface, body_color, torso_rect, border_radius=10)
        pygame.draw.rect(surface, accent_color, (cx - 6, cy - 20, 12, 55), border_radius=4)

        # Arms — pose changes with animation state
        arm_color = body_color
        if self.anim_state == Player.ANIM_ATTACK:
            fx = cx + 46 * self.facing
            pygame.draw.line(surface, arm_color, (cx + 14 * self.facing, cy), (fx, cy - 6), 10)
            pygame.draw.circle(surface, accent_color, (fx, cy - 6), 8)
        elif self.anim_state == Player.ANIM_SHIELD:
            pygame.draw.circle(surface, (90, 200, 255), (cx, cy), 60, width=4)
            pygame.draw.line(surface, arm_color, (cx - 14, cy), (cx - 24, cy - 10), 10)
            pygame.draw.line(surface, arm_color, (cx + 14, cy), (cx + 24, cy - 10), 10)
        elif self.anim_state == Player.ANIM_HIT:
            pygame.draw.line(surface, arm_color, (cx - 14, cy), (cx - 22, cy + 8), 10)
            pygame.draw.line(surface, arm_color, (cx + 14, cy), (cx + 22, cy + 8), 10)
        else:
            sway = math.sin(self._idle_phase) * 4
            pygame.draw.line(surface, arm_color, (cx - 14, cy), (cx - 22, cy + 14 + sway), 10)
            pygame.draw.line(surface, arm_color, (cx + 14, cy), (cx + 22, cy + 14 - sway), 10)

        # Head
        pygame.draw.circle(surface, (250, 220, 190), (cx, cy - 34), 16)
        # Hair (spiky, original style)
        hair_color = (240, 240, 245)
        for i in range(-2, 3):
            tip = (cx + i * 6, cy - 34 - 20 - abs(i) * 2)
            pygame.draw.polygon(surface, hair_color, [
                (cx + i * 6 - 4, cy - 40), (cx + i * 6 + 4, cy - 40), tip
            ])
        # Headband (original design, not Naruto's)
        pygame.draw.rect(surface, (30, 30, 40), (cx - 17, cy - 38, 34, 6))
        pygame.draw.circle(surface, accent_color, (cx, cy - 35), 4)

        if self.anim_state == Player.ANIM_HIT:
            flash = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            flash.fill((255, 60, 60, 60))
            surface.blit(flash, (cx - self.width // 2, cy - self.height // 2))

    def _draw_defeated(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        pygame.draw.ellipse(surface, (60, 60, 70), (cx - 30, cy + 40, 60, 16))
        pygame.draw.rect(surface, (70, 130, 220, 120), (cx - 24, cy + 10, 48, 20), border_radius=8)
        pygame.draw.circle(surface, (250, 220, 190), (cx, cy + 6), 14)
