import random
from typing import Dict, List

import pygame

from src.utils import clamp


class SmokeSystem:
    def __init__(self) -> None:
        self.particles: List[Dict] = []

    def spawn(self, origin: pygame.Vector2, direction: pygame.Vector2, count: int = 24) -> None:
        if direction.length_squared() == 0:
            direction = pygame.Vector2(-1, -0.2)
        direction = direction.normalize()
        normal = pygame.Vector2(-direction.y, direction.x)

        for _ in range(count):
            speed = random.uniform(35, 135)
            spread = normal * random.uniform(-44, 44)
            vel = direction * speed + spread + pygame.Vector2(random.uniform(-12, 12), random.uniform(-35, -7))

            self.particles.append(
                {
                    "pos": pygame.Vector2(origin) + normal * random.uniform(-8, 8),
                    "vel": vel,
                    "life": random.uniform(0.75, 1.55),
                    "max_life": 1.55,
                    "radius": random.uniform(8, 18),
                }
            )

    def update(self, dt: float) -> None:
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["pos"] += p["vel"] * dt
                p["vel"] *= max(0, 1 - 0.8 * dt)
                p["radius"] += 18 * dt
                alive.append(p)
        self.particles = alive

    def draw(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            alpha_factor = clamp(p["life"] / p["max_life"], 0, 1)
            radius = int(p["radius"])
            size = radius * 2 + 4
            particle = pygame.Surface((size, size), pygame.SRCALPHA)
            alpha = int(95 * alpha_factor)
            pygame.draw.circle(particle, (215, 215, 205, alpha), (size // 2, size // 2), radius)
            surface.blit(particle, (p["pos"].x - size // 2, p["pos"].y - size // 2))
