"""
Procedural sprite generator for the armored car enemy.

Generates the armored car with driver and gunner at a given scale.
All drawing is done with basic shapes — no external assets.

The car faces RIGHT (towards the house).
Sprite origin is at the bottom-center of the wheels.
"""

from __future__ import annotations

import math
from typing import NamedTuple
import pygame

from storm_the_house.core.settings import (
    ARMORED_CAR_BODY, ARMORED_CAR_BODY_DARK, ARMORED_CAR_BODY_LIGHT,
    ARMORED_CAR_WHEEL, ARMORED_CAR_WHEEL_RIM,
    ARMORED_CAR_WINDOW, ARMORED_CAR_WINDOW_SHINE,
    ARMORED_CAR_GUN_MOUNT, ARMORED_CAR_GUN_BARREL,
    ARMORED_CAR_HEADLIGHT, ARMORED_CAR_TAILLIGHT,
    ARMORED_CAR_DRIVER_SKIN, ARMORED_CAR_DRIVER_HELMET,
    ARMORED_CAR_GUNNER_SKIN, ARMORED_CAR_GUNNER_UNIFORM,
    MUZZLE_FLASH_COLOR, MUZZLE_FLASH_BRIGHT,
)


class ArmoredCarFrame(NamedTuple):
    """A single frame: surface + muzzle tip position + hitbox offset."""
    surface: pygame.Surface
    muzzle_x: int
    muzzle_y: int
    hitbox_offset_x: int
    hitbox_offset_y: int


# ── helpers ──────────────────────────────────────────────────────────────────

def _s(val: float, scale: float) -> int:
    """Scale and round a pixel value."""
    return max(1, int(val * scale))


# ── main sprite drawer ─────────────────────────────────────────────────────

def _draw_armored_car(
    scale: float,
    wheel_rotation: float = 0.0,
    gun_recoil: float = 0.0,
    gun_angle: float = -15.0,
    show_flash: bool = False,
) -> ArmoredCarFrame:
    """
    Draw the armored car sprite with driver and gunner.
    
    Parameters
    ----------
    scale : float
        Size multiplier for the sprite.
    wheel_rotation : float
        Rotation angle for wheel spokes (for driving animation).
    gun_recoil : float
        0..1 recoil amount for the machine gun.
    gun_angle : float
        Angle of the gun barrel in degrees (negative = pointing up/right).
    show_flash : bool
        Whether to show the muzzle flash.
    
    Returns
    -------
    ArmoredCarFrame
        The rendered frame with muzzle position info.
    """
    # ── dimensions ────────────────────────────────────────────────────
    car_length = _s(90, scale)
    car_height = _s(32, scale)
    cabin_height = _s(22, scale)
    wheel_radius = _s(10, scale)
    gun_length = _s(20, scale)
    
    # Total surface size (with room for gunner and muzzle flash)
    total_w = car_length + _s(30, scale)
    total_h = car_height + cabin_height + wheel_radius + _s(20, scale)
    
    surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    
    # Reference points
    car_left = _s(5, scale)
    car_bottom = total_h - _s(5, scale)
    car_top = car_bottom - car_height
    cabin_top = car_top - cabin_height
    
    wheel_y = car_bottom - wheel_radius // 2
    front_wheel_x = car_left + _s(18, scale)
    rear_wheel_x = car_left + car_length - _s(18, scale)
    
    # ── WHEELS ────────────────────────────────────────────────────────
    # Back wheel (drawn first, behind car)
    _draw_wheel(surf, rear_wheel_x, wheel_y, wheel_radius, wheel_rotation, scale)
    # Front wheel
    _draw_wheel(surf, front_wheel_x, wheel_y, wheel_radius, wheel_rotation, scale)
    
    # ── CAR BODY ──────────────────────────────────────────────────────
    # Main body (armored plating)
    body_rect = pygame.Rect(car_left, car_top, car_length, car_height)
    
    # Body base
    pygame.draw.rect(surf, ARMORED_CAR_BODY, body_rect, border_radius=3)
    
    # Highlight on top edge
    pygame.draw.line(surf, ARMORED_CAR_BODY_LIGHT,
                     (car_left + 3, car_top + 1),
                     (car_left + car_length - 3, car_top + 1), 2)
    
    # Shadow on bottom
    pygame.draw.line(surf, ARMORED_CAR_BODY_DARK,
                     (car_left + 3, car_top + car_height - 2),
                     (car_left + car_length - 3, car_top + car_height - 2), 2)
    
    # Armored plating details - vertical rivet lines
    for i in range(4):
        rx = car_left + _s(15 + i * 22, scale)
        pygame.draw.line(surf, ARMORED_CAR_BODY_DARK,
                         (rx, car_top + 4), (rx, car_top + car_height - 4), 1)
        # Rivets
        pygame.draw.circle(surf, ARMORED_CAR_BODY_LIGHT, (rx, car_top + 6), 1)
        pygame.draw.circle(surf, ARMORED_CAR_BODY_LIGHT, (rx, car_top + car_height - 6), 1)
    
    # ── CABIN / DRIVER COMPARTMENT ────────────────────────────────────
    cabin_left = car_left + _s(8, scale)
    cabin_width = _s(35, scale)
    cabin_rect = pygame.Rect(cabin_left, cabin_top, cabin_width, cabin_height + 2)
    
    # Cabin body
    pygame.draw.rect(surf, ARMORED_CAR_BODY_DARK, cabin_rect, border_radius=2)
    
    # Window
    win_w = _s(22, scale)
    win_h = _s(12, scale)
    win_x = cabin_left + (cabin_width - win_w) // 2
    win_y = cabin_top + _s(4, scale)
    win_rect = pygame.Rect(win_x, win_y, win_w, win_h)
    pygame.draw.rect(surf, ARMORED_CAR_WINDOW, win_rect, border_radius=2)
    
    # Window shine
    pygame.draw.line(surf, ARMORED_CAR_WINDOW_SHINE,
                     (win_x + 2, win_y + 2), (win_x + win_w - 4, win_y + 2), 1)
    
    # ── DRIVER (visible through window) ───────────────────────────────
    driver_cx = cabin_left + cabin_width // 2
    driver_cy = cabin_top + _s(10, scale)
    driver_r = _s(5, scale)
    # Helmet
    pygame.draw.circle(surf, ARMORED_CAR_DRIVER_HELMET, (driver_cx, driver_cy), driver_r)
    # Face (lower part visible)
    pygame.draw.circle(surf, ARMORED_CAR_DRIVER_SKIN,
                       (driver_cx + 1, driver_cy + driver_r // 2), driver_r // 2)
    
    # ── HEADLIGHT ─────────────────────────────────────────────────────
    headlight_x = car_left + car_length - _s(8, scale)
    headlight_y = car_top + car_height // 2
    pygame.draw.circle(surf, ARMORED_CAR_HEADLIGHT, (headlight_x, headlight_y), _s(4, scale))
    pygame.draw.circle(surf, (255, 255, 240), (headlight_x - 1, headlight_y - 1), _s(2, scale))
    
    # ── TAILLIGHT ─────────────────────────────────────────────────────
    taillight_x = car_left + _s(4, scale)
    taillight_y = car_top + car_height // 2
    pygame.draw.circle(surf, ARMORED_CAR_TAILLIGHT, (taillight_x, taillight_y), _s(3, scale))
    
    # ── GUN MOUNT (rear of car) ───────────────────────────────────────
    mount_x = car_left + _s(12, scale)
    mount_y = car_top - _s(2, scale)
    mount_w = _s(16, scale)
    mount_h = _s(8, scale)
    
    # Mount base
    mount_rect = pygame.Rect(mount_x, mount_y, mount_w, mount_h)
    pygame.draw.rect(surf, ARMORED_CAR_GUN_MOUNT, mount_rect, border_radius=2)
    
    # ── GUNNER ────────────────────────────────────────────────────────
    gunner_x = mount_x + mount_w // 2
    gunner_y = mount_y - _s(2, scale)
    
    # Body
    pygame.draw.ellipse(surf, ARMORED_CAR_GUNNER_UNIFORM,
                        pygame.Rect(gunner_x - _s(5, scale), gunner_y - _s(8, scale),
                                    _s(10, scale), _s(10, scale)))
    
    # Head/helmet
    pygame.draw.circle(surf, ARMORED_CAR_DRIVER_HELMET,
                       (gunner_x, gunner_y - _s(10, scale)), _s(4, scale))
    
    # Face
    pygame.draw.circle(surf, ARMORED_CAR_GUNNER_SKIN,
                       (gunner_x + 1, gunner_y - _s(9, scale)), _s(2, scale))
    
    # ── MACHINE GUN ───────────────────────────────────────────────────
    gun_base_x = gunner_x + _s(4, scale)
    gun_base_y = gunner_y - _s(4, scale)
    
    # Apply recoil
    recoil_offset = int(gun_recoil * _s(4, scale))
    
    # Gun angle
    angle_rad = math.radians(gun_angle)
    
    # Barrel end position
    barrel_end_x = gun_base_x + int(math.cos(angle_rad) * gun_length) - recoil_offset
    barrel_end_y = gun_base_y + int(math.sin(angle_rad) * gun_length)
    
    # Draw barrel
    barrel_thick = _s(4, scale)
    pygame.draw.line(surf, ARMORED_CAR_GUN_BARREL,
                     (gun_base_x - recoil_offset, gun_base_y),
                     (barrel_end_x, barrel_end_y), barrel_thick)
    
    # Barrel highlight
    pygame.draw.line(surf, (70, 75, 80),
                     (gun_base_x - recoil_offset, gun_base_y - 1),
                     (barrel_end_x, barrel_end_y - 1), max(1, barrel_thick // 2))
    
    # Barrel tip
    pygame.draw.circle(surf, (40, 42, 45), (barrel_end_x, barrel_end_y), _s(3, scale))
    
    # ── MUZZLE FLASH ──────────────────────────────────────────────────
    if show_flash:
        flash_r = _s(8, scale)
        # Outer glow
        flash_surf = pygame.Surface((flash_r * 6, flash_r * 6), pygame.SRCALPHA)
        pygame.draw.circle(flash_surf, (*MUZZLE_FLASH_COLOR, 100),
                           (flash_r * 3, flash_r * 3), flash_r * 3)
        surf.blit(flash_surf, (barrel_end_x - flash_r * 3, barrel_end_y - flash_r * 3))
        
        # Inner core
        core_surf = pygame.Surface((flash_r * 4, flash_r * 4), pygame.SRCALPHA)
        pygame.draw.circle(core_surf, (*MUZZLE_FLASH_BRIGHT, 200),
                           (flash_r * 2, flash_r * 2), flash_r)
        surf.blit(core_surf, (barrel_end_x - flash_r * 2, barrel_end_y - flash_r * 2))
        
        # White center
        pygame.draw.circle(surf, (255, 255, 255), (barrel_end_x, barrel_end_y), max(2, flash_r // 2))
    
    # ── SHADOW UNDER CAR ──────────────────────────────────────────────
    shadow_w = car_length - _s(10, scale)
    shadow_h = _s(6, scale)
    shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 50), shadow_surf.get_rect())
    surf.blit(shadow_surf, (car_left + _s(5, scale), car_bottom - _s(3, scale)))
    
    return ArmoredCarFrame(
        surface=surf,
        muzzle_x=barrel_end_x,
        muzzle_y=barrel_end_y,
        hitbox_offset_x=car_left,
        hitbox_offset_y=cabin_top,
    )


def _draw_wheel(surf: pygame.Surface, cx: int, cy: int, radius: int,
                rotation: float, scale: float):
    """Draw a single wheel with spokes."""
    # Tire
    pygame.draw.circle(surf, ARMORED_CAR_WHEEL, (cx, cy), radius)
    
    # Rim
    pygame.draw.circle(surf, ARMORED_CAR_WHEEL_RIM, (cx, cy), radius - max(1, _s(2, scale)))
    
    # Hub
    pygame.draw.circle(surf, ARMORED_CAR_WHEEL, (cx, cy), max(2, _s(3, scale)))
    
    # Spokes (rotate with wheel_rotation)
    num_spokes = 5
    for i in range(num_spokes):
        angle = rotation + (2 * math.pi * i / num_spokes)
        sx = cx + int(math.cos(angle) * (radius - _s(3, scale)))
        sy = cy + int(math.sin(angle) * (radius - _s(3, scale)))
        pygame.draw.line(surf, ARMORED_CAR_WHEEL, (cx, cy), (sx, sy), max(1, _s(2, scale)))


# ── public API ─────────────────────────────────────────────────────────────

# Cache for scaled sprites
_frame_cache: dict[tuple[float, float, float, bool], ArmoredCarFrame] = {}


def get_armored_car_frame(
    scale: float,
    wheel_rotation: float = 0.0,
    gun_recoil: float = 0.0,
    show_flash: bool = False,
) -> ArmoredCarFrame:
    """
    Get an armored car frame, using cache when possible.
    
    The cache key includes scale and visual state but not wheel_rotation
    for the base sprite - wheels are animated separately.
    """
    # Quantize scale for caching
    qs = round(scale * 20) / 20
    qr = round(gun_recoil * 10) / 10
    key = (qs, qr, show_flash, False)  # False = not exploding
    
    if key not in _frame_cache:
        _frame_cache[key] = _draw_armored_car(
            scale=qs,
            wheel_rotation=wheel_rotation,
            gun_recoil=qr,
            show_flash=show_flash,
        )
    
    return _frame_cache[key]


def generate_armored_car_frames(scale: float) -> dict[str, list[ArmoredCarFrame]]:
    """
    Generate all animation frames for the armored car at a given scale.
    
    Returns a dict with:
        - 'idle': frames when stationary and shooting
        - 'driving': frames when moving (wheel animation)
    """
    qs = round(scale * 20) / 20
    
    frames = {
        'idle': [],
        'driving': [],
    }
    
    # Idle frames (different gun recoil states)
    for i in range(4):
        recoil = 0.0
        flash = False
        if i == 1:
            recoil = 1.0
            flash = True
        elif i == 2:
            recoil = 0.5
        frames['idle'].append(_draw_armored_car(qs, 0.0, recoil, -15.0, flash))
    
    # Driving frames (wheel rotation)
    num_drive_frames = 8
    for i in range(num_drive_frames):
        rotation = (2 * math.pi * i) / num_drive_frames
        frames['driving'].append(_draw_armored_car(qs, rotation, 0.0, -10.0, False))
    
    return frames


def get_explosion_frame(scale: float, progress: float) -> pygame.Surface | None:
    """
    Generate an explosion frame at the given progress (0.0 to 1.0).
    
    Returns a surface with the explosion effect, or None if complete.
    """
    if progress >= 1.0:
        return None
    
    size = int(120 * scale)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    
    # Explosion expands over time
    max_radius = size // 2
    current_radius = int(max_radius * (0.3 + progress * 0.7))
    
    # Core color fades from white/yellow to orange/red
    alpha = int(255 * (1.0 - progress * 0.7))
    if progress < 0.3:
        core_color = (255, 255, 200, alpha)
    elif progress < 0.6:
        core_color = (255, 200, 100, alpha)
    else:
        core_color = (255, 150, 50, alpha)
    
    # Outer glow
    glow_alpha = int(150 * (1.0 - progress))
    pygame.draw.circle(surf, (255, 150, 50, glow_alpha), (cx, cy), current_radius)
    
    # Inner core
    inner_radius = int(current_radius * 0.6)
    pygame.draw.circle(surf, core_color, (cx, cy), inner_radius)
    
    # Bright center
    if progress < 0.5:
        center_radius = int(current_radius * 0.3)
        pygame.draw.circle(surf, (255, 255, 255, alpha), (cx, cy), center_radius)
    
    return surf
