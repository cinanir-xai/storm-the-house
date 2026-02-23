"""
Hired help system – manages repairman healing and gunman auto-shooting.

The HiredHelp object is created fresh each day in GameScene but reads
its counts from the persistent UpgradeState.
"""

from __future__ import annotations

import math
import pygame

from storm_the_house.core.settings import (
    REPAIRMAN_HEAL_INTERVAL, REPAIRMAN_HEAL_PER_MAN,
    REPAIRMAN_MAX_VISIBLE, REPAIRMAN_UNIQUE_SPOTS,
    GUNMAN_MAX_VISIBLE, GUNMAN_UNIQUE_SPOTS,
    MONEY_PER_KILL,
)
from storm_the_house.entities.upgrades import UpgradeState


# ── Repairman / gunman position definitions ──────────────────────────────
# Each spot: (x_offset_from_house_x, y_offset_from_house_y, pose_type)
# x/y offsets are fractions of house width/height.

# Repairman unique spots (relative to house rect)
_REPAIRMAN_SPOTS = [
    # (x_frac, y_frac, pose): pose = "roof_hammer", "roof_saw", "window",
    #   "front_hammer", "front_kneel", "side_stand"
    (0.25, -0.22, "roof_hammer"),     # on roof, left side
    (0.65, -0.18, "roof_saw"),        # on roof, right side
    (0.15, 0.20, "window_fix"),       # fixing left upper window
    (0.55, 0.55, "window_fix"),       # fixing right lower window
    (0.35, 0.85, "front_hammer"),     # in front of house, hammering
    (-0.10, 0.75, "front_kneel"),     # kneeling in front, left side
]

# Gunman unique spots
_GUNMAN_SPOTS = [
    # (x_frac, y_frac, pose): "kneel_front", "window_aim", "roof_prone",
    #   "roof_crouch", "side_stand"
    (0.10, 0.85, "kneel_front"),      # kneeling in front, left
    (0.60, 0.20, "window_aim"),       # aiming from upper right window
    (0.20, 0.55, "window_aim"),       # aiming from lower left window
    (0.40, -0.25, "roof_prone"),      # lying on roof
    (0.70, -0.15, "roof_crouch"),     # crouching on roof
    (-0.15, 0.60, "kneel_front"),     # kneeling further left
]


class HiredHelp:
    """Manages repair and gunman timers and their visual representations."""

    def __init__(self, upgrades: UpgradeState):
        self._upgrades = upgrades

        # Repair timer
        self._repair_timer: float = 0.0

        # Gunman timer
        self._gunman_timer: float = 0.0

        # Muzzle flash tracking for gunman shots
        self._gunman_flash_timer: float = 0.0
        self._gunman_flash_pos: tuple[int, int] | None = None

        # Animation timer for tool bobbing
        self._anim_timer: float = 0.0

    # ── update ────────────────────────────────────────────────────────

    def update(self, dt: float, house, enemies: list, money_ref: list[int]):
        """Tick repair and gunman timers.

        Parameters
        ----------
        house : House
            The player's house (for healing).
        enemies : list[Enemy]
            Active enemy list (for gunman targeting).
        money_ref : list[int]
            Single-element list ``[money]`` so we can mutate the caller's money.
        """
        self._anim_timer += dt

        # ── repairman healing ──────────────────────────────────────────
        if self._upgrades.repairman_count > 0:
            self._repair_timer += dt
            if self._repair_timer >= REPAIRMAN_HEAL_INTERVAL:
                self._repair_timer -= REPAIRMAN_HEAL_INTERVAL
                heal_amount = self._upgrades.repairman_count * REPAIRMAN_HEAL_PER_MAN
                house.hp = min(house.max_hp, house.hp + heal_amount)

        # ── gunman auto-shooting ───────────────────────────────────────
        if self._upgrades.gunman_count > 0 and enemies:
            fire_interval = self._upgrades.gunman_fire_interval
            self._gunman_timer += dt
            if self._gunman_timer >= fire_interval:
                self._gunman_timer -= fire_interval
                self._gunman_shoot(house, enemies, money_ref)

        # Flash timer
        if self._gunman_flash_timer > 0:
            self._gunman_flash_timer -= dt

    def _gunman_shoot(self, house, enemies: list, money_ref: list[int]):
        """Find the closest alive enemy and instantly kill it."""
        # Find closest living enemy to the house
        house_cx = house.x + house.width // 2
        house_cy = house.y + house.height // 2

        closest = None
        closest_dist = float("inf")
        for e in enemies:
            if not e.alive or e.state == "dying":
                continue
            dist = abs(e.x - house_cx)
            if dist < closest_dist:
                closest_dist = dist
                closest = e

        if closest is None:
            return

        # Instantly kill the enemy
        closest.take_damage(closest.hp)
        money_ref[0] += MONEY_PER_KILL

        # Set muzzle flash at the enemy's position
        rect = closest.get_hit_rect()
        self._gunman_flash_pos = (rect.centerx, rect.centery)
        self._gunman_flash_timer = 0.15

    # ── drawing ────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, house, time_ms: int):
        """Draw repairmen and gunmen on/around the house."""
        self._draw_repairmen(surface, house, time_ms)
        self._draw_gunmen(surface, house, time_ms)
        self._draw_gunman_flash(surface)

    def _draw_repairmen(self, surface: pygame.Surface, house, time_ms: int):
        count = self._upgrades.repairman_count
        if count <= 0:
            return

        visible = min(count, REPAIRMAN_MAX_VISIBLE)
        hx, hy, hw, hh = house.x, house.y, house.width, house.height

        for i in range(visible):
            if i < REPAIRMAN_UNIQUE_SPOTS and i < len(_REPAIRMAN_SPOTS):
                xf, yf, pose = _REPAIRMAN_SPOTS[i]
                px = hx + int(hw * xf)
                py = hy + int(hh * yf)
                self._draw_repairman_sprite(surface, px, py, pose, i, time_ms)
            else:
                # Extra repairmen standing on the left side of the house
                extra_idx = i - min(REPAIRMAN_UNIQUE_SPOTS, len(_REPAIRMAN_SPOTS))
                px = hx - 20 - extra_idx * 14
                py = hy + hh - 5
                self._draw_repairman_sprite(surface, px, py, "side_stand", i, time_ms)

    def _draw_gunmen(self, surface: pygame.Surface, house, time_ms: int):
        count = self._upgrades.gunman_count
        if count <= 0:
            return

        visible = min(count, GUNMAN_MAX_VISIBLE)
        hx, hy, hw, hh = house.x, house.y, house.width, house.height

        for i in range(visible):
            if i < GUNMAN_UNIQUE_SPOTS and i < len(_GUNMAN_SPOTS):
                xf, yf, pose = _GUNMAN_SPOTS[i]
                px = hx + int(hw * xf)
                py = hy + int(hh * yf)
                self._draw_gunman_sprite(surface, px, py, pose, i, time_ms)
            else:
                # Extra gunmen standing on the left side
                extra_idx = i - min(GUNMAN_UNIQUE_SPOTS, len(_GUNMAN_SPOTS))
                px = hx - 18 - extra_idx * 14
                py = hy + hh - 25
                self._draw_gunman_sprite(surface, px, py, "side_stand", i, time_ms)

    def _draw_gunman_flash(self, surface: pygame.Surface):
        """Draw muzzle flash effect when gunman shoots."""
        if self._gunman_flash_timer <= 0 or self._gunman_flash_pos is None:
            return
        fx, fy = self._gunman_flash_pos
        alpha = int(255 * (self._gunman_flash_timer / 0.15))
        # Bright flash circle
        flash_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(flash_surf, (255, 240, 150, alpha), (15, 15), 12)
        pygame.draw.circle(flash_surf, (255, 255, 220, min(255, alpha + 40)), (15, 15), 6)
        surface.blit(flash_surf, (fx - 15, fy - 15))

    # ── individual sprite drawers ──────────────────────────────────────

    def _draw_repairman_sprite(self, surface: pygame.Surface,
                                x: int, y: int, pose: str,
                                idx: int, time_ms: int):
        """Draw a single repairman at (x, y) with the given pose."""
        # Colors
        skin = (210, 170, 130)
        shirt = (80, 130, 180)       # blue work shirt
        pants = (70, 65, 60)
        hat = (220, 180, 50)         # yellow hard hat
        tool_col = (140, 130, 120)   # metal tool
        wood_col = (150, 100, 50)    # tool handle

        # Animation bob
        bob = math.sin(self._anim_timer * 3.0 + idx * 1.5) * 2

        if pose == "roof_hammer":
            # Standing on roof, hammering down
            # Body
            pygame.draw.rect(surface, shirt, (x, y + 6, 8, 12))
            pygame.draw.rect(surface, pants, (x + 1, y + 18, 7, 8))
            # Head + hard hat
            pygame.draw.circle(surface, skin, (x + 4, y + 3), 4)
            pygame.draw.rect(surface, hat, (x, y - 2, 9, 4), border_radius=1)
            # Arm with hammer (bobbing)
            arm_end_y = y + 8 + int(bob)
            pygame.draw.line(surface, skin, (x + 8, y + 8), (x + 14, arm_end_y), 2)
            # Hammer head
            pygame.draw.rect(surface, tool_col, (x + 12, arm_end_y - 2, 6, 4))
            pygame.draw.line(surface, wood_col, (x + 14, arm_end_y), (x + 14, arm_end_y + 8), 2)

        elif pose == "roof_saw":
            # On roof, using saw (horizontal motion)
            saw_bob = math.sin(self._anim_timer * 4.0 + idx * 2.0) * 3
            pygame.draw.rect(surface, shirt, (x, y + 6, 8, 12))
            pygame.draw.rect(surface, pants, (x + 1, y + 18, 7, 8))
            pygame.draw.circle(surface, skin, (x + 4, y + 3), 4)
            pygame.draw.rect(surface, hat, (x, y - 2, 9, 4), border_radius=1)
            # Arm with saw
            saw_x = x + 10 + int(saw_bob)
            pygame.draw.line(surface, skin, (x + 8, y + 10), (saw_x, y + 12), 2)
            # Saw blade (zigzag line)
            pygame.draw.line(surface, tool_col, (saw_x, y + 11), (saw_x + 10, y + 11), 2)
            # Saw teeth
            for tx in range(0, 10, 3):
                pygame.draw.line(surface, tool_col,
                                 (saw_x + tx, y + 13), (saw_x + tx + 1, y + 15), 1)

        elif pose == "window_fix":
            # Standing at a window, hammering on the frame
            pygame.draw.rect(surface, shirt, (x, y + 6, 8, 12))
            pygame.draw.rect(surface, pants, (x + 1, y + 18, 7, 8))
            pygame.draw.circle(surface, skin, (x + 4, y + 3), 4)
            pygame.draw.rect(surface, hat, (x, y - 2, 9, 4), border_radius=1)
            # Arm hammering at window
            arm_end_y = y + 6 + int(bob)
            pygame.draw.line(surface, skin, (x + 7, y + 8), (x + 15, arm_end_y), 2)
            pygame.draw.rect(surface, tool_col, (x + 13, arm_end_y - 2, 5, 4))
            pygame.draw.line(surface, wood_col, (x + 15, arm_end_y), (x + 15, arm_end_y + 6), 2)

        elif pose == "front_hammer":
            # Standing in front of house, hammering on the wall
            pygame.draw.rect(surface, shirt, (x, y + 6, 8, 14))
            pygame.draw.rect(surface, pants, (x + 1, y + 20, 7, 10))
            # Legs
            pygame.draw.rect(surface, (50, 45, 40), (x + 1, y + 28, 3, 4))
            pygame.draw.rect(surface, (50, 45, 40), (x + 5, y + 28, 3, 4))
            pygame.draw.circle(surface, skin, (x + 4, y + 3), 4)
            pygame.draw.rect(surface, hat, (x, y - 2, 9, 4), border_radius=1)
            # Arm with hammer
            arm_y = y + 8 + int(bob)
            pygame.draw.line(surface, skin, (x + 7, y + 10), (x + 16, arm_y), 2)
            pygame.draw.rect(surface, tool_col, (x + 14, arm_y - 2, 5, 4))
            pygame.draw.line(surface, wood_col, (x + 16, arm_y), (x + 16, arm_y + 7), 2)

        elif pose == "front_kneel":
            # Kneeling in front, fixing something low
            # Kneeling body (shorter)
            pygame.draw.rect(surface, shirt, (x, y + 4, 8, 10))
            pygame.draw.rect(surface, pants, (x + 1, y + 14, 7, 6))
            # Kneeling leg
            pygame.draw.rect(surface, pants, (x + 2, y + 18, 8, 4))
            pygame.draw.circle(surface, skin, (x + 4, y + 1), 4)
            pygame.draw.rect(surface, hat, (x, y - 4, 9, 4), border_radius=1)
            # Arm with wrench
            wrench_bob = math.sin(self._anim_timer * 2.5 + idx) * 2
            pygame.draw.line(surface, skin, (x + 7, y + 8),
                             (x + 14, y + 14 + int(wrench_bob)), 2)
            pygame.draw.rect(surface, tool_col,
                             (x + 12, y + 12 + int(wrench_bob), 5, 3))

        else:  # side_stand
            # Standing idle with tool in hand
            pygame.draw.rect(surface, shirt, (x, y - 24, 8, 14))
            pygame.draw.rect(surface, pants, (x + 1, y - 10, 7, 10))
            pygame.draw.rect(surface, (50, 45, 40), (x + 1, y, 3, 4))
            pygame.draw.rect(surface, (50, 45, 40), (x + 5, y, 3, 4))
            pygame.draw.circle(surface, skin, (x + 4, y - 27), 4)
            pygame.draw.rect(surface, hat, (x, y - 32, 9, 4), border_radius=1)
            # Holding hammer at side
            pygame.draw.line(surface, wood_col, (x + 9, y - 18), (x + 9, y - 6), 2)
            pygame.draw.rect(surface, tool_col, (x + 7, y - 20, 5, 4))

    def _draw_gunman_sprite(self, surface: pygame.Surface,
                             x: int, y: int, pose: str,
                             idx: int, time_ms: int):
        """Draw a single gunman at (x, y) with the given pose."""
        # Colors
        skin = (200, 160, 120)
        vest = (60, 80, 55)          # military green vest
        pants = (65, 60, 55)
        helmet = (85, 95, 80)
        gun_metal = (70, 70, 75)
        gun_wood = (110, 70, 40)

        # Subtle aiming sway
        sway = math.sin(self._anim_timer * 1.5 + idx * 2.0) * 1

        if pose == "kneel_front":
            # Kneeling, aiming left (towards enemies)
            # Body (kneeling)
            pygame.draw.rect(surface, vest, (x, y + 4, 8, 10))
            pygame.draw.rect(surface, pants, (x + 1, y + 14, 7, 5))
            # Kneeling leg
            pygame.draw.rect(surface, pants, (x - 4, y + 17, 10, 4))
            pygame.draw.circle(surface, skin, (x + 4, y + 1), 4)
            pygame.draw.ellipse(surface, helmet, (x - 1, y - 4, 10, 6))
            # Arms holding rifle (pointing left)
            gun_y = y + 8 + int(sway)
            pygame.draw.line(surface, skin, (x, y + 7), (x - 8, gun_y), 2)
            # Rifle
            pygame.draw.line(surface, gun_metal, (x - 6, gun_y), (x - 22, gun_y), 3)
            pygame.draw.rect(surface, gun_wood, (x - 8, gun_y - 1, 6, 4))

        elif pose == "window_aim":
            # Standing at window, aiming out (left)
            pygame.draw.rect(surface, vest, (x, y + 6, 8, 12))
            pygame.draw.rect(surface, pants, (x + 1, y + 18, 7, 8))
            pygame.draw.circle(surface, skin, (x + 4, y + 3), 4)
            pygame.draw.ellipse(surface, helmet, (x - 1, y - 2, 10, 6))
            # Arms + rifle pointing left through window
            gun_y = y + 9 + int(sway)
            pygame.draw.line(surface, skin, (x, y + 9), (x - 6, gun_y), 2)
            pygame.draw.line(surface, gun_metal, (x - 4, gun_y), (x - 18, gun_y), 3)
            pygame.draw.rect(surface, gun_wood, (x - 6, gun_y - 1, 5, 4))

        elif pose == "roof_prone":
            # Lying flat on roof, aiming left
            # Body horizontal
            pygame.draw.rect(surface, vest, (x, y + 2, 16, 6))
            pygame.draw.rect(surface, pants, (x + 14, y + 3, 8, 5))
            # Head
            pygame.draw.circle(surface, skin, (x - 1, y + 4), 4)
            pygame.draw.ellipse(surface, helmet, (x - 5, y, 8, 5))
            # Rifle
            gun_y = y + 4 + int(sway * 0.5)
            pygame.draw.line(surface, gun_metal, (x - 5, gun_y), (x - 20, gun_y), 3)
            pygame.draw.rect(surface, gun_wood, (x - 2, gun_y - 1, 5, 3))

        elif pose == "roof_crouch":
            # Crouching on roof, aiming left
            pygame.draw.rect(surface, vest, (x, y + 4, 8, 8))
            pygame.draw.rect(surface, pants, (x + 1, y + 12, 7, 5))
            pygame.draw.circle(surface, skin, (x + 4, y + 1), 4)
            pygame.draw.ellipse(surface, helmet, (x - 1, y - 3, 10, 5))
            # Rifle
            gun_y = y + 6 + int(sway)
            pygame.draw.line(surface, skin, (x, y + 6), (x - 6, gun_y), 2)
            pygame.draw.line(surface, gun_metal, (x - 4, gun_y), (x - 18, gun_y), 3)
            pygame.draw.rect(surface, gun_wood, (x - 6, gun_y - 1, 5, 4))

        else:  # side_stand
            # Standing with rifle at ready
            pygame.draw.rect(surface, vest, (x, y - 24, 8, 14))
            pygame.draw.rect(surface, pants, (x + 1, y - 10, 7, 10))
            pygame.draw.rect(surface, (50, 45, 40), (x + 1, y, 3, 4))
            pygame.draw.rect(surface, (50, 45, 40), (x + 5, y, 3, 4))
            pygame.draw.circle(surface, skin, (x + 4, y - 27), 4)
            pygame.draw.ellipse(surface, helmet, (x - 1, y - 32, 10, 5))
            # Rifle held diagonally
            pygame.draw.line(surface, gun_metal, (x - 2, y - 22), (x - 12, y - 10), 3)
            pygame.draw.rect(surface, gun_wood, (x - 4, y - 18, 5, 4))
