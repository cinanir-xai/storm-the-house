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


class ParticleManager:
    """Manages all active particle bursts."""

    def __init__(self):
        self._particles: list[_Particle] = []

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

    # ── update / draw ───────────────────────────────────────────────────

    def update(self, dt: float):
        for p in self._particles:
            p.update(dt)
        # Prune dead particles
        self._particles = [p for p in self._particles if p.alive]

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

    @property
    def count(self) -> int:
        return len(self._particles)
