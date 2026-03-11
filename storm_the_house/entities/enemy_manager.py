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

Armored cars (boss enemies):
  • Spawn count equals the day number (1 on day 1, 2 on day 2, etc.)
  • Appear at evenly spaced intervals throughout the day.
  • Have 20 HP and attack 3x faster than regular enemies.
"""

from __future__ import annotations

import random
import pygame

from storm_the_house.core.settings import (
    ENEMY_SPAWN_INTERVAL,
    ENEMY_SPEED_SCALE_PER_DAY,
    ENEMY_SPAWN_SCALE_PER_DAY,
    ENEMY_SPAWN_VARIANCE,
    DAY_DURATION,
)
from storm_the_house.entities.enemy import Enemy
from storm_the_house.entities.armored_car import ArmoredCar


class EnemyManager:
    """Owns the list of active enemies and the spawn timer."""

    def __init__(self, house_left_x: int, day: int = 1):
        self._house_left_x = house_left_x
        self._day = day
        self._enemies: list[Enemy] = []
        self._armored_cars: list[ArmoredCar] = []

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

        # Armored car spawning: day number = number of armored cars
        self._armored_cars_to_spawn = day
        self._armored_cars_spawned = 0
        # Space armored cars evenly throughout the day
        if self._armored_cars_to_spawn > 0:
            self._armored_car_interval = DAY_DURATION / (self._armored_cars_to_spawn + 1)
        else:
            self._armored_car_interval = float('inf')
        self._armored_car_timer = self._armored_car_interval * 0.5  # first one comes earlier

    # ── helpers ────────────────────────────────────────────────────────────

    def _jittered_interval(self) -> float:
        """Return the spawn interval with ±ENEMY_SPAWN_VARIANCE random jitter."""
        jitter = random.uniform(-ENEMY_SPAWN_VARIANCE, ENEMY_SPAWN_VARIANCE)
        return max(0.3, self._spawn_interval + jitter)  # clamp to avoid ≤0

    # ── spawning ──────────────────────────────────────────────────────────

    def _spawn_enemy(self):
        enemy = Enemy(self._house_left_x, speed_multiplier=self._speed_multiplier)
        self._enemies.append(enemy)

    def _spawn_armored_car(self):
        car = ArmoredCar(self._house_left_x, speed_multiplier=self._speed_multiplier)
        self._armored_cars.append(car)
        self._armored_cars_spawned += 1

    # ── public API ────────────────────────────────────────────────────────

    @property
    def enemies(self) -> list[Enemy]:
        return self._enemies

    @property
    def armored_cars(self) -> list[ArmoredCar]:
        return self._armored_cars

    def update(self, dt: float):
        """Tick all enemies and handle spawn timer."""
        # Spawn timer for regular enemies
        self._spawn_timer += dt
        if self._spawn_timer >= self._next_spawn_at:
            self._spawn_timer -= self._next_spawn_at
            self._next_spawn_at = self._jittered_interval()
            self._spawn_enemy()

        # Spawn timer for armored cars
        if self._armored_cars_spawned < self._armored_cars_to_spawn:
            self._armored_car_timer += dt
            if self._armored_car_timer >= self._armored_car_interval:
                self._armored_car_timer -= self._armored_car_interval
                self._spawn_armored_car()

        # Update each enemy
        for e in self._enemies:
            e.update(dt)

        # Update each armored car
        for car in self._armored_cars:
            car.update(dt)

        # Remove dead enemies
        self._enemies = [e for e in self._enemies if e.alive]
        self._armored_cars = [car for car in self._armored_cars if car.alive]

    def draw(self, surface: pygame.Surface, time_ms: int):
        """Draw all enemies sorted by depth (back-to-front)."""
        # Combine enemies and armored cars for depth sorting
        all_entities = []
        for e in self._enemies:
            all_entities.append(('enemy', e.foot_y, e))
        for car in self._armored_cars:
            all_entities.append(('car', car.foot_y, car))

        # Sort by foot_y (depth)
        all_entities.sort(key=lambda x: x[1])

        # Draw in order
        for entity_type, _, entity in all_entities:
            entity.draw(surface, time_ms)

    def draw_armored_car_effects(self, surface: pygame.Surface):
        """Draw muzzle flashes and health bars for armored cars."""
        for car in self._armored_cars:
            car.draw_muzzle_flash(surface)
            car.draw_health_bar(surface)
