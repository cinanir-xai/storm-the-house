"""
Particle effects – blood splatter (enemy hit) and dust puffs (ground miss).

Each particle is a small physics-driven dot with gravity, drag, and fade-out.
Particles are pooled per-emitter and cleaned up when all have expired.
"""

from __future__ import annotations

import math
import random
import pygame

from storm_the_house.core.settings import (
    BLOOD_COUNT_MIN, BLOOD_COUNT_MAX,
    BLOOD_SPEED_MIN, BLOOD_SPEED_MAX,
    BLOOD_LIFETIME_MIN, BLOOD_LIFETIME_MAX,
    BLOOD_GRAVITY, BLOOD_COLORS,
    DUST_COUNT_MIN, DUST_COUNT_MAX,
    DUST_SPEED_MIN, DUST_SPEED_MAX,
    DUST_LIFETIME_MIN, DUST_LIFETIME_MAX,
    DUST_GRAVITY, DUST_COLORS,
    EXPLOSION_COUNT_MIN, EXPLOSION_COUNT_MAX,
    EXPLOSION_SPEED_MIN, EXPLOSION_SPEED_MAX,
    EXPLOSION_LIFETIME_MIN, EXPLOSION_LIFETIME_MAX,
    EXPLOSION_GRAVITY, EXPLOSION_COLORS,
    DEBRIS_COUNT_MIN, DEBRIS_COUNT_MAX,
    DEBRIS_SPEED_MIN, DEBRIS_SPEED_MAX,
    DEBRIS_LIFETIME_MIN, DEBRIS_LIFETIME_MAX,
    DEBRIS_GRAVITY, DEBRIS_COLORS,
    BLOOD_PUDDLE_LIFETIME_MIN, BLOOD_PUDDLE_LIFETIME_MAX,
    BLOOD_PUDDLE_SIZE_MIN, BLOOD_PUDDLE_SIZE_MAX, BLOOD_PUDDLE_COLORS,
    BLOOD_PUDDLE_ALPHA,
)


class _Particle:
    """A single particle with position, velocity, lifetime, and color."""

    __slots__ = ("x", "y", "vx", "vy", "gravity", "lifetime", "max_lifetime",
                 "color", "size", "drag")

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 gravity: float, lifetime: float, color: tuple,
                 size: float, drag: float = 0.98):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.gravity = gravity
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        self.size = size
        self.drag = drag

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

    @property
    def alpha(self) -> int:
        """Fade out as lifetime depletes."""
        t = max(0.0, self.lifetime / self.max_lifetime)
        return int(255 * t * t)  # quadratic fade-out for smoother look

    def update(self, dt: float):
        self.lifetime -= dt
        self.vy += self.gravity * dt
        self.vx *= self.drag
        self.vy *= self.drag
        self.x += self.vx * dt
        self.y += self.vy * dt


class _BloodPuddle:
    """Static blood puddle decal that fades out."""

    __slots__ = ("x", "y", "size", "lifetime", "max_lifetime", "color", "blobs")

    def __init__(self, x: float, y: float, size: float, lifetime: float, color: tuple):
        self.x = x
        self.y = y
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        # Generate random blob positions for splatter effect
        self.blobs: list[tuple[float, float, float]] = []
        num_blobs = random.randint(3, 6)
        for _ in range(num_blobs):
            bx = random.uniform(-size * 1.2, size * 1.2)
            by = random.uniform(-size * 0.5, size * 0.5)
            br = random.uniform(size * 0.25, size * 0.6)
            self.blobs.append((bx, by, br))

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

    @property
    def alpha(self) -> int:
        t = max(0.0, self.lifetime / self.max_lifetime)
        return int(BLOOD_PUDDLE_ALPHA * t)

    def update(self, dt: float):
        self.lifetime -= dt


class ParticleManager:
    """Manages all active particle bursts."""

    def __init__(self):
        self._particles: list[_Particle] = []
        self._puddles: list[_BloodPuddle] = []

    # ── emitters ────────────────────────────────────────────────────────

    def emit_blood(self, x: float, y: float):
        """Spawn a burst of blood particles at (x, y)."""
        count = random.randint(BLOOD_COUNT_MIN, BLOOD_COUNT_MAX)
        for _ in range(count):
            angle = random.uniform(-math.pi * 0.8, math.pi * 0.2)  # mostly upward/outward
            speed = random.uniform(BLOOD_SPEED_MIN, BLOOD_SPEED_MAX)
            vx = math.cos(angle) * speed * random.choice([-1, 1])
            vy = -abs(math.sin(angle) * speed)  # always launch upward initially
            lifetime = random.uniform(BLOOD_LIFETIME_MIN, BLOOD_LIFETIME_MAX)
            color = random.choice(BLOOD_COLORS)
            size = random.uniform(1.5, 3.5)
            self._particles.append(
                _Particle(x, y, vx, vy, BLOOD_GRAVITY, lifetime, color, size, drag=0.97)
            )

        # Add a lingering puddle near the ground (offset to side)
        puddle_lifetime = random.uniform(BLOOD_PUDDLE_LIFETIME_MIN, BLOOD_PUDDLE_LIFETIME_MAX)
        puddle_size = random.uniform(BLOOD_PUDDLE_SIZE_MIN, BLOOD_PUDDLE_SIZE_MAX)
        puddle_color = random.choice(BLOOD_PUDDLE_COLORS)
        offset_x = random.choice([-1, 1]) * random.uniform(8, 16)
        self._puddles.append(
            _BloodPuddle(x + offset_x, y + random.uniform(4, 10), puddle_size, puddle_lifetime, puddle_color)
        )

    def emit_dust(self, x: float, y: float):
        """Spawn a puff of dust particles at (x, y) – for ground miss."""
        count = random.randint(DUST_COUNT_MIN, DUST_COUNT_MAX)
        for _ in range(count):
            angle = random.uniform(-math.pi * 0.9, -math.pi * 0.1)  # fan upward
            speed = random.uniform(DUST_SPEED_MIN, DUST_SPEED_MAX)
            vx = math.cos(angle) * speed * random.uniform(0.5, 1.5)
            vy = math.sin(angle) * speed  # upward (negative y)
            lifetime = random.uniform(DUST_LIFETIME_MIN, DUST_LIFETIME_MAX)
            color = random.choice(DUST_COLORS)
            size = random.uniform(2.0, 5.0)
            self._particles.append(
                _Particle(x, y, vx, vy, DUST_GRAVITY, lifetime, color, size, drag=0.95)
            )

    def emit_explosion(self, x: float, y: float, scale: float = 1.0):
        """Spawn an explosion burst at (x, y) – for armored car destruction."""
        # Fire/explosion particles
        count = random.randint(EXPLOSION_COUNT_MIN, EXPLOSION_COUNT_MAX)
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)  # all directions
            speed = random.uniform(EXPLOSION_SPEED_MIN, EXPLOSION_SPEED_MAX) * scale
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - random.uniform(30, 80)  # bias upward
            lifetime = random.uniform(EXPLOSION_LIFETIME_MIN, EXPLOSION_LIFETIME_MAX)
            color = random.choice(EXPLOSION_COLORS)
            size = random.uniform(3.0, 8.0) * scale
            self._particles.append(
                _Particle(x, y, vx, vy, EXPLOSION_GRAVITY, lifetime, color, size, drag=0.96)
            )

    def emit_debris(self, x: float, y: float, scale: float = 1.0):
        """Spawn debris particles at (x, y) – metal/vehicle fragments."""
        count = random.randint(DEBRIS_COUNT_MIN, DEBRIS_COUNT_MAX)
        for _ in range(count):
            angle = random.uniform(-math.pi * 0.8, math.pi * 0.2)  # mostly up and outward
            speed = random.uniform(DEBRIS_SPEED_MIN, DEBRIS_SPEED_MAX) * scale
            vx = math.cos(angle) * speed * random.choice([-1, 1])
            vy = -abs(math.sin(angle) * speed) - random.uniform(20, 60)  # upward
            lifetime = random.uniform(DEBRIS_LIFETIME_MIN, DEBRIS_LIFETIME_MAX)
            color = random.choice(DEBRIS_COLORS)
            size = random.uniform(2.0, 5.0) * scale
            self._particles.append(
                _Particle(x, y, vx, vy, DEBRIS_GRAVITY, lifetime, color, size, drag=0.98)
            )

    def emit_smoke(self, x: float, y: float, count: int = 8):
        """Spawn smoke particles at (x, y) – rising dark smoke."""
        for _ in range(count):
            angle = random.uniform(-math.pi * 0.3, math.pi * 0.3)  # mostly upward
            speed = random.uniform(20, 50)
            vx = math.cos(angle) * speed * random.choice([-1, 1])
            vy = -abs(math.sin(angle) * speed) - random.uniform(10, 30)
            lifetime = random.uniform(0.8, 1.5)
            # Dark grey to black smoke
            grey = random.randint(40, 80)
            color = (grey, grey, grey)
            size = random.uniform(6.0, 12.0)
            # Smoke rises and expands
            self._particles.append(
                _Particle(x, y, vx, vy, -30, lifetime, color, size, drag=0.99)  # negative gravity = rises
            )

    # ── update / draw ───────────────────────────────────────────────────

    def update(self, dt: float):
        for p in self._particles:
            p.update(dt)
        for puddle in self._puddles:
            puddle.update(dt)
        # Prune dead particles
        self._particles = [p for p in self._particles if p.alive]
        self._puddles = [p for p in self._puddles if p.alive]

    def draw(self, surface: pygame.Surface):
        """Draw all living particles with alpha fade."""
        for p in self._particles:
            alpha = p.alpha
            if alpha <= 0:
                continue
            r = max(1, int(p.size))
            # For small particles, a filled circle on a tiny alpha surface
            d = r * 2 + 2
            tmp = pygame.Surface((d, d), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (*p.color, alpha), (d // 2, d // 2), r)
            surface.blit(tmp, (int(p.x) - d // 2, int(p.y) - d // 2))

    def draw_puddles(self, surface: pygame.Surface):
        """Draw blood puddles behind everything else."""
        for puddle in self._puddles:
            alpha = puddle.alpha
            if alpha <= 0:
                continue
            # Draw each blob in the splatter
            for bx, by, br in puddle.blobs:
                r = max(1, int(br))
                d = r * 2 + 2
                tmp = pygame.Surface((d, d), pygame.SRCALPHA)
                pygame.draw.circle(tmp, (*puddle.color, alpha), (d // 2, d // 2), r)
                surface.blit(tmp, (int(puddle.x + bx) - d // 2, int(puddle.y + by) - d // 2))

    @property
    def count(self) -> int:
        return len(self._particles)
