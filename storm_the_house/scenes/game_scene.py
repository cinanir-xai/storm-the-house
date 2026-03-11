"""
Main gameplay scene – composes sky, ground, house, enemies, weapon,
particles, crosshair, and HUD.

This is the primary scene where the action takes place.
Each instance represents a single *day*.
"""

from __future__ import annotations

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
from storm_the_house.entities.weapon import Weapon
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
    weapon : Weapon | None
        Existing weapon to reuse across days.
    upgrades : UpgradeState | None
        Persistent upgrade tracker shared across days.
    """

    show_cursor = False  # signal to Game to hide the system cursor

    def __init__(self, day: int = 1, money: int = 0,
                 house: House | None = None,
                 weapon: Weapon | None = None,
                 upgrades: UpgradeState | None = None):
        self.day = day
        self.sky = SkyRenderer()
        self.ground = GroundRenderer()
        self.background = BackgroundRenderer()

        # Reuse house / weapon across days so HP and ammo persist
        self.house = house if house is not None else House()
        self.weapon = weapon if weapon is not None else Weapon()

        # Upgrades (persistent across days)
        self.upgrades = upgrades if upgrades is not None else UpgradeState()

        # Apply upgrades to weapon and house at the start of each day
        self.upgrades.apply_to_weapon(self.weapon)
        self.upgrades.apply_to_house(self.house)

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

    # ── properties ────────────────────────────────────────────────────

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
        if not self.weapon.try_fire():
            return

        # Check armored cars first (they're bigger targets)
        for car in self.enemy_manager.armored_cars:
            if not car.alive:
                continue
            rect = car.get_hit_rect()
            if rect.collidepoint(mx, my):
                destroyed = car.take_damage(self.weapon.damage)
                bx = max(rect.left, min(mx, rect.right))
                by = max(rect.top, min(my, rect.bottom))
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
                return  # Hit an armored car, stop checking

        # Then check regular enemies (sorted by depth for proper hit priority)
        enemies_sorted = sorted(
            self.enemy_manager.enemies,
            key=lambda e: e.foot_y,
            reverse=True,
        )

        hit = False
        for enemy in enemies_sorted:
            if not enemy.alive:
                continue
            rect = enemy.get_hit_rect()
            if rect.collidepoint(mx, my):
                killed = enemy.take_damage(self.weapon.damage)
                bx = max(rect.left, min(mx, rect.right))
                by = max(rect.top, min(my, rect.bottom))
                self.particles.emit_blood(bx, by)
                if killed:
                    self.money += MONEY_PER_KILL
                    self.kills += 1
                hit = True
                break

        if not hit and my > self._horizon_y:
            self.particles.emit_dust(mx, my)

    def _handle_reload(self):
        self.weapon.start_reload()

    def _process_enemy_shots(self):
        # Regular enemy shots
        for enemy in self.enemy_manager.enemies:
            if enemy.fired_this_frame:
                self.house.take_damage(ENEMY_SHOT_DAMAGE)

        # Armored car shots (same damage, 3x faster rate)
        for car in self.enemy_manager.armored_cars:
            if car.fired_this_frame:
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
                        self._handle_shoot(*event.pos)
                    elif event.button == 3:
                        self._handle_reload()
                elif event.type == pygame.KEYDOWN:
                    self._handle_debug_key(event.key)

        # Apply debug time scale
        dt *= self._time_scale

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
        self.weapon.update(dt)
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

    # ── debug controls ─────────────────────────────────────────────────

    def _handle_debug_key(self, key: int):
        """Process debug key presses (E / R / Y / T / Q)."""
        if key == pygame.K_q:
            # Toggle debug menu
            self._debug_menu_visible = not self._debug_menu_visible
        elif key == pygame.K_e:
            self.money += DEBUG_MONEY_ADD
        elif key == pygame.K_r:
            # Speed up
            self._time_scale = min(TIME_SCALE_MAX,
                                   self._time_scale * TIME_SCALE_STEP)
        elif key == pygame.K_y:
            # Slow down
            self._time_scale = max(TIME_SCALE_MIN,
                                   self._time_scale / TIME_SCALE_STEP)
        elif key == pygame.K_t:
            # Spawn armored car (debug)
            self.enemy_manager.spawn_armored_car()

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
        self.hud.draw(surface, self.weapon.ammo, self.weapon.max_ammo,
                      self.weapon.is_reloading, self.weapon.reload_progress,
                      self.house.hp, self.house.max_hp,
                      self.money, self.kills)

        # 9. Day indicator (top-center)
        self._draw_day_hud(surface)

        # 10. Debug speed indicator (if not 1×)
        if self._time_scale != 1.0 and self._debug_menu_visible:
            self._draw_speed_indicator(surface)

        # 11. Crosshair (always on top of everything)
        self.crosshair.draw(surface, self.weapon.reload_progress)

        # 12. Debug menu (only when toggled)
        if self._debug_menu_visible:
            self._draw_debug_menu(surface)

        # Keep a snapshot for the end-of-day background
        self.last_frame = surface.copy()

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
            "R - Speed up time",
            "Y - Slow down time",
            "T - Spawn armored truck",
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

