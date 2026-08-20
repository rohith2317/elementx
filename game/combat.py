"""
game/combat.py
Resolves combat interactions each frame: spawns projectiles for
gesture-triggered abilities, advances/collides them, and applies
damage to player/enemy. Also owns the ComboTracker and score/combo
bookkeeping used by the HUD.
"""
from __future__ import annotations

import time
from typing import List, Optional

import pygame

from config import ABILITY_STATS, SCREEN_WIDTH, COMBO_SCORE_MULTIPLIER
from game.abilities import Projectile, make_player_projectile, make_enemy_projectile, ComboTracker
from game.collision import find_projectile_hits, melee_in_range
from game.enemy import Enemy
from game.particles import ParticleSystem
from game.player import Player


GESTURE_TO_ABILITY = {
    "FIST": "BASIC_PUNCH",
    "ONE_FINGER": "LIGHTNING",
    "TWO_FINGERS": "WIND",
    "THREE_FINGERS": "ENERGY_BLAST",
    "ULTIMATE": "ULTIMATE",
}

ABILITY_DISPLAY_NAMES = {
    "BASIC_PUNCH": "Energy Punch",
    "LIGHTNING": "Lightning Strike",
    "WIND": "Wind Slash",
    "ENERGY_BLAST": "Energy Blast",
    "FIRE": "Fire Wave",
    "ULTIMATE": "ELEMENTX OMEGA",
    "SHIELD": "Guardian Shield",
    "HEAL": "Restore",
}


class CombatSystem:
    def __init__(self, particles: ParticleSystem, sound_manager=None) -> None:
        self.particles = particles
        self.sound_manager = sound_manager
        self.projectiles: List[Projectile] = []
        self.combo = ComboTracker()
        self.score = 0
        self.last_ability_name = "—"

    # ------------------------------------------------------------------
    def trigger_player_ability(self, gesture: str, player: Player) -> Optional[str]:
        """Given a newly-triggered (debounced) gesture, attempt to fire the
        matching ability. Returns the ability key if it fired."""
        if gesture == "OPEN_PALM":
            # Shield costs a small trickle of energy per activation but is
            # always allowed to engage (it's a defensive last resort, so it
            # shouldn't be lockable out by empty energy the way attacks are).
            player.spend_energy(ABILITY_STATS["SHIELD"]["energy"])
            player.start_shield()
            self.particles.emit_shield(player.x, player.y)
            self._play("shield")
            return "SHIELD"

        if gesture == "THUMBS_UP":
            heal_amount = 12
            player.heal(heal_amount)
            self.particles.emit_heal(player.x, player.y - 40)
            self._play("heal")
            return "HEAL"

        ability = GESTURE_TO_ABILITY.get(gesture)
        if ability is None:
            return None

        cost = ABILITY_STATS[ability]["energy"]
        if not player.spend_energy(cost):
            return None  # not enough energy

        player.trigger_animation(Player.ANIM_ATTACK, 0.25)
        origin_x = player.x + 40 * player.facing
        origin_y = player.y - 10
        proj = make_player_projectile(ability, origin_x, origin_y, direction=player.facing)
        self.projectiles.append(proj)
        self.last_ability_name = ABILITY_DISPLAY_NAMES.get(ability, ability)

        if ability == "LIGHTNING":
            self.particles.emit_lightning(origin_x, origin_y)
            self._play("lightning")
        elif ability == "WIND":
            self.particles.emit_wind(origin_x, origin_y)
            self._play("wind")
        elif ability == "ENERGY_BLAST":
            self.particles.emit_energy(origin_x, origin_y)
            self._play("attack")
        elif ability == "ULTIMATE":
            self.particles.emit_ultimate(origin_x, origin_y)
            self._play("ultimate")
        else:
            self.particles.emit_energy(origin_x, origin_y, count=6)
            self._play("attack")

        return ability

    def stop_shield_if_active(self, gesture_active: bool, player: Player) -> None:
        if player.is_shielding and not gesture_active:
            player.stop_shield()

    def spawn_enemy_projectile(self, enemy: Enemy) -> None:
        ox, oy = enemy.get_projectile_origin()
        proj = make_enemy_projectile(ox, oy, enemy.attack_damage, speed=8 + enemy.phase, direction=-1,
                                      color=enemy.color)
        self.projectiles.append(proj)

    # ------------------------------------------------------------------
    def update(self, dt: float, player: Player, enemy: Optional[Enemy]) -> None:
        for p in self.projectiles:
            p.update(dt, SCREEN_WIDTH)
        self.projectiles = [p for p in self.projectiles if p.alive]

        if enemy and enemy.alive:
            hits = find_projectile_hits(self.projectiles, enemy.rect(), owner_filter="player")
            for hit in hits:
                mult = self.combo.damage_multiplier()
                dmg = int(hit.damage * mult)
                landed = enemy.take_damage(dmg)
                hit.alive = False
                self.particles.emit_hit(hit.x, hit.y)
                if landed:
                    streak = self.combo.register_hit()
                    self.score += dmg * COMBO_SCORE_MULTIPLIER
                    self._play("hit")
                    if hit.ability == "ULTIMATE":
                        self.particles.shake(0.3, 10)

        if enemy:
            hits = find_projectile_hits(self.projectiles, self._player_rect(player), owner_filter="enemy")
            for hit in hits:
                dealt = player.take_damage(hit.damage)
                hit.alive = False
                if dealt > 0:
                    self.particles.emit_hit(player.x, player.y)
                    self.particles.shake(0.15, 6)
                    self._play("hit")

        self.combo.check_expired()

    @staticmethod
    def _player_rect(player: Player) -> pygame.Rect:
        return pygame.Rect(player.x - player.width // 2, player.y - player.height // 2,
                            player.width, player.height)

    def draw(self, surface: pygame.Surface) -> None:
        for p in self.projectiles:
            p.draw(surface)

    def _play(self, key: str) -> None:
        if self.sound_manager is not None:
            self.sound_manager.play(key)

    def reset_for_level(self) -> None:
        self.projectiles.clear()
        self.combo.hit_streak = 0
