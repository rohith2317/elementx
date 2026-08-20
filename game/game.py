"""
game/game.py
The GameController: owns the pygame window, the GestureDetector,
all game entities/systems, and the main state machine. main.py simply
constructs a GameController and calls run().
"""
from __future__ import annotations

import sys
import time
from typing import Optional, List

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE, COLOR_BG,
    GESTURE_COOLDOWN, PLAYER_START_POS, PLAYER_MOVE_SPEED, UPGRADE_OPTIONS,
)
from game.states import GameState, StateManager
from game.player import Player
from game.enemy import Enemy
from game.round_manager import RoundManager
from game.combat import CombatSystem, ABILITY_DISPLAY_NAMES
from game.particles import ParticleSystem
from ui.hud import HUD
from ui.menu import MainMenu, HowToPlayScreen, SettingsScreen
from audio.sound_manager import SoundManager
from vision.gesture_detector import GestureDetector, GestureResult, GESTURE_NONE, GESTURE_ULTIMATE
from utils.helpers import clamp


class GameController:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()

        self.fonts = self._load_fonts()
        self.state_mgr = StateManager(GameState.MAIN_MENU)

        self.settings = {
            "volume": 0.7,
            "difficulty": "NORMAL",
            "sensitivity": 0.7,
            "camera_index": 0,
        }

        self.sound_manager = SoundManager(master_volume=self.settings["volume"])
        self.particles = ParticleSystem()
        self.combat = CombatSystem(self.particles, self.sound_manager)
        self.hud = HUD(self.fonts)
        self.round_manager = RoundManager()

        self.player: Optional[Player] = None
        self.enemies: List[Enemy] = []  # All active enemies in current round
        self.current_enemy: Optional[Enemy] = None  # Enemy player is fighting

        self.detector = GestureDetector(camera_index=self.settings["camera_index"])
        self.camera_available = False
        self.mediapipe_available = False
        self.keyboard_fallback = False
        self._last_gesture_result = GestureResult()
        self._gesture_last_trigger_time = 0.0
        self._last_triggered_gesture = GESTURE_NONE

        self.countdown_value = 3
        self._countdown_timer = 0.0
        self._round_complete_timer = 0.0
        self._next_enemy_spawn_timer = 0.5  # Wait 0.5s before spawning next enemy

        # Upgrade selection
        self.upgrade_selection: List[dict] = []
        self.selected_upgrade_index = 0

        self.running = True
        self.webcam_warning = ""

        self._build_menus()
        self._init_vision()

    # ------------------------------------------------------------------
    def _load_fonts(self) -> dict:
        pygame.font.init()

        def safe_font(name: str, size: int, bold: bool = False) -> pygame.font.Font:
            try:
                font = pygame.font.SysFont(name, size, bold=bold)
                if font is not None:
                    return font
            except Exception:
                pass
            return pygame.font.Font(None, size)

        return {
            "title": safe_font("arialblack", 64, bold=True),
            "large": safe_font("arial", 40, bold=True),
            "medium": safe_font("arial", 26, bold=True),
            "small": safe_font("arial", 18),
        }

    def _build_menus(self) -> None:
        self.main_menu = MainMenu(
            self.fonts,
            on_start=self._start_new_game,
            on_how_to_play=lambda: self.state_mgr.set(GameState.HOW_TO_PLAY),
            on_settings=lambda: self.state_mgr.set(GameState.SETTINGS),
            on_exit=self._quit,
        )
        self.how_to_play = HowToPlayScreen(self.fonts, on_back=lambda: self.state_mgr.set(GameState.MAIN_MENU))
        self.settings_screen = SettingsScreen(
            self.fonts,
            on_back=lambda: self.state_mgr.set(GameState.MAIN_MENU),
            get_settings=lambda: self.settings,
            set_setting=self._apply_setting,
        )

    def _apply_setting(self, key: str, value) -> None:
        self.settings[key] = value
        if key == "volume":
            self.sound_manager.set_volume(value)
        if key == "camera_index":
            self._init_vision(reinit_camera=True)

    def _init_vision(self, reinit_camera: bool = False) -> None:
        if reinit_camera:
            self.detector.release()
            self.detector = GestureDetector(camera_index=self.settings["camera_index"])
        cam_ok, mp_ok = self.detector.initialize()
        self.camera_available = cam_ok
        self.mediapipe_available = mp_ok
        self.keyboard_fallback = not (cam_ok and mp_ok)
        if self.keyboard_fallback:
            self.webcam_warning = "Webcam unavailable — Keyboard fallback enabled."
        else:
            self.webcam_warning = ""

    def _quit(self) -> None:
        self.running = False

    # ------------------------------------------------------------------
    # Game initialization and round management
    # ------------------------------------------------------------------
    def _start_new_game(self) -> None:
        self.round_manager.reset()
        self.combat.score = 0
        self.player = Player(*PLAYER_START_POS)
        self._begin_round()
        self.state_mgr.set(GameState.COUNTDOWN)
        self.countdown_value = 3
        self._countdown_timer = time.time()

    def _begin_round(self) -> None:
        """Start a new round: spawn player and first enemy."""
        self.enemies.clear()
        self.current_enemy = None
        self._next_enemy_spawn_timer = 0.0

        # Spawn first enemy for this round
        next_enemy = self.round_manager.spawn_next_enemy()
        if next_enemy:
            self.enemies.append(next_enemy)
            self.current_enemy = next_enemy

        self.combat.reset_for_level()

    def _try_spawn_next_enemy(self) -> bool:
        """Try to spawn the next enemy in the round. Returns True if spawned."""
        if not self.round_manager.is_round_complete():
            next_enemy = self.round_manager.spawn_next_enemy()
            if next_enemy:
                self.enemies.append(next_enemy)
                self.current_enemy = next_enemy
                return True
        return False

    def _check_round_complete(self) -> None:
        """Check if all enemies in the round have been killed."""
        if self.round_manager.is_round_complete():
            self.state_mgr.set(GameState.ROUND_COMPLETE)
            self._round_complete_timer = 2.0
            self.sound_manager.play("victory")
            # Select 3 random upgrade options
            import random
            self.upgrade_selection = random.sample(UPGRADE_OPTIONS, min(3, len(UPGRADE_OPTIONS)))
            self.selected_upgrade_index = 0

    def _apply_selected_upgrade(self) -> None:
        """Apply the selected upgrade to the player."""
        if 0 <= self.selected_upgrade_index < len(self.upgrade_selection):
            upgrade = self.upgrade_selection[self.selected_upgrade_index]
            self.player.apply_upgrade(upgrade["key"])
            self.sound_manager.play("attack")

        # Move to next round or victory
        if self.round_manager.advance_round():
            self._begin_round()
            self.state_mgr.set(GameState.COUNTDOWN)
            self.countdown_value = 3
            self._countdown_timer = time.time()
        else:
            self.state_mgr.set(GameState.VICTORY)
            self.sound_manager.play("victory")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        try:
            while self.running:
                dt = self.clock.tick(FPS) / 1000.0
                self._handle_events()
                self._update(dt)
                self._draw()
                pygame.display.flip()
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        self.detector.release()
        pygame.quit()

    # ------------------------------------------------------------------
    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

            state = self.state_mgr.current
            if state == GameState.MAIN_MENU:
                self.main_menu.handle_event(event)
            elif state == GameState.HOW_TO_PLAY:
                self.how_to_play.handle_event(event)
            elif state == GameState.SETTINGS:
                self.settings_screen.handle_event(event)

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        state = self.state_mgr.current
        if event.key == pygame.K_ESCAPE:
            if state == GameState.PLAYING:
                self.state_mgr.set(GameState.PAUSED)
            elif state == GameState.PAUSED:
                self.state_mgr.set(GameState.PLAYING)
            elif state in (GameState.HOW_TO_PLAY, GameState.SETTINGS):
                self.state_mgr.set(GameState.MAIN_MENU)

        if state == GameState.PLAYING and self.player and self.player.alive:
            if event.key == pygame.K_j:
                self._trigger_ability_by_gesture("FIST")
            elif event.key == pygame.K_k:
                self._trigger_ability_by_gesture("ONE_FINGER")
            elif event.key == pygame.K_l:
                self._trigger_ability_by_gesture("ULTIMATE")
            elif event.key == pygame.K_SPACE:
                self._trigger_ability_by_gesture("OPEN_PALM")

        if state == GameState.PAUSED and event.key == pygame.K_r:
            self.state_mgr.set(GameState.PLAYING)

        if state == GameState.GAME_OVER and event.key == pygame.K_r:
            self._start_new_game()

        if state == GameState.VICTORY and event.key == pygame.K_RETURN:
            self.state_mgr.set(GameState.MAIN_MENU)

        # Upgrade selection
        if state == GameState.UPGRADE:
            if event.key == pygame.K_LEFT:
                self.selected_upgrade_index = (self.selected_upgrade_index - 1) % len(self.upgrade_selection)
            elif event.key == pygame.K_RIGHT:
                self.selected_upgrade_index = (self.selected_upgrade_index + 1) % len(self.upgrade_selection)
            elif event.key == pygame.K_RETURN:
                self._apply_selected_upgrade()

    # ------------------------------------------------------------------
    def _update(self, dt: float) -> None:
        state = self.state_mgr.current

        if state == GameState.MAIN_MENU:
            self.main_menu.update(dt)
        elif state == GameState.HOW_TO_PLAY:
            self.how_to_play.update(dt)
        elif state == GameState.SETTINGS:
            self.settings_screen.update(dt)
        elif state == GameState.COUNTDOWN:
            self._update_countdown()
        elif state == GameState.PLAYING:
            self._update_playing(dt)
        elif state == GameState.ROUND_COMPLETE:
            self._update_round_complete(dt)

        self.particles.update(dt)

    def _update_countdown(self) -> None:
        elapsed = time.time() - self._countdown_timer
        remaining = 3 - int(elapsed)
        if remaining <= 0:
            self.state_mgr.set(GameState.PLAYING)
        else:
            self.countdown_value = remaining

    def _update_round_complete(self, dt: float) -> None:
        self._round_complete_timer -= dt
        if self._round_complete_timer <= 0:
            self.state_mgr.set(GameState.UPGRADE)

    def _process_vision(self) -> GestureResult:
        if self.keyboard_fallback:
            return GestureResult()
        result = self.detector.process_frame()
        self._last_gesture_result = result
        return result

    def _trigger_ability_by_gesture(self, gesture: str) -> None:
        if not self.player or not self.player.alive:
            return
        ability = self.combat.trigger_player_ability(gesture, self.player)
        if ability:
            combo_name = self.combat.combo.register_gesture(gesture)

    def _update_playing(self, dt: float) -> None:
        if not self.player:
            return

        # Spawn next enemy if the current one is dead and there are more to spawn
        if self.current_enemy and not self.current_enemy.alive:
            self._next_enemy_spawn_timer -= dt
            if self._next_enemy_spawn_timer <= 0:
                self.round_manager.register_enemy_kill()
                # Reward XP
                xp_reward = self.round_manager.get_reward_xp(is_round_complete=False)
                self.player.add_xp(xp_reward)
                # Try to spawn next enemy
                if not self._try_spawn_next_enemy():
                    self._check_round_complete()
                else:
                    self._next_enemy_spawn_timer = 0.5

        result = self._process_vision()

        if not self.keyboard_fallback:
            # Movement from left hand position
            if result.primary_hand_x is not None and result.hand_count > 0:
                self.player.set_position_from_ratio(1.0 - result.primary_hand_x)

            gesture = result.gesture
            now = time.time()
            gesture_changed = gesture != self._last_triggered_gesture
            cooldown_ok = (now - self._gesture_last_trigger_time) >= GESTURE_COOLDOWN

            if gesture == "OPEN_PALM":
                if not self.player.is_shielding:
                    self._trigger_ability_by_gesture("OPEN_PALM")
                self._gesture_last_trigger_time = now
            else:
                self.combat.stop_shield_if_active(False, self.player)

                if gesture != GESTURE_NONE and (gesture_changed or cooldown_ok):
                    self._trigger_ability_by_gesture(gesture)
                    self._gesture_last_trigger_time = now

            self._last_triggered_gesture = gesture
        else:
            # Keyboard fallback movement
            keys = pygame.key.get_pressed()
            if keys[pygame.K_a]:
                self.player.move(-PLAYER_MOVE_SPEED)
            if keys[pygame.K_d]:
                self.player.move(PLAYER_MOVE_SPEED)
            if not keys[pygame.K_SPACE] and self.player.is_shielding:
                self.player.stop_shield()

        self.player.update(dt)

        # Update all active enemies
        for enemy in self.enemies:
            if enemy.alive:
                enemy.update(dt, self.player.x, self.player.y)

                # Enemy attack handling
                if enemy.pending_attack and enemy.alive:
                    if enemy.ranged:
                        self.combat.spawn_enemy_projectile(enemy)
                    else:
                        # Melee attack
                        from game.collision import melee_in_range
                        if melee_in_range(enemy.x, self.player.x):
                            dmg = self.player.take_damage(enemy.attack_damage)
                            if dmg > 0:
                                self.particles.emit_hit(self.player.x, self.player.y)

        self.combat.update(dt, self.player, self.current_enemy)

        if not self.player.alive:
            self.state_mgr.set(GameState.GAME_OVER)
            self.sound_manager.play("game_over")

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        state = self.state_mgr.current
        self.screen.fill(COLOR_BG)

        if state == GameState.MAIN_MENU:
            self.main_menu.draw(self.screen)
        elif state == GameState.HOW_TO_PLAY:
            self.how_to_play.draw(self.screen)
        elif state == GameState.SETTINGS:
            self.settings_screen.draw(self.screen)
        elif state in (GameState.COUNTDOWN, GameState.PLAYING, GameState.PAUSED,
                       GameState.ROUND_COMPLETE, GameState.GAME_OVER):
            self._draw_gameplay()
            if state == GameState.COUNTDOWN:
                self.hud.draw_countdown(self.screen, str(self.countdown_value) if self.countdown_value > 0 else "FIGHT!")
            elif state == GameState.PAUSED:
                self.hud.draw_center_message(self.screen, "PAUSED", "Press ESC to resume")
            elif state == GameState.ROUND_COMPLETE:
                self.hud.draw_center_message(
                    self.screen, "ROUND COMPLETE!",
                    f"Score: {self.combat.score}   Level: {self.player.level}   XP: {self.player.xp}/{self.player.xp_to_next_level}"
                )
            elif state == GameState.GAME_OVER:
                self.hud.draw_center_message(self.screen, "GAME OVER", "Press R to retry")
        elif state == GameState.UPGRADE:
            self._draw_upgrade_screen()
        elif state == GameState.VICTORY:
            self.screen.fill((20, 14, 30))
            from utils.helpers import draw_text
            cx = SCREEN_WIDTH // 2
            draw_text(self.screen, "VICTORY!", self.fonts["title"], (255, 210, 60), (cx, 260), center=True)
            draw_text(self.screen, f"Final Score: {self.combat.score}", self.fonts["medium"],
                      (230, 230, 235), (cx, 340), center=True)
            draw_text(self.screen, f"Final Level: {self.player.level}", self.fonts["medium"],
                      (230, 230, 235), (cx, 380), center=True)
            draw_text(self.screen, "Press ENTER to return to menu", self.fonts["small"],
                      (200, 200, 210), (cx, 450), center=True)

    def _draw_gameplay(self) -> None:
        shake_x, shake_y = self.particles.get_shake_offset()
        bg_color = self.round_manager.background_color
        game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        game_surface.fill(bg_color)

        pygame.draw.rect(game_surface, (30, 30, 42), (0, 560, SCREEN_WIDTH, 160))
        pygame.draw.line(game_surface, (60, 60, 80), (0, 560), (SCREEN_WIDTH, 560), 2)

        if self.player:
            self.player.draw(game_surface)

        # Draw all active enemies
        for enemy in self.enemies:
            enemy.draw(game_surface)

        self.combat.draw(game_surface)
        self.particles.draw(game_surface)

        self.screen.blit(game_surface, (shake_x, shake_y))

        if self.player and self.current_enemy:
            self.hud.draw_top_bars(self.screen, self.player, self.current_enemy,
                                    self.round_manager.round_name, self.round_manager.round_number,
                                    self.combat.score)
            self.hud.draw_bottom_status(self.screen, self._last_gesture_result.gesture,
                                         self.combat.last_ability_name,
                                         self.combat.combo.hit_streak, self.combat.score)

            # Round progress
            enemy_count = self.round_manager.current["enemy_count"]
            killed = self.round_manager.enemies_killed_in_round
            from utils.helpers import draw_text
            progress_text = f"ROUND {self.round_manager.round_number} - Enemies: {killed}/{enemy_count}"
            draw_text(self.screen, progress_text, self.fonts["small"], (200, 200, 210), (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 90), center=True)

        if not self.keyboard_fallback:
            self.hud.draw_webcam_preview(self.screen, self.detector.last_frame_bgr,
                                          self._last_gesture_result, self.detector)
        elif self.webcam_warning:
            from utils.helpers import draw_text
            draw_text(self.screen, self.webcam_warning, self.fonts["small"], (255, 120, 120), (24, SCREEN_HEIGHT - 30))

    def _draw_upgrade_screen(self) -> None:
        """Draw the upgrade selection screen."""
        self.screen.fill((20, 14, 30))
        from utils.helpers import draw_text

        cx = SCREEN_WIDTH // 2
        draw_text(self.screen, f"ROUND {self.round_manager.round_number} COMPLETE!", self.fonts["large"],
                  (255, 210, 60), (cx, 80), center=True)
        draw_text(self.screen, "Choose an Upgrade", self.fonts["medium"], (230, 230, 235), (cx, 160), center=True)

        # Draw upgrade options
        start_y = 250
        spacing = 100
        for i, upgrade in enumerate(self.upgrade_selection):
            y = start_y + i * spacing
            is_selected = i == self.selected_upgrade_index
            color = (255, 255, 0) if is_selected else (200, 200, 200)
            border_color = (255, 210, 60) if is_selected else (100, 100, 100)

            # Box for upgrade
            box = pygame.Rect(cx - 280, y - 30, 560, 70)
            pygame.draw.rect(self.screen, border_color, box, width=3, border_radius=8)
            if is_selected:
                pygame.draw.rect(self.screen, (255, 210, 60, 100), box, border_radius=8)

            draw_text(self.screen, f"{upgrade['icon']} {upgrade['name']}", self.fonts["medium"], color, (cx - 250, y), center=False)
            draw_text(self.screen, upgrade['description'], self.fonts["small"], (180, 180, 180), (cx - 250, y + 25), center=False)

        draw_text(self.screen, "← LEFT / RIGHT → to select, ENTER to confirm", self.fonts["small"],
                  (150, 150, 150), (cx, SCREEN_HEIGHT - 60), center=True)
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()

        self.fonts = self._load_fonts()
        self.state_mgr = StateManager(GameState.MAIN_MENU)

        self.settings = {
            "volume": 0.7,
            "difficulty": "NORMAL",
            "sensitivity": 0.7,
            "camera_index": 0,
        }

        self.sound_manager = SoundManager(master_volume=self.settings["volume"])
        self.particles = ParticleSystem()
        self.combat = CombatSystem(self.particles, self.sound_manager)
        self.hud = HUD(self.fonts)
        self.round_manager = RoundManager()

        self.player: Optional[Player] = None
        self.enemies: List[Enemy] = []  # All active enemies in current round
        self.current_enemy: Optional[Enemy] = None  # Enemy player is fighting

        self.detector = GestureDetector(camera_index=self.settings["camera_index"])
        self.camera_available = False
        self.mediapipe_available = False
        self.keyboard_fallback = False
        self._last_gesture_result = GestureResult()
        self._gesture_last_trigger_time = 0.0
        self._last_triggered_gesture = GESTURE_NONE

        self.countdown_value = 3
        self._countdown_timer = 0.0
        self._round_complete_timer = 0.0
        self._next_enemy_spawn_timer = 0.5  # Wait 0.5s before spawning next enemy

        # Upgrade selection
        self.upgrade_selection: List[dict] = []
        self.selected_upgrade_index = 0

        self.running = True
        self.webcam_warning = ""

        self._build_menus()
        self._init_vision()

    # ------------------------------------------------------------------
    def _load_fonts(self) -> dict:
        pygame.font.init()

        def safe_font(name: str, size: int, bold: bool = False) -> pygame.font.Font:
            try:
                font = pygame.font.SysFont(name, size, bold=bold)
                if font is not None:
                    return font
            except Exception:
                pass
            return pygame.font.Font(None, size)

        return {
            "title": safe_font("arialblack", 64, bold=True),
            "large": safe_font("arial", 40, bold=True),
            "medium": safe_font("arial", 26, bold=True),
            "small": safe_font("arial", 18),
        }

    def _build_menus(self) -> None:
        self.main_menu = MainMenu(
            self.fonts,
            on_start=self._start_new_game,
            on_how_to_play=lambda: self.state_mgr.set(GameState.HOW_TO_PLAY),
            on_settings=lambda: self.state_mgr.set(GameState.SETTINGS),
            on_exit=self._quit,
        )
        self.how_to_play = HowToPlayScreen(self.fonts, on_back=lambda: self.state_mgr.set(GameState.MAIN_MENU))
        self.settings_screen = SettingsScreen(
            self.fonts,
            on_back=lambda: self.state_mgr.set(GameState.MAIN_MENU),
            get_settings=lambda: self.settings,
            set_setting=self._apply_setting,
        )

    def _apply_setting(self, key: str, value) -> None:
        self.settings[key] = value
        if key == "volume":
            self.sound_manager.set_volume(value)
        if key == "camera_index":
            self._init_vision(reinit_camera=True)

    def _init_vision(self, reinit_camera: bool = False) -> None:
        if reinit_camera:
            self.detector.release()
            self.detector = GestureDetector(camera_index=self.settings["camera_index"])
        cam_ok, mp_ok = self.detector.initialize()
        self.camera_available = cam_ok
        self.mediapipe_available = mp_ok
        self.keyboard_fallback = not (cam_ok and mp_ok)
        if self.keyboard_fallback:
            self.webcam_warning = "Webcam unavailable — Keyboard fallback enabled."
        else:
            self.webcam_warning = ""

    def _quit(self) -> None:
        self.running = False

    # ------------------------------------------------------------------
    # Game initialization and round management
    # ------------------------------------------------------------------
    def _start_new_game(self) -> None:
        self.round_manager.reset()
        self.combat.score = 0
        self.player = Player(*PLAYER_START_POS)
        self._begin_round()
        self.state_mgr.set(GameState.COUNTDOWN)
        self.countdown_value = 3
        self._countdown_timer = time.time()

    def _begin_round(self) -> None:
        """Start a new round: spawn player and first enemy."""
        self.enemies.clear()
        self.current_enemy = None
        self._next_enemy_spawn_timer = 0.0

        # Spawn first enemy for this round
        next_enemy = self.round_manager.spawn_next_enemy()
        if next_enemy:
            self.enemies.append(next_enemy)
            self.current_enemy = next_enemy

        self.combat.reset_for_level()

    def _try_spawn_next_enemy(self) -> bool:
        """Try to spawn the next enemy in the round. Returns True if spawned."""
        if not self.round_manager.is_round_complete():
            next_enemy = self.round_manager.spawn_next_enemy()
            if next_enemy:
                self.enemies.append(next_enemy)
                self.current_enemy = next_enemy
                return True
        return False

    def _check_round_complete(self) -> None:
        """Check if all enemies in the round have been killed."""
        if self.round_manager.is_round_complete():
            self.state_mgr.set(GameState.ROUND_COMPLETE)
            self._round_complete_timer = 2.0
            self.sound_manager.play("victory")
            # Select 3 random upgrade options
            import random
            self.upgrade_selection = random.sample(UPGRADE_OPTIONS, min(3, len(UPGRADE_OPTIONS)))
            self.selected_upgrade_index = 0

    def _apply_selected_upgrade(self) -> None:
        """Apply the selected upgrade to the player."""
        if 0 <= self.selected_upgrade_index < len(self.upgrade_selection):
            upgrade = self.upgrade_selection[self.selected_upgrade_index]
            self.player.apply_upgrade(upgrade["key"])
            self.sound_manager.play("attack")

        # Move to next round or victory
        if self.round_manager.advance_round():
            self._begin_round()
            self.state_mgr.set(GameState.COUNTDOWN)
            self.countdown_value = 3
            self._countdown_timer = time.time()
        else:
            self.state_mgr.set(GameState.VICTORY)
            self.sound_manager.play("victory")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        try:
            while self.running:
                dt = self.clock.tick(FPS) / 1000.0
                self._handle_events()
                self._update(dt)
                self._draw()
                pygame.display.flip()
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        self.detector.release()
        pygame.quit()

    # ------------------------------------------------------------------
    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

            state = self.state_mgr.current
            if state == GameState.MAIN_MENU:
                self.main_menu.handle_event(event)
            elif state == GameState.HOW_TO_PLAY:
                self.how_to_play.handle_event(event)
            elif state == GameState.SETTINGS:
                self.settings_screen.handle_event(event)

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        state = self.state_mgr.current
        if event.key == pygame.K_ESCAPE:
            if state == GameState.PLAYING:
                self.state_mgr.set(GameState.PAUSED)
            elif state == GameState.PAUSED:
                self.state_mgr.set(GameState.PLAYING)
            elif state in (GameState.HOW_TO_PLAY, GameState.SETTINGS):
                self.state_mgr.set(GameState.MAIN_MENU)

        if state == GameState.PLAYING and self.player and self.player.alive:
            if event.key == pygame.K_j:
                self._trigger_ability_by_gesture("FIST")
            elif event.key == pygame.K_k:
                self._trigger_ability_by_gesture("ONE_FINGER")
            elif event.key == pygame.K_l:
                self._trigger_ability_by_gesture("ULTIMATE")
            elif event.key == pygame.K_SPACE:
                self._trigger_ability_by_gesture("OPEN_PALM")

        if state == GameState.PAUSED and event.key == pygame.K_r:
            self.state_mgr.set(GameState.PLAYING)

        if state == GameState.GAME_OVER and event.key == pygame.K_r:
            self._start_new_game()

        if state == GameState.VICTORY and event.key == pygame.K_RETURN:
            self.state_mgr.set(GameState.MAIN_MENU)

    # ------------------------------------------------------------------
    def _update(self, dt: float) -> None:
        state = self.state_mgr.current

        if state == GameState.MAIN_MENU:
            self.main_menu.update(dt)
        elif state == GameState.HOW_TO_PLAY:
            self.how_to_play.update(dt)
        elif state == GameState.SETTINGS:
            self.settings_screen.update(dt)
        elif state == GameState.COUNTDOWN:
            self._update_countdown()
        elif state == GameState.PLAYING:
            self._update_playing(dt)
        elif state == GameState.ROUND_COMPLETE:
            self._update_round_complete(dt)

        self.particles.update(dt)

    def _update_countdown(self) -> None:
        elapsed = time.time() - self._countdown_timer
        remaining = 3 - int(elapsed)
        if remaining <= 0:
            self.state_mgr.set(GameState.PLAYING)
        else:
            self.countdown_value = remaining

    def _update_round_complete(self, dt: float) -> None:
        self._round_complete_timer -= dt
        if self._round_complete_timer <= 0:
            self.state_mgr.set(GameState.UPGRADE)

    def _process_vision(self) -> GestureResult:
        if self.keyboard_fallback:
            return GestureResult()
        result = self.detector.process_frame()
        self._last_gesture_result = result
        return result

    def _trigger_ability_by_gesture(self, gesture: str) -> None:
        if not self.player or not self.player.alive:
            return
        ability = self.combat.trigger_player_ability(gesture, self.player)
        if ability:
            combo_name = self.combat.combo.register_gesture(gesture)
            # combo_name currently used for potential future bonus FX/logic

    def _update_playing(self, dt: float) -> None:
        if not self.player:
            return

        # Spawn next enemy if the current one is dead and there are more to spawn
        if self.current_enemy and not self.current_enemy.alive:
            self._next_enemy_spawn_timer -= dt
            if self._next_enemy_spawn_timer <= 0:
                self.round_manager.register_enemy_kill()
                # Reward XP
                xp_reward = self.round_manager.get_reward_xp(is_round_complete=False)
                self.player.add_xp(xp_reward)
                # Try to spawn next enemy
                if not self._try_spawn_next_enemy():
                    self._check_round_complete()
                else:
                    self._next_enemy_spawn_timer = 0.5

        result = self._process_vision()

        if not self.keyboard_fallback:
            # Movement from left hand position
            if result.primary_hand_x is not None and result.hand_count > 0:
                self.player.set_position_from_ratio(1.0 - result.primary_hand_x)

            gesture = result.gesture
            now = time.time()
            gesture_changed = gesture != self._last_triggered_gesture
            cooldown_ok = (now - self._gesture_last_trigger_time) >= GESTURE_COOLDOWN

            if gesture == "OPEN_PALM":
                if not self.player.is_shielding:
                    self._trigger_ability_by_gesture("OPEN_PALM")
                self._gesture_last_trigger_time = now
            else:
                self.combat.stop_shield_if_active(False, self.player)

                if gesture != GESTURE_NONE and (gesture_changed or cooldown_ok):
                    self._trigger_ability_by_gesture(gesture)
                    self._gesture_last_trigger_time = now

            self._last_triggered_gesture = gesture
        else:
            # Keyboard fallback movement
            keys = pygame.key.get_pressed()
            if keys[pygame.K_a]:
                self.player.move(-PLAYER_MOVE_SPEED)
            if keys[pygame.K_d]:
                self.player.move(PLAYER_MOVE_SPEED)
            if not keys[pygame.K_SPACE] and self.player.is_shielding:
                self.player.stop_shield()

        self.player.update(dt)

        # Update all active enemies
        for enemy in self.enemies:
            if enemy.alive:
                enemy.update(dt, self.player.x, self.player.y)

                # Enemy attack handling
                if enemy.pending_attack and enemy.alive:
                    if enemy.ranged:
                        self.combat.spawn_enemy_projectile(enemy)
                    else:
                        # Melee attack
                        from game.collision import melee_in_range
                        if melee_in_range(enemy.x, self.player.x):
                            dmg = self.player.take_damage(enemy.attack_damage)
                            if dmg > 0:
                                self.particles.emit_hit(self.player.x, self.player.y)

        self.combat.update(dt, self.player, self.current_enemy)

        if not self.player.alive:
            self.state_mgr.set(GameState.GAME_OVER)
            self.sound_manager.play("game_over")

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        state = self.state_mgr.current
        self.screen.fill(COLOR_BG)

        if state == GameState.MAIN_MENU:
            self.main_menu.draw(self.screen)
        elif state == GameState.HOW_TO_PLAY:
            self.how_to_play.draw(self.screen)
        elif state == GameState.SETTINGS:
            self.settings_screen.draw(self.screen)
        elif state in (GameState.COUNTDOWN, GameState.PLAYING, GameState.PAUSED,
                       GameState.ROUND_COMPLETE, GameState.GAME_OVER):
            self._draw_gameplay()
            if state == GameState.COUNTDOWN:
                self.hud.draw_countdown(self.screen, str(self.countdown_value) if self.countdown_value > 0 else "FIGHT!")
            elif state == GameState.PAUSED:
                self.hud.draw_center_message(self.screen, "PAUSED", "Press ESC to resume")
            elif state == GameState.ROUND_COMPLETE:
                self.hud.draw_center_message(
                    self.screen, "ROUND COMPLETE!",
                    f"Score: {self.combat.score}   Level: {self.player.level}   XP: {self.player.xp}/{self.player.xp_to_next_level}"
                )
            elif state == GameState.GAME_OVER:
                self.hud.draw_center_message(self.screen, "GAME OVER", "Press R to retry")
        elif state == GameState.UPGRADE:
            self._draw_upgrade_screen()
        elif state == GameState.VICTORY:
            self.screen.fill((20, 14, 30))
            from utils.helpers import draw_text
            cx = SCREEN_WIDTH // 2
            draw_text(self.screen, "VICTORY!", self.fonts["title"], (255, 210, 60), (cx, 260), center=True)
            draw_text(self.screen, f"Final Score: {self.combat.score}", self.fonts["medium"],
                      (230, 230, 235), (cx, 340), center=True)
            draw_text(self.screen, f"Final Level: {self.player.level}", self.fonts["medium"],
                      (230, 230, 235), (cx, 380), center=True)
            draw_text(self.screen, "Press ENTER to return to menu", self.fonts["small"],
                      (200, 200, 210), (cx, 450), center=True)

    def _draw_gameplay(self) -> None:
        shake_x, shake_y = self.particles.get_shake_offset()
        bg_color = self.round_manager.background_color
        game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        game_surface.fill(bg_color)

        pygame.draw.rect(game_surface, (30, 30, 42), (0, 560, SCREEN_WIDTH, 160))
        pygame.draw.line(game_surface, (60, 60, 80), (0, 560), (SCREEN_WIDTH, 560), 2)

        if self.player:
            self.player.draw(game_surface)

        # Draw all active enemies
        for enemy in self.enemies:
            enemy.draw(game_surface)

        self.combat.draw(game_surface)
        self.particles.draw(game_surface)

        self.screen.blit(game_surface, (shake_x, shake_y))

        if self.player and self.current_enemy:
            self.hud.draw_top_bars(self.screen, self.player, self.current_enemy,
                                    self.round_manager.round_name, self.round_manager.round_number,
                                    self.combat.score)
            self.hud.draw_bottom_status(self.screen, self._last_gesture_result.gesture,
                                         self.combat.last_ability_name,
                                         self.combat.combo.hit_streak, self.combat.score)

            # Round progress
            enemy_count = self.round_manager.current["enemy_count"]
            killed = self.round_manager.enemies_killed_in_round
            from utils.helpers import draw_text
            progress_text = f"ROUND {self.round_manager.round_number} - Enemies: {killed}/{enemy_count}"
            draw_text(self.screen, progress_text, self.fonts["small"], (200, 200, 210), (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 90), center=True)

        if not self.keyboard_fallback:
            self.hud.draw_webcam_preview(self.screen, self.detector.last_frame_bgr,
                                          self._last_gesture_result, self.detector)
        elif self.webcam_warning:
            from utils.helpers import draw_text
            draw_text(self.screen, self.webcam_warning, self.fonts["small"], (255, 120, 120), (24, SCREEN_HEIGHT - 30))
