"""
Enemy entity – a soldier that walks from the left towards the house,
then stops and shoots.

States
------
WALKING   – moving right towards the house.
ATTACKING – standing still, playing shoot animation in a loop.
DYING     – hit-points reached zero; fading out before removal.
"""

from __future__ import annotations

import enum
import random
import pygame

from storm_the_house.core.settings import (
    SCREEN_HEIGHT, HORIZON_Y_RATIO,
    ENEMY_SPEED_MIN, ENEMY_SPEED_MAX,
    ENEMY_STOP_DISTANCE,
    ENEMY_WALK_FRAME_DURATION, ENEMY_ATTACK_FRAME_DURATION,
    ENEMY_ATTACK_COOLDOWN,
    ENEMY_SPAWN_Y_MARGIN_TOP, ENEMY_SPAWN_Y_MARGIN_BOT,
    MUZZLE_FLASH_COLOR, MUZZLE_FLASH_BRIGHT, MUZZLE_FLASH_DURATION,
    ENEMY_HP, ENEMY_DEATH_FADE_TIME,
    ENEMY_SPEED_VARIANCE,
)
from storm_the_house.entities.enemy_sprites import (
    generate_walk_frames, generate_attack_frames, get_fire_frame_index,
    SpriteFrame,
)
from storm_the_house.utils.drawing import draw_ellipse_alpha


class _State(enum.Enum):
    WALKING = "walking"
    ATTACKING = "attacking"
    DYING = "dying"


# ── Sprite cache ─────────────────────────────────────────────────────────────
# Keyed by a rounded scale so we don't regenerate for every tiny variation.

_walk_cache: dict[float, list[pygame.Surface]] = {}
_attack_cache: dict[float, list[pygame.Surface]] = {}


def _quantise_scale(s: float) -> float:
    """Round scale to nearest 0.05 so we can cache frames."""
    return round(s * 20) / 20


def _get_walk_frames(scale: float) -> list[pygame.Surface]:
    qs = _quantise_scale(scale)
    if qs not in _walk_cache:
        _walk_cache[qs] = generate_walk_frames(qs)
    return _walk_cache[qs]


def _get_attack_frames(scale: float) -> list[pygame.Surface]:
    qs = _quantise_scale(scale)
    if qs not in _attack_cache:
        _attack_cache[qs] = generate_attack_frames(qs)
    return _attack_cache[qs]


# ── Enemy class ──────────────────────────────────────────────────────────────

class Enemy:
    """A single enemy soldier."""

    def __init__(self, house_left_x: int, speed_multiplier: float = 1.0):
        horizon_y = int(SCREEN_HEIGHT * HORIZON_Y_RATIO)
        ground_h = SCREEN_HEIGHT - horizon_y

        # Random y on the ground (with margins so they don't spawn at horizon
        # edge or very bottom)
        y_min = horizon_y + int(ground_h * ENEMY_SPAWN_Y_MARGIN_TOP)
        y_max = SCREEN_HEIGHT - int(ground_h * ENEMY_SPAWN_Y_MARGIN_BOT)
        self.foot_y = random.randint(y_min, y_max)

        # Depth factor: 0 at horizon, 1 at bottom of screen
        self.depth = (self.foot_y - horizon_y) / ground_h
        # Scale sprite by depth (further = smaller)
        self.scale = 0.55 + self.depth * 0.9

        # Speed also scales with depth (further = slower for parallax feel)
        base_speed = random.uniform(ENEMY_SPEED_MIN, ENEMY_SPEED_MAX)
        # Per-enemy random variance: ±10 %
        individual_variance = 1.0 + random.uniform(
            -ENEMY_SPEED_VARIANCE, ENEMY_SPEED_VARIANCE
        )
        # Apply depth factor, day-based multiplier, and individual variance
        self.speed = base_speed * (0.6 + self.depth * 0.6) * speed_multiplier * individual_variance

        # Spawn off-screen left
        self.x = random.uniform(-80, -30)

        # Where to stop (a bit before the house)
        stop_jitter = random.randint(-15, 15)
        self.stop_x = house_left_x - ENEMY_STOP_DISTANCE + stop_jitter

        # State
        self._state = _State.WALKING
        self.alive = True

        # Health
        self.hp: int = ENEMY_HP
        self.max_hp: int = ENEMY_HP
        self._death_timer: float = 0.0  # counts up during DYING state

        # Animation
        self._walk_frames = _get_walk_frames(self.scale)
        self._attack_frames = _get_attack_frames(self.scale)
        self._fire_frame_idx = get_fire_frame_index(len(self._attack_frames))

        self._frame_idx = random.randint(0, len(self._walk_frames) - 1)
        self._frame_timer = 0.0

        # Attack cooldown
        self._attack_timer = 0.0
        self._attack_playing = False

        # Muzzle flash
        self._flash_timer = 0.0
        self._show_flash = False

        # Set True on the frame the gun actually fires (consumed by manager)
        self.fired_this_frame: bool = False

    # ── properties ────────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def current_frame(self) -> SpriteFrame:
        if self._state == _State.WALKING:
            return self._walk_frames[self._frame_idx % len(self._walk_frames)]
        else:
            return self._attack_frames[self._frame_idx % len(self._attack_frames)]

    # ── hit detection / damage ─────────────────────────────────────────

    def get_hit_rect(self) -> pygame.Rect:
        """Return the screen-space bounding rect for hit-testing clicks."""
        frame = self.current_frame
        fw, fh = frame.surface.get_size()
        draw_x = int(self.x) - fw // 3
        draw_y = int(self.foot_y) - fh
        return pygame.Rect(draw_x, draw_y, fw, fh)

    def take_damage(self, amount: int) -> bool:
        """Apply *amount* damage.  Returns True if this killed the enemy."""
        if self._state == _State.DYING or not self.alive:
            return False
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self._state = _State.DYING
            self._death_timer = 0.0
            return True
        return False

    # ── update ────────────────────────────────────────────────────────────

    def update(self, dt: float):
        if not self.alive:
            return

        # Reset per-frame flag
        self.fired_this_frame = False

        if self._state == _State.WALKING:
            self._update_walking(dt)
        elif self._state == _State.ATTACKING:
            self._update_attacking(dt)
        elif self._state == _State.DYING:
            self._update_dying(dt)

        # Flash timer
        if self._show_flash:
            self._flash_timer -= dt
            if self._flash_timer <= 0:
                self._show_flash = False

    def _update_walking(self, dt: float):
        # Move right
        self.x += self.speed * dt

        # Advance walk animation
        self._frame_timer += dt
        if self._frame_timer >= ENEMY_WALK_FRAME_DURATION:
            self._frame_timer -= ENEMY_WALK_FRAME_DURATION
            self._frame_idx = (self._frame_idx + 1) % len(self._walk_frames)

        # Check if reached stop position
        if self.x >= self.stop_x:
            self.x = self.stop_x
            self._state = _State.ATTACKING
            self._frame_idx = 0
            self._frame_timer = 0.0
            self._attack_timer = 0.0
            self._attack_playing = False

    def _update_attacking(self, dt: float):
        if self._attack_playing:
            # Playing through attack animation
            self._frame_timer += dt
            if self._frame_timer >= ENEMY_ATTACK_FRAME_DURATION:
                self._frame_timer -= ENEMY_ATTACK_FRAME_DURATION
                self._frame_idx += 1

                # Trigger flash on fire frame
                if self._frame_idx == self._fire_frame_idx:
                    self._show_flash = True
                    self._flash_timer = MUZZLE_FLASH_DURATION
                    self.fired_this_frame = True

                # Animation finished?
                if self._frame_idx >= len(self._attack_frames):
                    self._frame_idx = 0
                    self._attack_playing = False
                    self._attack_timer = 0.0
        else:
            # Cooldown between shots
            self._attack_timer += dt
            if self._attack_timer >= ENEMY_ATTACK_COOLDOWN:
                self._attack_playing = True
                self._frame_idx = 0
                self._frame_timer = 0.0

    def _update_dying(self, dt: float):
        """Fade out and mark dead when timer expires."""
        self._death_timer += dt
        if self._death_timer >= ENEMY_DEATH_FADE_TIME:
            self.alive = False

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, time_ms: int):
        if not self.alive:
            return

        frame = self.current_frame
        fw, fh = frame.surface.get_size()

        # Position: x is left of sprite, foot_y is the ground line
        draw_x = int(self.x) - fw // 3   # anchor roughly at body center
        draw_y = int(self.foot_y) - fh

        # Compute alpha for dying fade-out
        if self._state == _State.DYING:
            fade = 1.0 - min(1.0, self._death_timer / ENEMY_DEATH_FADE_TIME)
            alpha = int(255 * fade)
        else:
            alpha = 255

        # Ground shadow
        shadow_alpha = max(0, int(30 * (alpha / 255)))
        shadow_w = int(fw * 0.7)
        shadow_h = max(3, int(4 * self.scale))
        draw_ellipse_alpha(
            surface, (0, 0, 0, shadow_alpha),
            pygame.Rect(draw_x + fw // 2 - shadow_w // 2,
                        int(self.foot_y) - shadow_h // 2,
                        shadow_w, shadow_h))

        # Sprite (with alpha for dying)
        if alpha < 255:
            tmp = frame.surface.copy()
            tmp.set_alpha(alpha)
            surface.blit(tmp, (draw_x, draw_y))
        else:
            surface.blit(frame.surface, (draw_x, draw_y))

        # Muzzle flash (don't show while dying)
        if self._show_flash and self._state != _State.DYING:
            self._draw_muzzle_flash(surface, frame, draw_x, draw_y)

    def _draw_muzzle_flash(self, surface: pygame.Surface,
                           frame: SpriteFrame,
                           draw_x: int, draw_y: int):
        """Draw a bright muzzle flash at the gun barrel tip."""
        mx = draw_x + frame.muzzle_x
        my = draw_y + frame.muzzle_y

        flash_r = max(3, int(6 * self.scale))

        # Outer glow
        glow_surf = pygame.Surface((flash_r * 6, flash_r * 6), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*MUZZLE_FLASH_COLOR, 80),
                           (flash_r * 3, flash_r * 3), flash_r * 3)
        surface.blit(glow_surf, (mx - flash_r * 3, my - flash_r * 3))

        # Inner bright core
        core_surf = pygame.Surface((flash_r * 4, flash_r * 4), pygame.SRCALPHA)
        pygame.draw.circle(core_surf, (*MUZZLE_FLASH_BRIGHT, 180),
                           (flash_r * 2, flash_r * 2), flash_r)
        surface.blit(core_surf, (mx - flash_r * 2, my - flash_r * 2))

        # Tiny white center
        pygame.draw.circle(surface, (255, 255, 255),
                           (mx, my), max(1, flash_r // 2))

        # Short horizontal flash line (barrel direction)
        line_len = int(flash_r * 2.5)
        flash_line = pygame.Surface((line_len, 3), pygame.SRCALPHA)
        flash_line.fill((*MUZZLE_FLASH_COLOR, 140))
        surface.blit(flash_line, (mx, my - 1))
