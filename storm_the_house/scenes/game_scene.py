"""
Main gameplay scene – composes sky, ground, house, enemies, weapon,
particles, crosshair, and HUD.

This is the primary scene where the action takes place.
Each instance represents a single *day*.
"""

from __future__ import annotations

import math
import time

import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HORIZON_Y_RATIO,
    ENEMY_SHOT_DAMAGE, MONEY_PER_KILL,
    DAY_DURATION, DAY_END_BONUS, HUD_DAY_COLOR,
    DEBUG_MONEY_ADD, TIME_SCALE_MIN, TIME_SCALE_MAX, TIME_SCALE_STEP,
    ARMORED_CAR_MONEY_REWARD,
)
from storm_the_house.rendering.sky import SkyRenderer
from storm_the_house.rendering.ground import GroundRenderer
from storm_the_house.rendering.background import BackgroundRenderer
from storm_the_house.rendering.crosshair import CrosshairRenderer
from storm_the_house.rendering.hud import HUDRenderer
from storm_the_house.entities.house import House
from storm_the_house.entities.enemy_manager import EnemyManager
from storm_the_house.entities.weapons import WeaponManager, Weapon, Shotgun
from storm_the_house.entities.particles import ParticleManager
from storm_the_house.entities.upgrades import UpgradeState
from storm_the_house.entities.hired_help import HiredHelp


class GameScene:
    """Top-level scene that owns all renderers and game entities.

    Parameters
    ----------
    day : int
        Current day number (1-based).
    money : int
        Starting money carried over from previous day.
    house : House | None
        Existing house to reuse across days (preserves HP / damage).
    weapon_manager : WeaponManager | None
        Existing weapon manager to reuse across days.
    upgrades : UpgradeState | None
        Persistent upgrade tracker shared across days.
    """

    show_cursor = False  # signal to Game to hide the system cursor

    def __init__(self, day: int = 1, money: int = 0,
                 house: House | None = None,
                 weapon_manager: WeaponManager | None = None,
                 upgrades: UpgradeState | None = None):
        self.day = day
        self.sky = SkyRenderer()
        self.ground = GroundRenderer()
        self.background = BackgroundRenderer()

        # Reuse house / weapon manager across days so HP and ammo persist
        self.house = house if house is not None else House()
        self.weapon_manager = weapon_manager if weapon_manager is not None else WeaponManager()

        # Upgrades (persistent across days)
        self.upgrades = upgrades if upgrades is not None else UpgradeState()

        # Apply upgrades to weapons and house at the start of each day
        self._apply_upgrades()

        # Enemy manager – needs the house left edge and day for difficulty scaling
        self.enemy_manager = EnemyManager(house_left_x=self.house.x, day=day)

        # Player money
        self.money: int = money

        # Day timer
        self._day_elapsed: float = 0.0
        self._day_over: bool = False

        # Debug time scale (R = speed up, Y = slow down)
        self._time_scale: float = 1.0

        # Debug menu toggle (Q)
        self._debug_menu_visible: bool = False

        # God mode (G key)
        self._god_mode: bool = False

        # Kill counter (this day only)
        self.kills: int = 0

        # Hired help (repair + gunmen)
        self.hired_help = HiredHelp(self.upgrades)

        # Game over flag (house destroyed)
        self._game_over: bool = False

        # Particle effects
        self.particles = ParticleManager()

        # UI layers
        self.crosshair = CrosshairRenderer()
        self.hud = HUDRenderer()

        # Derived constants
        self._horizon_y = int(SCREEN_HEIGHT * HORIZON_Y_RATIO)

        # Vignette overlay (pre-rendered once)
        self._vignette = self._make_vignette()

        # Day label font (lazy)
        self._font_day: pygame.font.Font | None = None
        self._font_debug: pygame.font.Font | None = None

        # Last frame snapshot for EOD background
        self.last_frame: pygame.Surface | None = None

        # Reload key held state for shotgun
        self._reload_key_held: bool = False

        # Automatic fire state (assault rifle)
        self._fire_held: bool = False

        # Out of ammo indicator
        self._out_of_ammo_timer: float = 0.0
        self._out_of_ammo_duration: float = 0.8  # How long to show "OUT OF AMMO"

    def _apply_upgrades(self):
        """Apply all upgrades to weapons and house."""
        # Apply pistol upgrades
        self.upgrades.apply_to_pistol(self.weapon_manager.pistol)

        # Apply shotgun upgrades if owned
        if self.weapon_manager.shotgun:
            self.upgrades.apply_to_shotgun(self.weapon_manager.shotgun)

        # Apply assault rifle upgrades if owned
        if self.weapon_manager.assault_rifle:
            self.upgrades.apply_to_assault_rifle(self.weapon_manager.assault_rifle)

        # Apply house upgrades
        self.upgrades.apply_to_house(self.house)

    # ── properties ────────────────────────────────────────────────────

    @property
    def weapon(self) -> Weapon:
        """Get the current weapon."""
        return self.weapon_manager.current_weapon

    @property
    def day_progress(self) -> float:
        """0.0 → 1.0 representing how far through the day we are."""
        return min(1.0, self._day_elapsed / DAY_DURATION)

    @property
    def next_scene(self) -> str | None:
        """Return ``'end_of_day'`` when the day timer expires,
        or ``'game_over'`` when the house is destroyed."""
        if self._game_over:
            return "game_over"
        if self._day_over:
            return "end_of_day"
        return None

    # ── helpers ───────────────────────────────────────────────────────────

    def _get_font_day(self) -> pygame.font.Font:
        if self._font_day is None:
            self._font_day = pygame.font.SysFont("arial", 22, bold=True)
        return self._font_day

    @staticmethod
    def _make_vignette() -> pygame.Surface:
        """Create a subtle darkening vignette around screen edges."""
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        max_alpha = 55
        border = 180

        for i in range(border):
            alpha = int(max_alpha * ((border - i) / border) ** 2)
            color = (0, 0, 0, alpha)
            rect = pygame.Rect(i, i,
                               SCREEN_WIDTH - 2 * i,
                               SCREEN_HEIGHT - 2 * i)
            pygame.draw.rect(surf, color, rect, 1)
        return surf

    # ── shooting logic ───────────────────────────────────────────────────

    def _handle_shoot(self, mx: int, my: int):
        """Process a left-click at screen position (mx, my)."""
        weapon = self.weapon
        result = weapon.try_fire(mx, my)

        if not result.success:
            # Show "OUT OF AMMO" text if out of ammo
            if weapon.ammo <= 0 and not weapon.is_reloading:
                self._out_of_ammo_timer = self._out_of_ammo_duration
            if weapon.weapon_type == "assault_rifle":
                self._fire_held = False
                if hasattr(weapon, "release_trigger"):
                    weapon.release_trigger()
            return

        # Process each pellet (shotgun has multiple, pistol has one)
        for pellet_x, pellet_y in result.pellets:
            hit = self._process_pellet(pellet_x, pellet_y, weapon.damage)
            if not hit and pellet_y > self._horizon_y:
                self.particles.emit_dust(pellet_x, pellet_y)

    def _process_pellet(self, px: int, py: int, damage: int) -> bool:
        """Process a single pellet hit. Returns True if something was hit."""
        # Check armored cars first (they're bigger targets)
        for car in self.enemy_manager.armored_cars:
            if not car.alive:
                continue
            rect = car.get_hit_rect()
            if rect.collidepoint(px, py):
                destroyed = car.take_damage(damage)
                bx = max(rect.left, min(px, rect.right))
                by = max(rect.top, min(py, rect.bottom))
                self.particles.emit_blood(bx, by)
                if destroyed:
                    self.money += ARMORED_CAR_MONEY_REWARD
                    self.kills += 1
                    # Emit explosion and debris
                    cx = rect.centerx
                    cy = rect.centery
                    self.particles.emit_explosion(cx, cy, scale=car.scale)
                    self.particles.emit_debris(cx, cy, scale=car.scale)
                    self.particles.emit_smoke(cx, cy - 20, count=12)
                return True

        # Then check regular enemies (sorted by depth for proper hit priority)
        enemies_sorted = sorted(
            self.enemy_manager.enemies,
            key=lambda e: e.foot_y,
            reverse=True,
        )

        for enemy in enemies_sorted:
            if not enemy.alive:
                continue
            rect = enemy.get_hit_rect()
            if rect.collidepoint(px, py):
                killed = enemy.take_damage(damage)
                bx = max(rect.left, min(px, rect.right))
                by = max(rect.top, min(py, rect.bottom))
                self.particles.emit_blood(bx, by)
                if killed:
                    self.money += MONEY_PER_KILL
                    self.kills += 1
                return True

        return False

    def _handle_reload_press(self):
        """Handle reload key press."""
        weapon = self.weapon
        if isinstance(weapon, Shotgun):
            weapon.start_reload()
            self._reload_key_held = True
        else:
            weapon.start_reload()

    def _handle_reload_release(self):
        """Handle reload key release."""
        weapon = self.weapon
        if isinstance(weapon, Shotgun):
            weapon.release_reload()
            self._reload_key_held = False

    def _process_enemy_shots(self):
        # Regular enemy shots
        for enemy in self.enemy_manager.enemies:
            if enemy.fired_this_frame:
                if not self._god_mode:
                    self.house.take_damage(ENEMY_SHOT_DAMAGE)

        # Armored car shots (same damage, 3x faster rate)
        for car in self.enemy_manager.armored_cars:
            if car.fired_this_frame:
                if not self._god_mode:
                    self.house.take_damage(ENEMY_SHOT_DAMAGE)

    # ── tick / draw ──────────────────────────────────────────────────────

    def update(self, dt: float, events: list[pygame.event.Event] | None = None):
        """Advance all sub-systems by *dt* seconds."""
        if self._day_over or self._game_over:
            return

        # Process input events
        if events:
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self._fire_held = True
                        self._handle_shoot(*event.pos)
                    elif event.button == 3:
                        # Right-click also reloads
                        self._handle_reload_press()
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self._fire_held = False
                        weapon = self.weapon
                        if hasattr(weapon, "release_trigger"):
                            weapon.release_trigger()
                    elif event.button == 3:
                        self._handle_reload_release()
                elif event.type == pygame.KEYDOWN:
                    self._handle_key_press(event.key)
                elif event.type == pygame.KEYUP:
                    self._handle_key_release(event.key)

        # Apply debug time scale
        dt *= self._time_scale

        # Update out of ammo timer
        if self._out_of_ammo_timer > 0:
            self._out_of_ammo_timer -= dt

        # Automatic fire (assault rifle)
        if self._fire_held and self.weapon.weapon_type == "assault_rifle":
            if self.weapon.can_fire:
                mx, my = pygame.mouse.get_pos()
                self._handle_shoot(mx, my)
            elif self.weapon.ammo <= 0 and not self.weapon.is_reloading:
                self._fire_held = False
                if hasattr(self.weapon, "release_trigger"):
                    self.weapon.release_trigger()

        # Day timer
        self._day_elapsed += dt
        if self._day_elapsed >= DAY_DURATION:
            self._day_elapsed = DAY_DURATION
            self._day_over = True
            # Award end-of-day bonus
            self.money += DAY_END_BONUS
            return

        self.sky.update(dt)
        self.ground.update(dt)
        self.house.update(dt)
        self.enemy_manager.update(dt)
        self.weapon_manager.update(dt)
        self.particles.update(dt)

        self._process_enemy_shots()

        # Hired help (repair + gunman auto-shoot)
        money_ref = [self.money]
        self.hired_help.update(dt, self.house,
                               self.enemy_manager.enemies, money_ref,
                               self.enemy_manager.armored_cars)
        # Check if gunman earned money
        earned = money_ref[0] - self.money
        if earned > 0:
            self.kills += earned // MONEY_PER_KILL
        self.money = money_ref[0]

        # Check for game over (house destroyed)
        if self.house.hp <= 0:
            self._game_over = True

    def _handle_key_press(self, key: int):
        """Handle key press events."""
        # Weapon switching (1, 2, 3 keys)
        if key == pygame.K_1:
            self.weapon_manager.switch_to(0)
            self._fire_held = False
        elif key == pygame.K_2:
            if self.weapon_manager.owned_count > 1:
                self.weapon_manager.switch_to(1)
                self._fire_held = False
        elif key == pygame.K_3:
            if self.weapon_manager.owned_count > 2:
                self.weapon_manager.switch_to(2)
                self._fire_held = False
        elif key == pygame.K_r or key == pygame.K_SPACE:
            # R and Space both reload
            self._handle_reload_press()
        elif key == pygame.K_q:
            # Toggle debug menu
            self._debug_menu_visible = not self._debug_menu_visible
        elif key == pygame.K_e:
            self.money += DEBUG_MONEY_ADD
        elif key == pygame.K_g:
            # Toggle God mode
            self._god_mode = not self._god_mode
        elif key == pygame.K_t:
            # Spawn armored car (debug)
            self.enemy_manager.spawn_armored_car()
        # R and Y for time scale are handled differently now
        elif key == pygame.K_f:
            # Speed up time (moved from R to F)
            self._time_scale = min(TIME_SCALE_MAX,
                                   self._time_scale * TIME_SCALE_STEP)
        elif key == pygame.K_y:
            # Slow down time
            self._time_scale = max(TIME_SCALE_MIN,
                                   self._time_scale / TIME_SCALE_STEP)

    def _handle_key_release(self, key: int):
        """Handle key release events."""
        if key == pygame.K_r or key == pygame.K_SPACE:
            self._handle_reload_release()
        if key in (pygame.K_1, pygame.K_2, pygame.K_3):
            weapon = self.weapon
            if hasattr(weapon, "release_trigger"):
                weapon.release_trigger()

    def draw(self, surface: pygame.Surface, time_ms: int):
        """Render the full scene in back-to-front order."""
        dp = self.day_progress

        # 1. Sky (with day progress for dynamic colours / sun position)
        self.sky.draw(surface, time_ms, dp)

        # 2. Ground base
        self.ground.draw(surface, time_ms)

        # 3. Background decorations (dunes, fence)
        self.background.draw(surface, time_ms)

        # 4. Enemies and armored cars (sorted by depth internally)
        self.enemy_manager.draw(surface, time_ms)

        # 5. House
        self.house.draw(surface, time_ms)

        # 5b. Hired help (repairmen + gunmen on/around house)
        self.hired_help.draw(surface, self.house, time_ms)

        # 6. Particles
        self.particles.draw(surface)

        # 6b. Armored car effects (muzzle flashes)
        self.enemy_manager.draw_armored_car_effects(surface)

        # Armored car smoke effects (damage-based)
        for car in self.enemy_manager.armored_cars:
            if car.should_emit_smoke():
                rect = car.get_hit_rect()
                self.particles.emit_smoke(rect.centerx, rect.top, count=6)
                car.reset_smoke_timer()

        # 7. Vignette overlay
        surface.blit(self._vignette, (0, 0))

        # 8. HUD (ammo, house HP, money, kills)
        weapon = self.weapon
        self.hud.draw(surface, weapon.ammo, weapon.max_ammo,
                      weapon.is_reloading, weapon.reload_progress,
                      self.house.hp, self.house.max_hp,
                      self.money, self.kills,
                      weapon.weapon_type, weapon.name)

        # 9. Day indicator (top-center)
        self._draw_day_hud(surface)

        # 10. Debug speed indicator (if not 1×)
        if self._time_scale != 1.0 and self._debug_menu_visible:
            self._draw_speed_indicator(surface)

        # 11. Crosshair (always on top of everything)
        recoil_offset = getattr(weapon, "recoil_offset", (0, 0))
        self.crosshair.draw(surface, weapon.reload_progress, recoil_offset)

        # 12. Out of ammo indicator
        if self._out_of_ammo_timer > 0:
            self._draw_out_of_ammo(surface)

        # 13. Debug menu (only when toggled)
        if self._debug_menu_visible:
            self._draw_debug_menu(surface)

        # 14. God mode indicator
        if self._god_mode:
            self._draw_god_mode_indicator(surface)

        # 15. Draw current weapon in bottom-right corner
        self._draw_weapon_display(surface, weapon)

        # Keep a snapshot for the end-of-day background
        self.last_frame = surface.copy()

    def _draw_out_of_ammo(self, surface: pygame.Surface):
        """Draw 'OUT OF AMMO' text below the crosshair."""
        mx, my = pygame.mouse.get_pos()
        font = self._get_font_day()

        # Pulsing alpha
        alpha = int(200 + 55 * math.sin(time.time() * 10))

        text = "OUT OF AMMO"
        text_surf = font.render(text, True, (255, 60, 60))
        shadow_surf = font.render(text, True, (100, 20, 20))

        # Position below crosshair
        tx = mx - text_surf.get_width() // 2
        ty = my + 30

        # Background
        bg_w = text_surf.get_width() + 16
        bg_h = text_surf.get_height() + 8
        bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, min(150, alpha)), bg.get_rect(), border_radius=4)
        surface.blit(bg, (tx - 8, ty - 2))

        surface.blit(shadow_surf, (tx + 1, ty + 1))
        surface.blit(text_surf, (tx, ty))

    def _draw_weapon_display(self, surface: pygame.Surface, weapon):
        """Draw the current weapon in the bottom-right corner with transparent background."""
        weapon_type = weapon.weapon_type

        # Position for weapon display (bottom-right, above house HP bar)
        wx = SCREEN_WIDTH - 220
        wy = SCREEN_HEIGHT - 180

        # Draw semi-transparent background panel
        panel_w = 200
        panel_h = 120
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 128), panel.get_rect(), border_radius=8)
        pygame.draw.rect(panel, (60, 55, 50, 180), panel.get_rect(), width=2, border_radius=8)
        surface.blit(panel, (wx - 20, wy - 20))

        if weapon_type == "shotgun":
            self._draw_shotgun_model(surface, wx, wy, weapon)
        elif weapon_type == "assault_rifle":
            self._draw_rifle_model(surface, wx, wy, weapon)
        else:
            self._draw_pistol_model(surface, wx, wy, weapon)

    def _draw_pistol_model(self, surface: pygame.Surface, x: int, y: int, weapon):
        """Draw a pistol model."""
        # Slide (top part)
        slide_col = (60, 60, 65)
        pygame.draw.rect(surface, slide_col, pygame.Rect(x, y, 80, 20), border_radius=2)
        # Slide serrations
        for i in range(5):
            sx = x + 60 + i * 4
            pygame.draw.line(surface, (45, 45, 50), (sx, y + 2), (sx, y + 18), 1)

        # Barrel
        pygame.draw.rect(surface, (50, 50, 55), pygame.Rect(x + 75, y + 5, 15, 10), border_radius=1)

        # Frame
        frame_col = (55, 55, 60)
        pygame.draw.rect(surface, frame_col, pygame.Rect(x, y + 18, 70, 15), border_radius=2)

        # Trigger guard
        pygame.draw.arc(surface, frame_col, pygame.Rect(x + 25, y + 28, 20, 15), 0, math.pi, 3)

        # Grip
        grip_col = (90, 60, 35)
        pygame.draw.polygon(surface, grip_col, [
            (x, y + 33),
            (x + 35, y + 33),
            (x + 40, y + 85),
            (x - 5, y + 85),
        ])
        # Grip texture
        for i in range(8):
            gy = y + 40 + i * 5
            pygame.draw.line(surface, (70, 45, 25), (x + 2, gy), (x + 32, gy), 1)

        # Magazine
        pygame.draw.rect(surface, (50, 50, 55), pygame.Rect(x + 5, y + 35, 15, 30), border_radius=1)

    def _draw_shotgun_model(self, surface: pygame.Surface, x: int, y: int, weapon):
        """Draw an M870-style pump-action shotgun model."""
        # Barrel (long, top)
        barrel_col = (50, 50, 55)
        pygame.draw.rect(surface, barrel_col, pygame.Rect(x + 60, y - 10, 100, 12), border_radius=2)
        # Barrel end
        pygame.draw.ellipse(surface, (40, 40, 45), pygame.Rect(x + 155, y - 11, 10, 14))

        # Magazine tube (under barrel)
        pygame.draw.rect(surface, (55, 55, 60), pygame.Rect(x + 60, y + 2, 90, 8), border_radius=2)

        # Receiver (main body)
        receiver_col = (45, 45, 50)
        pygame.draw.rect(surface, receiver_col, pygame.Rect(x, y, 70, 30), border_radius=3)
        # Ejection port
        pygame.draw.rect(surface, (30, 30, 35), pygame.Rect(x + 35, y + 3, 20, 12), border_radius=1)

        # Pump (wooden, under receiver)
        pump_col = (110, 70, 40)
        pump_offset = 5 if hasattr(weapon, '_is_pumping') and weapon._is_pumping else 0
        pygame.draw.rect(surface, pump_col, pygame.Rect(x + 15 - pump_offset, y + 28, 45, 18), border_radius=3)
        # Pump grip texture
        for i in range(6):
            py = y + 31 + i * 2
            pygame.draw.line(surface, (90, 55, 30), (x + 18 - pump_offset, py), (x + 57 - pump_offset, py), 1)

        # Stock (wooden)
        stock_col = (100, 65, 35)
        pygame.draw.polygon(surface, stock_col, [
            (x - 5, y + 5),
            (x - 60, y - 10),
            (x - 80, y + 20),
            (x - 75, y + 50),
            (x - 30, y + 55),
            (x, y + 30),
        ])
        # Stock texture
        pygame.draw.line(surface, (80, 50, 25), (x - 10, y + 10), (x - 70, y + 25), 2)
        pygame.draw.line(surface, (80, 50, 25), (x - 15, y + 20), (x - 72, y + 35), 2)

        # Trigger guard
        pygame.draw.arc(surface, receiver_col, pygame.Rect(x - 5, y + 25, 25, 15), 0, math.pi, 3)

        # Shell indicator (show loaded shells visually)
        for i in range(weapon.ammo):
            sx = x - 55 + i * 12
            sy = y + 60
            # Draw small shell
            pygame.draw.rect(surface, (180, 140, 60), pygame.Rect(sx, sy, 8, 15), border_radius=1)
            pygame.draw.rect(surface, (200, 50, 30), pygame.Rect(sx, sy, 8, 8), border_radius=1)

    def _draw_rifle_model(self, surface: pygame.Surface, x: int, y: int, weapon):
        """Draw an M16-style assault rifle model."""
        metal = (55, 55, 60)
        dark = (40, 40, 45)
        olive = (85, 90, 70)
        stock_col = (75, 65, 55)

        # Barrel + muzzle
        pygame.draw.rect(surface, metal, pygame.Rect(x + 80, y - 2, 110, 8), border_radius=2)
        pygame.draw.rect(surface, dark, pygame.Rect(x + 185, y - 4, 12, 12), border_radius=2)
        pygame.draw.line(surface, (90, 90, 95), (x + 190, y - 3), (x + 190, y + 7), 2)

        # Front sight
        pygame.draw.rect(surface, dark, pygame.Rect(x + 155, y - 6, 6, 16), border_radius=1)

        # Carry handle / upper receiver
        pygame.draw.rect(surface, metal, pygame.Rect(x + 20, y - 8, 70, 20), border_radius=3)
        pygame.draw.rect(surface, dark, pygame.Rect(x + 35, y - 14, 40, 6), border_radius=2)

        # Lower receiver
        pygame.draw.rect(surface, metal, pygame.Rect(x + 10, y + 6, 70, 18), border_radius=3)
        pygame.draw.circle(surface, dark, (x + 40, y + 15), 3)

        # Magazine (curved, size reflects ammo)
        mag_height = max(26, 36 + weapon.ammo)
        mag_points = [
            (x + 40, y + 22),
            (x + 60, y + 22),
            (x + 55, y + 22 + mag_height),
            (x + 35, y + 22 + mag_height),
        ]
        pygame.draw.polygon(surface, (60, 60, 65), mag_points)
        pygame.draw.line(surface, (90, 90, 95), (x + 38, y + 30), (x + 52, y + mag_height), 2)

        # Handguard
        pygame.draw.rect(surface, olive, pygame.Rect(x + 85, y + 6, 45, 12), border_radius=2)
        for i in range(4):
            pygame.draw.line(surface, (70, 75, 60), (x + 90 + i * 10, y + 8), (x + 90 + i * 10, y + 16), 1)

        # Stock
        pygame.draw.polygon(surface, stock_col, [
            (x + 10, y + 6),
            (x - 30, y - 4),
            (x - 55, y + 8),
            (x - 50, y + 34),
            (x - 10, y + 28),
            (x + 10, y + 20),
        ])
        pygame.draw.rect(surface, dark, pygame.Rect(x - 52, y + 10, 10, 20), border_radius=2)

        # Grip
        pygame.draw.polygon(surface, stock_col, [
            (x + 28, y + 22),
            (x + 18, y + 52),
            (x + 35, y + 55),
            (x + 42, y + 26),
        ])

        # Trigger guard
        pygame.draw.arc(surface, dark, pygame.Rect(x + 20, y + 20, 22, 14), 0, math.pi, 3)

    # ── day HUD ──────────────────────────────────────────────────────────

    def _draw_day_hud(self, surface: pygame.Surface):
        """Draw 'Day X' and a time-remaining bar at the top-center."""
        font = self._get_font_day()
        dp = self.day_progress

        # Day label
        label = font.render(f"Day {self.day}", True, HUD_DAY_COLOR)
        label_shadow = font.render(f"Day {self.day}", True, (0, 0, 0))
        lx = (SCREEN_WIDTH - label.get_width()) // 2
        ly = 12

        # Background panel
        panel_w = label.get_width() + 24
        bar_w = 160
        total_w = max(panel_w, bar_w + 20)
        panel_h = label.get_height() + 26
        panel_x = (SCREEN_WIDTH - total_w) // 2
        panel = pygame.Surface((total_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 90), panel.get_rect(),
                         border_radius=6)
        surface.blit(panel, (panel_x, ly - 4))

        surface.blit(label_shadow, (lx + 1, ly + 1))
        surface.blit(label, (lx, ly))

        # Time bar beneath the label
        bar_h = 6
        bar_x = (SCREEN_WIDTH - bar_w) // 2
        bar_y = ly + label.get_height() + 4

        # Background
        pygame.draw.rect(surface, (50, 45, 40),
                         pygame.Rect(bar_x, bar_y, bar_w, bar_h),
                         border_radius=3)
        # Fill (shrinks as day progresses)
        fill_w = max(0, int(bar_w * (1.0 - dp)))
        if fill_w > 0:
            # Color transitions from bright to warm as day ends
            if dp < 0.5:
                bar_color = (200, 210, 140)
            elif dp < 0.8:
                bar_color = (220, 180, 90)
            else:
                bar_color = (220, 130, 60)
            pygame.draw.rect(surface, bar_color,
                             pygame.Rect(bar_x, bar_y, fill_w, bar_h),
                             border_radius=3)
        # Border
        pygame.draw.rect(surface, (120, 110, 90),
                         pygame.Rect(bar_x, bar_y, bar_w, bar_h),
                         width=1, border_radius=3)

    # ── debug speed indicator ──────────────────────────────────────────

    def _draw_speed_indicator(self, surface: pygame.Surface):
        """Show the current time scale when it's not 1×."""
        font = self._get_font_day()
        if self._time_scale >= 1.0:
            text = f"Speed: {self._time_scale:.0f}×"
        else:
            text = f"Speed: {self._time_scale:.2f}×"
        color = (255, 200, 80) if self._time_scale > 1.0 else (100, 200, 255)
        label = font.render(text, True, color)
        shadow = font.render(text, True, (0, 0, 0))
        x = SCREEN_WIDTH // 2 - label.get_width() // 2
        y = 52
        surface.blit(shadow, (x + 1, y + 1))
        surface.blit(label, (x, y))

    # ── debug menu ──────────────────────────────────────────────────────

    def _get_font_debug(self) -> pygame.font.Font:
        if self._font_debug is None:
            self._font_debug = pygame.font.SysFont("arial", 18, bold=False)
        return self._font_debug

    def _draw_debug_menu(self, surface: pygame.Surface):
        """Draw debug menu in the bottom-left corner."""
        font = self._get_font_debug()
        lines = [
            "Debug Controls:",
            "E - Add money",
            "F - Speed up time",
            "Y - Slow down time",
            "T - Spawn armored truck",
            "G - Toggle God mode",
            "Q - Toggle debug menu",
        ]

        # Render text to calculate panel size
        rendered = [font.render(line, True, (230, 220, 200)) for line in lines]
        width = max(r.get_width() for r in rendered) + 20
        height = sum(r.get_height() for r in rendered) + 16

        # Panel background
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 18, 15, 200), panel.get_rect(), border_radius=6)
        pygame.draw.rect(panel, (80, 70, 55, 220), panel.get_rect(), width=1, border_radius=6)

        # Position bottom-left with margin
        x = 16
        y = SCREEN_HEIGHT - height - 16
        surface.blit(panel, (x, y))

        # Draw text
        ty = y + 8
        for text_surf in rendered:
            surface.blit(text_surf, (x + 10, ty))
            ty += text_surf.get_height()

    def _draw_god_mode_indicator(self, surface: pygame.Surface):
        """Draw 'GOD MODE' indicator when active."""
        font = self._get_font_day()
        text = "GOD MODE"
        color = (255, 215, 0)  # Gold
        label = font.render(text, True, color)
        shadow = font.render(text, True, (0, 0, 0))

        # Position top-right
        x = SCREEN_WIDTH - label.get_width() - 20
        y = 60

        # Pulsing effect
        alpha = int(180 + 75 * abs(math.sin(time.time() * 3)))

        # Draw with glow
        glow_surf = pygame.Surface((label.get_width() + 20, label.get_height() + 10), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (255, 215, 0, 50), glow_surf.get_rect(), border_radius=4)
        surface.blit(glow_surf, (x - 10, y - 5))

        surface.blit(shadow, (x + 1, y + 1))
        surface.blit(label, (x, y))

