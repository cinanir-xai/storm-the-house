"""
Procedural sprite generator for the armored car enemy.

Generates a green military technical (pickup truck) with driver and gunner.
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
    ARMORED_CAR_GUN_MOUNT, ARMORED_CAR_GUN_BARREL,
    ARMORED_CAR_HEADLIGHT, ARMORED_CAR_TAILLIGHT,
    MUZZLE_FLASH_COLOR, MUZZLE_FLASH_BRIGHT,
    ENEMY_SKIN, ENEMY_SKIN_SHADOW, ENEMY_SHIRT, ENEMY_PANTS,
    ENEMY_HELMET, ENEMY_HELMET_SHADOW, ENEMY_GUN_METAL,
    ENEMY_GUN_DARK, ENEMY_GUN_WOOD,
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
    gun_angle: float = -12.0,
    show_flash: bool = False,
) -> ArmoredCarFrame:
    """
    Draw a military technical (pickup truck) with driver and gunner.

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
    truck_length = _s(105, scale)
    truck_height = _s(26, scale)
    cab_height = _s(18, scale)
    bed_height = _s(16, scale)
    wheel_radius = _s(10, scale)
    gun_length = _s(22, scale)

    # Total surface size (with room for gunner and muzzle flash)
    total_w = truck_length + _s(30, scale)
    total_h = truck_height + cab_height + wheel_radius + _s(24, scale)

    surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)

    # Reference points
    truck_left = _s(6, scale)
    truck_bottom = total_h - _s(6, scale)
    truck_top = truck_bottom - truck_height
    cab_top = truck_top - cab_height
    bed_top = truck_top - bed_height

    wheel_y = truck_bottom - wheel_radius // 2
    front_wheel_x = truck_left + _s(26, scale)
    rear_wheel_x = truck_left + truck_length - _s(28, scale)

    # ── WHEELS ────────────────────────────────────────────────────────
    _draw_wheel(surf, rear_wheel_x, wheel_y, wheel_radius, wheel_rotation, scale)
    _draw_wheel(surf, front_wheel_x, wheel_y, wheel_radius, wheel_rotation, scale)

    # ── CHASSIS / BODY ────────────────────────────────────────────────
    body_rect = pygame.Rect(truck_left, truck_top, truck_length, truck_height)
    pygame.draw.rect(surf, ARMORED_CAR_BODY, body_rect, border_radius=3)

    # Front hood slope
    hood_pts = [
        (truck_left + truck_length - _s(20, scale), truck_top),
        (truck_left + truck_length + _s(4, scale), truck_top + _s(6, scale)),
        (truck_left + truck_length + _s(4, scale), truck_top + truck_height - _s(2, scale)),
        (truck_left + truck_length - _s(20, scale), truck_top + truck_height),
    ]
    pygame.draw.polygon(surf, ARMORED_CAR_BODY, hood_pts)
    pygame.draw.polygon(surf, ARMORED_CAR_BODY_DARK, hood_pts, 2)

    # Body highlight and shadow
    pygame.draw.line(surf, ARMORED_CAR_BODY_LIGHT,
                     (truck_left + 4, truck_top + 1),
                     (truck_left + truck_length - 4, truck_top + 1), 2)
    pygame.draw.line(surf, ARMORED_CAR_BODY_DARK,
                     (truck_left + 4, truck_top + truck_height - 2),
                     (truck_left + truck_length - 6, truck_top + truck_height - 2), 2)

    # Door line
    door_x = truck_left + _s(40, scale)
    pygame.draw.line(surf, ARMORED_CAR_BODY_DARK,
                     (door_x, truck_top + 2), (door_x, truck_top + truck_height - 2), 1)
    pygame.draw.circle(surf, ARMORED_CAR_BODY_LIGHT,
                       (door_x + _s(6, scale), truck_top + truck_height // 2), 2)

    # ── CABIN (open top) ──────────────────────────────────────────────
    cab_left = truck_left + _s(40, scale)
    cab_width = _s(30, scale)
    cab_rect = pygame.Rect(cab_left, cab_top + _s(4, scale), cab_width, cab_height - _s(2, scale))
    pygame.draw.rect(surf, ARMORED_CAR_BODY_DARK, cab_rect, border_radius=2)

    # Windshield frame (open top, no glass)
    windshield_pts = [
        (cab_left + cab_width - _s(2, scale), cab_top + _s(6, scale)),
        (cab_left + cab_width + _s(8, scale), cab_top + _s(10, scale)),
        (cab_left + cab_width + _s(6, scale), cab_top + _s(16, scale)),
        (cab_left + cab_width - _s(2, scale), cab_top + _s(12, scale)),
    ]
    pygame.draw.polygon(surf, ARMORED_CAR_BODY_LIGHT, windshield_pts, 2)

    # Roll bar behind cab
    roll_x = cab_left - _s(6, scale)
    pygame.draw.line(surf, ARMORED_CAR_BODY_LIGHT,
                     (roll_x, cab_top + _s(4, scale)),
                     (roll_x, cab_top - _s(10, scale)), 2)
    pygame.draw.line(surf, ARMORED_CAR_BODY_LIGHT,
                     (roll_x, cab_top - _s(10, scale)),
                     (roll_x + _s(16, scale), cab_top - _s(10, scale)), 2)

    # ── DRIVER (open cab) ─────────────────────────────────────────────
    driver_cx = cab_left + _s(8, scale)
    driver_cy = cab_top + _s(8, scale)
    driver_r = _s(4, scale)
    # Torso
    pygame.draw.rect(surf, ENEMY_SHIRT,
                     pygame.Rect(driver_cx - _s(4, scale), driver_cy + _s(2, scale),
                                 _s(8, scale), _s(10, scale)))
    # Head
    pygame.draw.circle(surf, ENEMY_SKIN, (driver_cx, driver_cy), driver_r)
    pygame.draw.circle(surf, ENEMY_SKIN_SHADOW, (driver_cx + 1, driver_cy + 1), driver_r - 1)
    # Helmet
    pygame.draw.ellipse(surf, ENEMY_HELMET,
                        pygame.Rect(driver_cx - driver_r - 1, driver_cy - driver_r - 1,
                                    driver_r * 2 + 2, driver_r + _s(3, scale)))
    pygame.draw.ellipse(surf, ENEMY_HELMET_SHADOW,
                        pygame.Rect(driver_cx - driver_r + 1, driver_cy - driver_r + 1,
                                    driver_r * 2 - 2, driver_r))

    # ── BED / REAR PLATFORM ───────────────────────────────────────────
    bed_left = truck_left + _s(6, scale)
    bed_width = _s(38, scale)
    bed_rect = pygame.Rect(bed_left, bed_top + _s(6, scale), bed_width, bed_height)
    pygame.draw.rect(surf, ARMORED_CAR_BODY_DARK, bed_rect, border_radius=2)
    # Bed rails
    pygame.draw.line(surf, ARMORED_CAR_BODY_LIGHT,
                     (bed_left, bed_top + _s(6, scale)),
                     (bed_left + bed_width, bed_top + _s(6, scale)), 2)
    pygame.draw.line(surf, ARMORED_CAR_BODY_LIGHT,
                     (bed_left, bed_top + bed_height + _s(6, scale)),
                     (bed_left + bed_width, bed_top + bed_height + _s(6, scale)), 2)

    # ── GUN MOUNT (rear) ──────────────────────────────────────────────
    mount_x = bed_left + bed_width // 2 - _s(4, scale)
    mount_y = bed_top + _s(2, scale)
    mount_w = _s(10, scale)
    mount_h = _s(8, scale)
    mount_rect = pygame.Rect(mount_x, mount_y, mount_w, mount_h)
    pygame.draw.rect(surf, ARMORED_CAR_GUN_MOUNT, mount_rect, border_radius=2)
    pygame.draw.line(surf, ARMORED_CAR_GUN_MOUNT,
                     (mount_x + mount_w // 2, mount_y),
                     (mount_x + mount_w // 2, mount_y - _s(8, scale)), 2)

    # ── GUNNER ────────────────────────────────────────────────────────
    gunner_x = mount_x + mount_w // 2
    gunner_y = mount_y - _s(6, scale)

    # Body
    pygame.draw.rect(surf, ENEMY_SHIRT,
                     pygame.Rect(gunner_x - _s(4, scale), gunner_y, _s(8, scale), _s(10, scale)))
    pygame.draw.rect(surf, ENEMY_PANTS,
                     pygame.Rect(gunner_x - _s(3, scale), gunner_y + _s(9, scale), _s(6, scale), _s(6, scale)))

    # Head
    pygame.draw.circle(surf, ENEMY_SKIN, (gunner_x, gunner_y - _s(2, scale)), _s(4, scale))
    pygame.draw.circle(surf, ENEMY_SKIN_SHADOW, (gunner_x + 1, gunner_y - 1), _s(3, scale))
    # Helmet
    pygame.draw.ellipse(surf, ENEMY_HELMET,
                        pygame.Rect(gunner_x - _s(5, scale), gunner_y - _s(7, scale),
                                    _s(10, scale), _s(6, scale)))

    # ── MACHINE GUN ───────────────────────────────────────────────────
    gun_base_x = gunner_x + _s(4, scale)
    gun_base_y = gunner_y - _s(4, scale)
    recoil_offset = int(gun_recoil * _s(4, scale))
    angle_rad = math.radians(gun_angle)

    barrel_end_x = gun_base_x + int(math.cos(angle_rad) * gun_length) - recoil_offset
    barrel_end_y = gun_base_y + int(math.sin(angle_rad) * gun_length)

    barrel_thick = _s(3, scale)
    pygame.draw.line(surf, ENEMY_GUN_METAL,
                     (gun_base_x - recoil_offset, gun_base_y),
                     (barrel_end_x, barrel_end_y), barrel_thick)
    pygame.draw.line(surf, ENEMY_GUN_DARK,
                     (gun_base_x - recoil_offset, gun_base_y + 1),
                     (barrel_end_x, barrel_end_y + 1), max(1, barrel_thick - 1))

    # Receiver and stock
    receiver_rect = pygame.Rect(gun_base_x - _s(6, scale), gun_base_y - _s(2, scale),
                                _s(8, scale), _s(4, scale))
    pygame.draw.rect(surf, ENEMY_GUN_METAL, receiver_rect)
    pygame.draw.rect(surf, ENEMY_GUN_WOOD,
                     pygame.Rect(gun_base_x - _s(8, scale), gun_base_y - _s(1, scale),
                                 _s(4, scale), _s(3, scale)))

    # Ammo box
    ammo_rect = pygame.Rect(gun_base_x - _s(3, scale), gun_base_y + _s(3, scale),
                            _s(6, scale), _s(4, scale))
    pygame.draw.rect(surf, ENEMY_GUN_DARK, ammo_rect)

    # Barrel tip
    pygame.draw.circle(surf, ENEMY_GUN_DARK, (barrel_end_x, barrel_end_y), _s(2, scale))

    # ── MUZZLE FLASH ──────────────────────────────────────────────────
    if show_flash:
        flash_r = _s(7, scale)
        flash_surf = pygame.Surface((flash_r * 6, flash_r * 6), pygame.SRCALPHA)
        pygame.draw.circle(flash_surf, (*MUZZLE_FLASH_COLOR, 100),
                           (flash_r * 3, flash_r * 3), flash_r * 3)
        surf.blit(flash_surf, (barrel_end_x - flash_r * 3, barrel_end_y - flash_r * 3))

        core_surf = pygame.Surface((flash_r * 4, flash_r * 4), pygame.SRCALPHA)
        pygame.draw.circle(core_surf, (*MUZZLE_FLASH_BRIGHT, 200),
                           (flash_r * 2, flash_r * 2), flash_r)
        surf.blit(core_surf, (barrel_end_x - flash_r * 2, barrel_end_y - flash_r * 2))

        pygame.draw.circle(surf, (255, 255, 255), (barrel_end_x, barrel_end_y), max(2, flash_r // 2))

    # ── LIGHTS ─────────────────────────────────────────────────────────
    headlight_x = truck_left + truck_length + _s(2, scale)
    headlight_y = truck_top + truck_height // 2
    pygame.draw.circle(surf, ARMORED_CAR_HEADLIGHT, (headlight_x, headlight_y), _s(4, scale))
    pygame.draw.circle(surf, (255, 255, 240), (headlight_x - 1, headlight_y - 1), _s(2, scale))

    taillight_x = truck_left + _s(4, scale)
    taillight_y = truck_top + truck_height // 2
    pygame.draw.circle(surf, ARMORED_CAR_TAILLIGHT, (taillight_x, taillight_y), _s(3, scale))

    # ── SHADOW UNDER TRUCK ─────────────────────────────────────────────
    shadow_w = truck_length - _s(8, scale)
    shadow_h = _s(6, scale)
    shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 50), shadow_surf.get_rect())
    surf.blit(shadow_surf, (truck_left + _s(5, scale), truck_bottom - _s(3, scale)))

    return ArmoredCarFrame(
        surface=surf,
        muzzle_x=barrel_end_x,
        muzzle_y=barrel_end_y,
        hitbox_offset_x=truck_left,
        hitbox_offset_y=cab_top,
    )


def _draw_wheel(surf: pygame.Surface, cx: int, cy: int, radius: int,
                rotation: float, scale: float):
    """Draw a single wheel with spokes."""
    pygame.draw.circle(surf, ARMORED_CAR_WHEEL, (cx, cy), radius)
    pygame.draw.circle(surf, ARMORED_CAR_WHEEL_RIM, (cx, cy), radius - max(1, _s(2, scale)))
    pygame.draw.circle(surf, ARMORED_CAR_WHEEL, (cx, cy), max(2, _s(3, scale)))

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
    qs = round(scale * 20) / 20
    qr = round(gun_recoil * 10) / 10
    key = (qs, qr, show_flash, False)

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
        frames['idle'].append(_draw_armored_car(qs, 0.0, recoil, -12.0, flash))

    # Driving frames (wheel rotation)
    num_drive_frames = 8
    for i in range(num_drive_frames):
        rotation = (2 * math.pi * i) / num_drive_frames
        frames['driving'].append(_draw_armored_car(qs, rotation, 0.0, -8.0, False))

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

    glow_alpha = int(150 * (1.0 - progress))
    pygame.draw.circle(surf, (255, 150, 50, glow_alpha), (cx, cy), current_radius)

    inner_radius = int(current_radius * 0.6)
    pygame.draw.circle(surf, core_color, (cx, cy), inner_radius)

    if progress < 0.5:
        center_radius = int(current_radius * 0.3)
        pygame.draw.circle(surf, (255, 255, 255, alpha), (cx, cy), center_radius)

    return surf
