"""
Enemy manager – spawns enemies at regular intervals and manages the
active enemy list.

Enemies are drawn sorted by foot_y so that enemies closer to the camera
(larger foot_y) appear in front of those further away.

Difficulty scales with the day number:
  • Enemy speed increases by 10 % per day (multiplicative).
  • Spawn interval shrinks by 15 % per day (multiplicative).
  • Each spawn timer has ±1 s random jitter.
  • Each enemy gets a ±10 % individual speed modifier.
"""

from __future__ import annotations

import random
import pygame

from storm_the_house.core.settings import (
    ENEMY_SPAWN_INTERVAL,
    ENEMY_SPEED_SCALE_PER_DAY,
    ENEMY_SPAWN_SCALE_PER_DAY,
    ENEMY_SPAWN_VARIANCE,
)
from storm_the_house.entities.enemy import Enemy


class EnemyManager:
    """Owns the list of active enemies and the spawn timer."""

    def __init__(self, house_left_x: int, day: int = 1):
        self._house_left_x = house_left_x
        self._day = day
        self._enemies: list[Enemy] = []

        # Day-based difficulty modifiers
        # Speed multiplier: 1.10^(day-1)  →  day 1 = 1.0, day 2 = 1.10, …
        self._speed_multiplier: float = ENEMY_SPEED_SCALE_PER_DAY ** (day - 1)
        # Spawn interval multiplier: 0.85^(day-1)  →  interval shrinks each day
        self._spawn_interval: float = (
            ENEMY_SPAWN_INTERVAL * (ENEMY_SPAWN_SCALE_PER_DAY ** (day - 1))
        )

        self._spawn_timer: float = 0.0
        self._next_spawn_at: float = self._jittered_interval()

        # Spawn one immediately so the screen isn't empty at start
        self._spawn_enemy()

    # ── helpers ────────────────────────────────────────────────────────────

    def _jittered_interval(self) -> float:
        """Return the spawn interval with ±ENEMY_SPAWN_VARIANCE random jitter."""
        jitter = random.uniform(-ENEMY_SPAWN_VARIANCE, ENEMY_SPAWN_VARIANCE)
        return max(0.3, self._spawn_interval + jitter)  # clamp to avoid ≤0

    # ── spawning ──────────────────────────────────────────────────────────

    def _spawn_enemy(self):
        enemy = Enemy(self._house_left_x, speed_multiplier=self._speed_multiplier)
        self._enemies.append(enemy)

    # ── public API ────────────────────────────────────────────────────────

    @property
    def enemies(self) -> list[Enemy]:
        return self._enemies

    def update(self, dt: float):
        """Tick all enemies and handle spawn timer."""
        # Spawn timer
        self._spawn_timer += dt
        if self._spawn_timer >= self._next_spawn_at:
            self._spawn_timer -= self._next_spawn_at
            self._next_spawn_at = self._jittered_interval()
            self._spawn_enemy()

        # Update each enemy
        for e in self._enemies:
            e.update(dt)

        # Remove dead enemies
        self._enemies = [e for e in self._enemies if e.alive]

    def draw(self, surface: pygame.Surface, time_ms: int):
        """Draw all enemies sorted by depth (back-to-front)."""
        for e in sorted(self._enemies, key=lambda e: e.foot_y):
            e.draw(surface, time_ms)
