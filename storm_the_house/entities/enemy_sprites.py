"""
Procedural sprite generator for enemy soldiers.

Generates walk-cycle and attack animation frames at a given scale.
All drawing is done with basic shapes — no external assets.

The soldier faces RIGHT (towards the house).
Sprite origin is at the bottom-center of the feet.
"""

from __future__ import annotations

import math
from typing import NamedTuple
import pygame

from storm_the_house.core.settings import (
    ENEMY_SKIN, ENEMY_SKIN_SHADOW,
    ENEMY_SHIRT, ENEMY_SHIRT_SHADOW,
    ENEMY_PANTS, ENEMY_PANTS_SHADOW,
    ENEMY_BOOTS,
    ENEMY_GUN_METAL, ENEMY_GUN_DARK, ENEMY_GUN_WOOD,
    ENEMY_HELMET, ENEMY_HELMET_SHADOW,
)


class SpriteFrame(NamedTuple):
    """A single animation frame: surface + muzzle tip position."""
    surface: pygame.Surface
    muzzle_x: int
    muzzle_y: int


# ── helpers ──────────────────────────────────────────────────────────────────

def _s(val: float, scale: float) -> int:
    """Scale and round a pixel value."""
    return max(1, int(val * scale))


# ── single-frame drawer ─────────────────────────────────────────────────────

def _draw_soldier_frame(
    scale: float,
    leg_phase: float,       # 0..1 walk cycle phase  (0 = neutral)
    arm_offset: float,      # vertical arm bob (px, pre-scale)
    gun_angle: float,       # gun tilt in degrees (0 = horizontal)
    recoil: float,          # 0..1 recoil amount for attack
    head_offset: tuple[int, int] = (0, 0),
    torso_offset: tuple[int, int] = (0, 0),
    tilt: float = 0.0,
) -> SpriteFrame:
    """
    Draw one frame of a soldier sprite and return the Surface.

    The soldier is drawn facing right.  Coordinate system:
        (0, 0) is top-left of the surface.
        The bottom-center is the "foot" anchor.
    """
    # ── dimensions ────────────────────────────────────────────────────
    body_h = _s(16, scale)       # torso height
    head_r = _s(5, scale)        # head radius
    leg_len = _s(10, scale)      # upper+lower leg total
    arm_len = _s(10, scale)
    boot_h = _s(3, scale)
    helmet_h = _s(4, scale)

    total_h = head_r * 2 + helmet_h + body_h + leg_len + boot_h + _s(4, scale)
    total_w = _s(30, scale)      # enough room for gun + body

    surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)

    # Reference points
    cx = total_w // 2 - _s(2, scale)   # body center x (shifted left a bit)
    foot_y = total_h - _s(2, scale)
    hip_y = foot_y - leg_len - boot_h
    shoulder_y = hip_y - body_h
    neck_y = shoulder_y - _s(1, scale)
    head_cy = neck_y - head_r

    # Apply torso/head offsets for death poses
    hip_y += torso_offset[1]
    shoulder_y += torso_offset[1]
    neck_y += torso_offset[1] + head_offset[1]
    head_cy += torso_offset[1] + head_offset[1]
    cx += torso_offset[0]

    # ── LEGS (two legs, with walk cycle) ──────────────────────────────
    leg_spread = math.sin(leg_phase * math.pi * 2) * _s(5, scale)
    leg_back_spread = -leg_spread

    tilt_rad = math.radians(tilt)
    tilt_dx = int(math.cos(tilt_rad) * _s(3, scale))
    tilt_dy = int(math.sin(tilt_rad) * _s(3, scale))

    # Leg thickness
    lt = max(2, _s(3, scale))

    # Back leg (drawn first, behind body)
    knee_back_x = cx + int(leg_back_spread * 0.5)
    knee_back_y = hip_y + leg_len // 2
    foot_back_x = cx + int(leg_back_spread)
    foot_back_y = foot_y
    pygame.draw.line(surf, ENEMY_PANTS_SHADOW,
                     (cx, hip_y), (knee_back_x, knee_back_y), lt)
    pygame.draw.line(surf, ENEMY_PANTS_SHADOW,
                     (knee_back_x, knee_back_y),
                     (foot_back_x, foot_back_y), lt)
    # Boot (back)
    pygame.draw.rect(surf, ENEMY_BOOTS,
                     pygame.Rect(foot_back_x - lt // 2, foot_back_y - boot_h,
                                 lt + _s(2, scale), boot_h))

    # ── TORSO ─────────────────────────────────────────────────────────
    torso_w = _s(8, scale)
    torso_rect = pygame.Rect(cx - torso_w // 2, shoulder_y, torso_w, body_h)
    pygame.draw.rect(surf, ENEMY_SHIRT, torso_rect)
    # Shadow on right side of torso
    shadow_rect = pygame.Rect(cx, shoulder_y, torso_w // 2, body_h)
    pygame.draw.rect(surf, ENEMY_SHIRT_SHADOW, shadow_rect)
    # Belt
    belt_y = hip_y - _s(2, scale)
    pygame.draw.rect(surf, (50, 45, 35),
                     pygame.Rect(cx - torso_w // 2 - 1, belt_y,
                                 torso_w + 2, _s(2, scale)))

    # ── FRONT LEG ─────────────────────────────────────────────────────
    knee_front_x = cx + int(leg_spread * 0.5)
    knee_front_y = hip_y + leg_len // 2
    foot_front_x = cx + int(leg_spread)
    foot_front_y = foot_y
    pygame.draw.line(surf, ENEMY_PANTS,
                     (cx, hip_y), (knee_front_x, knee_front_y), lt)
    pygame.draw.line(surf, ENEMY_PANTS,
                     (knee_front_x, knee_front_y),
                     (foot_front_x, foot_front_y), lt)
    # Boot (front)
    pygame.draw.rect(surf, ENEMY_BOOTS,
                     pygame.Rect(foot_front_x - lt // 2, foot_front_y - boot_h,
                                 lt + _s(2, scale), boot_h))

    # ── ARM + GUN ─────────────────────────────────────────────────────
    arm_y = shoulder_y + _s(3, scale) + int(arm_offset * scale)
    arm_thick = max(2, _s(2.5, scale))

    # Gun
    gun_len = _s(14, scale)
    gun_thick = max(2, _s(2.5, scale))
    stock_len = _s(5, scale)

    gun_angle_rad = math.radians(gun_angle)
    recoil_px = int(recoil * _s(3, scale))

    hand_x = cx + torso_w // 2 + _s(1, scale)
    hand_y = arm_y + _s(4, scale)

    # Barrel end
    barrel_end_x = hand_x + int(math.cos(gun_angle_rad) * gun_len) - recoil_px
    barrel_end_y = hand_y + int(math.sin(gun_angle_rad) * gun_len)

    # Stock end (behind hand)
    stock_end_x = hand_x - int(math.cos(gun_angle_rad) * stock_len) - recoil_px
    stock_end_y = hand_y - int(math.sin(gun_angle_rad) * stock_len)

    # Draw stock (wood)
    pygame.draw.line(surf, ENEMY_GUN_WOOD,
                     (hand_x - recoil_px, hand_y),
                     (stock_end_x, stock_end_y),
                     gun_thick + 1)

    # Draw barrel (metal)
    pygame.draw.line(surf, ENEMY_GUN_METAL,
                     (hand_x - recoil_px, hand_y),
                     (barrel_end_x, barrel_end_y),
                     gun_thick)
    # Dark underside of barrel
    pygame.draw.line(surf, ENEMY_GUN_DARK,
                     (hand_x - recoil_px, hand_y + 1),
                     (barrel_end_x, barrel_end_y + 1),
                     max(1, gun_thick - 1))

    # Back arm (behind torso, just a short stub visible)
    back_arm_x = cx - torso_w // 2
    pygame.draw.line(surf, ENEMY_SKIN_SHADOW,
                     (back_arm_x, arm_y),
                     (back_arm_x - _s(2, scale),
                      arm_y + _s(5, scale) + int(arm_offset * scale * 0.5)),
                     arm_thick)

    # Front arm (holding gun)
    pygame.draw.line(surf, ENEMY_SKIN,
                     (hand_x - _s(1, scale), shoulder_y + _s(2, scale)),
                     (hand_x - recoil_px, hand_y),
                     arm_thick)
    # Hand circle
    pygame.draw.circle(surf, ENEMY_SKIN,
                       (hand_x - recoil_px, hand_y),
                       max(1, _s(2, scale)))

    # ── HEAD ──────────────────────────────────────────────────────────
    # Neck
    pygame.draw.line(surf, ENEMY_SKIN,
                     (cx, shoulder_y), (cx, neck_y), max(2, _s(2, scale)))

    head_dx = int(math.sin(tilt_rad) * _s(6, scale))
    head_dy = int(math.cos(tilt_rad) * _s(2, scale))

    # Head circle
    pygame.draw.circle(surf, ENEMY_SKIN, (cx + head_dx, head_cy + head_dy), head_r)
    # Shadow on right side of face
    pygame.draw.circle(surf, ENEMY_SKIN_SHADOW,
                       (cx + head_dx + head_r // 3, head_cy + head_dy), head_r - 1)
    # Re-draw left highlight
    pygame.draw.circle(surf, ENEMY_SKIN,
                       (cx + head_dx - head_r // 4, head_cy + head_dy - head_r // 4),
                       head_r // 2)

    # Eye (simple dot)
    eye_x = cx + head_dx + head_r // 2
    eye_y = head_cy + head_dy - _s(1, scale)
    pygame.draw.circle(surf, (30, 30, 30), (eye_x, eye_y), max(1, _s(1, scale)))

    # ── HELMET ────────────────────────────────────────────────────────
    helmet_w = head_r * 2 + _s(3, scale)
    helmet_top = head_cy + head_dy - head_r - _s(1, scale)
    # Main dome
    pygame.draw.ellipse(surf, ENEMY_HELMET,
                        pygame.Rect(cx + head_dx - helmet_w // 2, helmet_top,
                                    helmet_w, head_r + helmet_h))
    # Brim
    brim_y = head_cy + head_dy - head_r // 2
    pygame.draw.line(surf, ENEMY_HELMET,
                     (cx + head_dx - helmet_w // 2 - _s(1, scale), brim_y),
                     (cx + head_dx + helmet_w // 2 + _s(2, scale), brim_y),
                     max(2, _s(2, scale)))
    # Helmet shadow
    pygame.draw.ellipse(surf, ENEMY_HELMET_SHADOW,
                        pygame.Rect(cx + head_dx - helmet_w // 2 + 2,
                                    helmet_top + helmet_h // 2,
                                    helmet_w - 2, head_r))

    return SpriteFrame(surface=surf, muzzle_x=barrel_end_x, muzzle_y=barrel_end_y)


# ── public API: generate full animation sets ─────────────────────────────────

def generate_walk_frames(scale: float, num_frames: int = 8) -> list[SpriteFrame]:
    """
    Generate *num_frames* of a walk cycle at the given *scale*.

    Returns a list of SpriteFrame named tuples.
    """
    frames = []
    for i in range(num_frames):
        phase = i / num_frames              # 0 .. ~1
        arm_bob = math.sin(phase * math.pi * 2) * 1.5
        frames.append(_draw_soldier_frame(
            scale=scale,
            leg_phase=phase,
            arm_offset=arm_bob,
            gun_angle=-5 + math.sin(phase * math.pi * 2) * 3,  # slight bob
            recoil=0.0,
        ))
    return frames


def generate_attack_frames(scale: float, num_frames: int = 6) -> list[SpriteFrame]:
    """
    Generate *num_frames* of a shooting / attack animation.

    Frame 0-1: aim, Frame 2: fire (recoil), Frame 3-5: recover.
    """
    frames = []
    for i in range(num_frames):
        t = i / max(num_frames - 1, 1)
        if t < 0.33:
            # Aiming — gun rises slightly
            gun_angle = -5 - t * 10
            recoil = 0.0
            arm_off = -1
        elif t < 0.5:
            # Fire!
            gun_angle = -8
            recoil = 1.0
            arm_off = 1
        else:
            # Recover
            recover = (t - 0.5) / 0.5
            gun_angle = -8 + recover * 3
            recoil = max(0.0, 1.0 - recover * 2)
            arm_off = 1 - recover
        frames.append(_draw_soldier_frame(
            scale=scale,
            leg_phase=0.0,          # standing still
            arm_offset=arm_off,
            gun_angle=gun_angle,
            recoil=recoil,
        ))
    return frames


def generate_death_frames(scale: float) -> dict[str, list[SpriteFrame]]:
    """Generate multiple death animation variations, all ending flat on ground."""
    variants: dict[str, list[SpriteFrame]] = {}

    # Faceplant: falls forward, ends flat face-down
    frames = []
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        frames.append(_draw_soldier_frame(
            scale=scale,
            leg_phase=0.2 + t * 0.5,
            arm_offset=2 + t * 10,
            gun_angle=-10 - t * 30,
            recoil=0.5 + t * 0.8,
            head_offset=(int(3 * t * scale), int(12 * t * scale)),
            torso_offset=(0, int(14 * t * scale)),
            tilt=-70 * t,  # ends nearly horizontal
        ))
    variants["faceplant"] = frames

    # Kneel then fall forward: kneels first, then topples face-down
    frames = []
    for t in [0.0, 0.3, 0.55, 0.8, 1.0]:
        # First part: kneel (small drop), second part: fall forward
        if t < 0.4:
            kneel_t = t / 0.4
            fall_t = 0.0
        else:
            kneel_t = 1.0
            fall_t = (t - 0.4) / 0.6
        frames.append(_draw_soldier_frame(
            scale=scale,
            leg_phase=0.05 + kneel_t * 0.2,
            arm_offset=3 + fall_t * 8,
            gun_angle=-5 - fall_t * 25,
            recoil=0.4 + fall_t * 0.7,
            head_offset=(int(2 * fall_t * scale), int(4 * kneel_t * scale + 10 * fall_t * scale)),
            torso_offset=(0, int(5 * kneel_t * scale + 12 * fall_t * scale)),
            tilt=-55 * fall_t,
        ))
    variants["kneel_fall"] = frames

    # Sit fall: falls backward onto butt, then lies flat on back
    frames = []
    for t in [0.0, 0.3, 0.55, 0.8, 1.0]:
        if t < 0.35:
            sit_t = t / 0.35
            lie_t = 0.0
        else:
            sit_t = 1.0
            lie_t = (t - 0.35) / 0.65
        frames.append(_draw_soldier_frame(
            scale=scale,
            leg_phase=-0.2 + sit_t * 0.3,
            arm_offset=4 + lie_t * 6,
            gun_angle=-3 - lie_t * 15,
            recoil=0.5 + lie_t * 0.6,
            head_offset=(int(-2 * lie_t * scale), int(3 * sit_t * scale + 10 * lie_t * scale)),
            torso_offset=(0, int(4 * sit_t * scale + 12 * lie_t * scale)),
            tilt=60 * lie_t,  # falls backward (positive tilt)
        ))
    variants["sit_fall"] = frames

    # Kneel back: kneels then falls backward onto back
    frames = []
    for t in [0.0, 0.35, 0.6, 0.85, 1.0]:
        if t < 0.4:
            kneel_t = t / 0.4
            fall_t = 0.0
        else:
            kneel_t = 1.0
            fall_t = (t - 0.4) / 0.6
        frames.append(_draw_soldier_frame(
            scale=scale,
            leg_phase=0.05 + kneel_t * 0.25,
            arm_offset=3 + fall_t * 7,
            gun_angle=-6 - fall_t * 20,
            recoil=0.5 + fall_t * 0.6,
            head_offset=(int(-3 * fall_t * scale), int(4 * kneel_t * scale + 11 * fall_t * scale)),
            torso_offset=(0, int(6 * kneel_t * scale + 13 * fall_t * scale)),
            tilt=55 * fall_t,  # falls backward
        ))
    variants["kneel_back"] = frames

    return variants


def get_fire_frame_index(num_frames: int = 6) -> int:
    """Return the frame index at which the gun actually fires (for flash)."""
    # Frame at ~33% is the fire frame
    return max(1, int(num_frames * 0.33))
