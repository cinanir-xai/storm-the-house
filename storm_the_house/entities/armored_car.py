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
    ARMORED_CAR_CRACK_COLOR, ARMORED_CAR_CRACK_SHADOW,
    ARMORED_CAR_SMOKE_INTERVAL,
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

        # Damage visuals
        self._damage_cracks: list[list[tuple[int, int]]] = []
        self._crack_seed: int = random.randint(1000, 9999)
        self._smoke_timer: float = 0.0

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
        self._add_damage_crack()

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

        # Smoke timer for damage
        if self._state != _State.EXPLODING:
            self._smoke_timer += dt

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

        # Sprite
        surface.blit(frame.surface, (draw_x, draw_y))

        # Damage cracks overlay
        self._draw_damage_cracks(surface, draw_x, draw_y)

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

    def _add_damage_crack(self):
        """Add a crack to the truck body based on current damage."""
        damage_frac = 1.0 - (self.hp / self.max_hp)
        if damage_frac <= 0:
            return

        rng = random.Random(self._crack_seed + len(self._damage_cracks) * 17)
        # Generate a short jagged crack line
        crack_len = int(12 + damage_frac * 18)
        num_segments = rng.randint(3, 5)
        start_x = rng.randint(-20, 20)
        start_y = rng.randint(-12, 8)
        points = [(start_x, start_y)]

        angle = rng.uniform(-0.6, 0.6)
        for _ in range(num_segments):
            angle += rng.uniform(-0.5, 0.5)
            nx = points[-1][0] + int(math.cos(angle) * crack_len / num_segments)
            ny = points[-1][1] + int(math.sin(angle) * crack_len / num_segments)
            points.append((nx, ny))

        self._damage_cracks.append(points)

    def _draw_damage_cracks(self, surface: pygame.Surface, draw_x: int, draw_y: int):
        """Draw cracks on the truck body to indicate damage."""
        if not self._damage_cracks:
            return

        frame = self.current_frame
        fw, fh = frame.surface.get_size()
        body_center_x = draw_x + fw // 2
        body_center_y = draw_y + fh // 2

        for crack in self._damage_cracks:
            if len(crack) < 2:
                continue
            # Shadow
            shadow_points = [(body_center_x + x + 1, body_center_y + y + 1) for x, y in crack]
            pygame.draw.lines(surface, ARMORED_CAR_CRACK_SHADOW, False, shadow_points, 2)
            # Main crack
            crack_points = [(body_center_x + x, body_center_y + y) for x, y in crack]
            pygame.draw.lines(surface, ARMORED_CAR_CRACK_COLOR, False, crack_points, 1)

    def should_emit_smoke(self) -> bool:
        """Return True when smoke should be emitted based on damage level."""
        if self._state == _State.EXPLODING:
            return False
        damage_frac = 1.0 - (self.hp / self.max_hp)
        if damage_frac < 0.3:
            return False
        return self._smoke_timer >= ARMORED_CAR_SMOKE_INTERVAL

    def reset_smoke_timer(self):
        """Reset smoke timer after emitting smoke."""
        self._smoke_timer = 0.0

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

