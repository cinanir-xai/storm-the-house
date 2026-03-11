"""
Armored Car entity – a boss-type enemy that drives to the middle of the screen
and attacks the house with a machine gun.

States
------
DRIVING  – moving right towards the attack position.
ATTACKING – stationary, firing at the house.
EXPLODING – destroyed; playing explosion animation before removal.
"""

from __future__ import annotations

import enum
import random
import math
import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HORIZON_Y_RATIO,
    ARMORED_CAR_HP, ARMORED_CAR_SPEED, ARMORED_CAR_ATTACK_COOLDOWN,
    ARMORED_CAR_STOP_X_RATIO, ARMORED_CAR_MONEY_REWARD,
    ENEMY_SPAWN_Y_MARGIN_TOP, ENEMY_SPAWN_Y_MARGIN_BOT,
    MUZZLE_FLASH_DURATION, ENEMY_SHOT_DAMAGE,
    EXPLOSION_FLASH_DURATION,
)
from storm_the_house.entities.armored_car_sprites import (
    generate_armored_car_frames, get_explosion_frame,
)
from storm_the_house.utils.drawing import draw_ellipse_alpha


class _State(enum.Enum):
    DRIVING = "driving"
    ATTACKING = "attacking"
    EXPLODING = "exploding"


class ArmoredCar:
    """A boss-type armored car enemy with a driver and machine gunner."""

    def __init__(self, house_left_x: int, speed_multiplier: float = 1.0):
        horizon_y = int(SCREEN_HEIGHT * HORIZON_Y_RATIO)
        ground_h = SCREEN_HEIGHT - horizon_y

        # Random y on the ground (similar to enemies)
        y_min = horizon_y + int(ground_h * ENEMY_SPAWN_Y_MARGIN_TOP)
        y_max = SCREEN_HEIGHT - int(ground_h * ENEMY_SPAWN_Y_MARGIN_BOT)
        self.foot_y = random.randint(y_min, y_max)

        # Depth factor: 0 at horizon, 1 at bottom of screen
        self.depth = (self.foot_y - horizon_y) / ground_h
        # Scale sprite by depth (armored car is larger than soldiers)
        self.scale = 1.2 + self.depth * 0.6

        # Speed scales with depth and day multiplier
        self.speed = ARMORED_CAR_SPEED * (0.7 + self.depth * 0.5) * speed_multiplier

        # Spawn off-screen left
        self.x = random.uniform(-150, -100)

        # Target position: middle of screen (can shoot from there)
        self.target_x = int(SCREEN_WIDTH * ARMORED_CAR_STOP_X_RATIO)

        # State
        self._state = _State.DRIVING
        self.alive = True

        # Health
        self.hp: int = ARMORED_CAR_HP
        self.max_hp: int = ARMORED_CAR_HP

        # Animation
        self._frames = generate_armored_car_frames(self.scale)
        self._frame_idx = 0
        self._frame_timer = 0.0
        self._wheel_rotation = 0.0

        # Attack cooldown
        self._attack_timer = 0.0
        self._attack_playing = False

        # Muzzle flash
        self._flash_timer = 0.0
        self._show_flash = False

        # Set True on the frame the gun fires
        self.fired_this_frame: bool = False

        # Explosion state
        self._explosion_timer: float = 0.0
        self._explosion_duration: float = 0.8  # seconds

        # Damage flash (when hit)
        self._damage_flash_timer: float = 0.0

    # ── properties ────────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def current_frame(self):
        if self._state == _State.DRIVING:
            return self._frames['driving'][self._frame_idx % len(self._frames['driving'])]
        elif self._state == _State.ATTACKING:
            return self._frames['idle'][self._frame_idx % len(self._frames['idle'])]
        else:
            # Exploding - return last known frame
            return self._frames['idle'][0]

    # ── hit detection / damage ─────────────────────────────────────────

    def get_hit_rect(self) -> pygame.Rect:
        """Return the screen-space bounding rect for hit-testing clicks."""
        frame = self.current_frame
        fw, fh = frame.surface.get_size()
        # Center the car on x position
        draw_x = int(self.x) - fw // 2
        draw_y = int(self.foot_y) - fh
        return pygame.Rect(draw_x, draw_y, fw, fh)

    def take_damage(self, amount: int) -> bool:
        """Apply damage. Returns True if this destroyed the car."""
        if self._state == _State.EXPLODING or not self.alive:
            return False

        self.hp -= amount
        self._damage_flash_timer = 0.1  # brief white flash

        if self.hp <= 0:
            self.hp = 0
            self._state = _State.EXPLODING
            self._explosion_timer = 0.0
            return True
        return False

    # ── update ────────────────────────────────────────────────────────────

    def update(self, dt: float):
        if not self.alive:
            return

        # Reset per-frame flag
        self.fired_this_frame = False

        # Damage flash timer
        if self._damage_flash_timer > 0:
            self._damage_flash_timer -= dt

        if self._state == _State.DRIVING:
            self._update_driving(dt)
        elif self._state == _State.ATTACKING:
            self._update_attacking(dt)
        elif self._state == _State.EXPLODING:
            self._update_exploding(dt)

        # Flash timer
        if self._show_flash:
            self._flash_timer -= dt
            if self._flash_timer <= 0:
                self._show_flash = False

    def _update_driving(self, dt: float):
        # Move right
        self.x += self.speed * dt

        # Wheel rotation animation
        self._wheel_rotation += dt * 8  # rotation speed
        self._frame_idx = int(self._wheel_rotation) % len(self._frames['driving'])

        # Check if reached target position
        if self.x >= self.target_x:
            self.x = self.target_x
            self._state = _State.ATTACKING
            self._frame_idx = 0
            self._frame_timer = 0.0
            self._attack_timer = 0.0
            self._attack_playing = False

    def _update_attacking(self, dt: float):
        if self._attack_playing:
            # Playing through attack animation
            self._frame_timer += dt
            frame_duration = 0.08  # fast attack animation

            if self._frame_timer >= frame_duration:
                self._frame_timer -= frame_duration
                self._frame_idx += 1

                # Trigger flash on fire frame
                if self._frame_idx == 1:
                    self._show_flash = True
                    self._flash_timer = MUZZLE_FLASH_DURATION
                    self.fired_this_frame = True

                # Animation finished?
                if self._frame_idx >= len(self._frames['idle']):
                    self._frame_idx = 0
                    self._attack_playing = False
                    self._attack_timer = 0.0
        else:
            # Cooldown between shots
            self._attack_timer += dt
            if self._attack_timer >= ARMORED_CAR_ATTACK_COOLDOWN:
                self._attack_playing = True
                self._frame_idx = 0
                self._frame_timer = 0.0

    def _update_exploding(self, dt: float):
        """Play explosion animation then mark dead."""
        self._explosion_timer += dt
        if self._explosion_timer >= self._explosion_duration:
            self.alive = False

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, time_ms: int):
        if not self.alive:
            return

        if self._state == _State.EXPLODING:
            self._draw_explosion(surface)
            return

        frame = self.current_frame
        fw, fh = frame.surface.get_size()

        # Position: center car on x, foot_y is the ground line
        draw_x = int(self.x) - fw // 2
        draw_y = int(self.foot_y) - fh

        # Ground shadow
        shadow_w = int(fw * 0.8)
        shadow_h = max(4, int(6 * self.scale))
        draw_ellipse_alpha(
            surface, (0, 0, 0, 40),
            pygame.Rect(draw_x + fw // 2 - shadow_w // 2,
                        int(self.foot_y) - shadow_h // 2,
                        shadow_w, shadow_h))

        # Sprite (with damage flash)
        if self._damage_flash_timer > 0:
            # Flash white on damage
            tmp = frame.surface.copy()
            white_overlay = pygame.Surface(tmp.get_size(), pygame.SRCALPHA)
            white_overlay.fill((255, 255, 255, 100))
            tmp.blit(white_overlay, (0, 0))
            surface.blit(tmp, (draw_x, draw_y))
        else:
            surface.blit(frame.surface, (draw_x, draw_y))

    def _draw_explosion(self, surface: pygame.Surface):
        """Draw the explosion animation."""
        progress = self._explosion_timer / self._explosion_duration

        # Draw the car fading out
        if progress < 0.5:
            frame = self.current_frame
            fw, fh = frame.surface.get_size()
            draw_x = int(self.x) - fw // 2
            draw_y = int(self.foot_y) - fh

            alpha = int(255 * (1.0 - progress * 2))
            tmp = frame.surface.copy()
            tmp.set_alpha(alpha)
            surface.blit(tmp, (draw_x, draw_y))

        # Draw explosion effect
        explosion_surf = get_explosion_frame(self.scale, progress)
        if explosion_surf:
            ew, eh = explosion_surf.get_size()
            # Center explosion on car
            draw_x = int(self.x) - ew // 2
            draw_y = int(self.foot_y) - eh // 2 - int(20 * self.scale)
            surface.blit(explosion_surf, (draw_x, draw_y))

    def draw_muzzle_flash(self, surface: pygame.Surface):
        """Draw muzzle flash separately (for proper layering)."""
        if not self._show_flash or self._state != _State.ATTACKING:
            return

        frame = self.current_frame
        fw, fh = frame.surface.get_size()
        draw_x = int(self.x) - fw // 2
        draw_y = int(self.foot_y) - fh

        # Muzzle position from frame
        mx = draw_x + frame.muzzle_x
        my = draw_y + frame.muzzle_y

        flash_r = max(4, int(10 * self.scale))

        # Outer glow
        glow_surf = pygame.Surface((flash_r * 6, flash_r * 6), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 240, 150, 80),
                           (flash_r * 3, flash_r * 3), flash_r * 3)
        surface.blit(glow_surf, (mx - flash_r * 3, my - flash_r * 3))

        # Inner bright core
        core_surf = pygame.Surface((flash_r * 4, flash_r * 4), pygame.SRCALPHA)
        pygame.draw.circle(core_surf, (255, 255, 220, 180),
                           (flash_r * 2, flash_r * 2), flash_r)
        surface.blit(core_surf, (mx - flash_r * 2, my - flash_r * 2))

        # White center
        pygame.draw.circle(surface, (255, 255, 255),
                           (mx, my), max(2, flash_r // 2))

    # ── health bar ────────────────────────────────────────────────────────

    def draw_health_bar(self, surface: pygame.Surface):
        """Draw a health bar above the armored car."""
        if self._state == _State.EXPLODING:
            return

        frame = self.current_frame
        fw = frame.surface.get_width()

        bar_width = int(fw * 0.8)
        bar_height = 6
        bar_x = int(self.x) - bar_width // 2
        bar_y = int(self.foot_y) - frame.surface.get_height() - 15

        # Background
        pygame.draw.rect(surface, (40, 40, 40),
                         pygame.Rect(bar_x - 1, bar_y - 1, bar_width + 2, bar_height + 2),
                         border_radius=2)

        # Empty bar
        pygame.draw.rect(surface, (80, 30, 30),
                         pygame.Rect(bar_x, bar_y, bar_width, bar_height),
                         border_radius=2)

        # Health fill
        hp_frac = self.hp / self.max_hp
        fill_width = int(bar_width * hp_frac)
        if fill_width > 0:
            # Color gradient based on health
            if hp_frac > 0.6:
                color = (80, 200, 80)
            elif hp_frac > 0.3:
                color = (220, 180, 50)
            else:
                color = (200, 50, 40)
            pygame.draw.rect(surface, color,
                             pygame.Rect(bar_x, bar_y, fill_width, bar_height),
                             border_radius=2)
