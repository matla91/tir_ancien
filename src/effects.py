import random
from typing import Dict, List, Tuple

import pygame

from src.utils import clamp


class SmokeSystem:
    def __init__(self) -> None:
        self.particles: List[Dict] = []

    def spawn(self, origin: pygame.Vector2, direction: pygame.Vector2, count: int = 34) -> None:
        """Dense muzzle smoke for black-powder feedback."""
        if direction.length_squared() == 0:
            direction = pygame.Vector2(-1, -0.2)
        direction = direction.normalize()
        normal = pygame.Vector2(-direction.y, direction.x)

        for _ in range(count):
            speed = random.uniform(45, 170)
            spread = normal * random.uniform(-62, 62)
            upward_drift = pygame.Vector2(random.uniform(-18, 10), random.uniform(-55, -12))
            vel = direction * speed + spread + upward_drift

            self.particles.append(
                {
                    "pos": pygame.Vector2(origin) + normal * random.uniform(-12, 12),
                    "vel": vel,
                    "life": random.uniform(0.95, 2.25),
                    "max_life": 2.25,
                    "radius": random.uniform(10, 24),
                    "growth": random.uniform(18, 34),
                    "alpha": random.randint(70, 125),
                }
            )

    def update(self, dt: float) -> None:
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["pos"] += p["vel"] * dt
                p["vel"] *= max(0, 1 - 0.95 * dt)
                p["vel"].y -= 8 * dt
                p["radius"] += p["growth"] * dt
                alive.append(p)
        self.particles = alive

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2 | None = None) -> None:
        offset = offset or pygame.Vector2(0, 0)
        for p in self.particles:
            alpha_factor = clamp(p["life"] / p["max_life"], 0, 1)
            radius = int(p["radius"])
            size = radius * 2 + 4
            particle = pygame.Surface((size, size), pygame.SRCALPHA)
            alpha = int(p["alpha"] * alpha_factor)
            color = random.choice([(215, 215, 205, alpha), (190, 190, 180, alpha), (160, 160, 150, alpha)])
            pygame.draw.circle(particle, color, (size // 2, size // 2), radius)
            surface.blit(particle, (p["pos"].x + offset.x - size // 2, p["pos"].y + offset.y - size // 2))


class FloatingTextSystem:
    def __init__(self) -> None:
        self.items: List[Dict] = []

    def spawn(self, text: str, pos: pygame.Vector2, color: Tuple[int, int, int], size: int = 28) -> None:
        self.items.append(
            {
                "text": text,
                "pos": pygame.Vector2(pos),
                "vel": pygame.Vector2(random.uniform(-18, 18), random.uniform(-72, -48)),
                "life": 1.05,
                "max_life": 1.05,
                "color": color,
                "size": size,
            }
        )

    def update(self, dt: float) -> None:
        alive = []
        for item in self.items:
            item["life"] -= dt
            if item["life"] > 0:
                item["pos"] += item["vel"] * dt
                item["vel"].y += 18 * dt
                alive.append(item)
        self.items = alive

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2 | None = None) -> None:
        offset = offset or pygame.Vector2(0, 0)
        for item in self.items:
            alpha = int(255 * clamp(item["life"] / item["max_life"], 0, 1))
            font = pygame.font.SysFont("arial", item["size"], bold=True)
            shadow = font.render(item["text"], True, (0, 0, 0))
            text = font.render(item["text"], True, item["color"])
            shadow.set_alpha(alpha)
            text.set_alpha(alpha)
            pos = item["pos"] + offset
            surface.blit(shadow, (pos.x + 2, pos.y + 2))
            surface.blit(text, (pos.x, pos.y))


class ImpactFeedbackSystem:
    def __init__(self) -> None:
        self.impacts: List[Dict] = []

    def spawn(self, pos: pygame.Vector2, score: int) -> None:
        self.impacts.append(
            {
                "pos": pygame.Vector2(pos),
                "life": 0.42,
                "max_life": 0.42,
                "score": score,
            }
        )

    def update(self, dt: float) -> None:
        alive = []
        for impact in self.impacts:
            impact["life"] -= dt
            if impact["life"] > 0:
                alive.append(impact)
        self.impacts = alive

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2 | None = None) -> None:
        offset = offset or pygame.Vector2(0, 0)
        for impact in self.impacts:
            t = 1 - clamp(impact["life"] / impact["max_life"], 0, 1)
            radius = int(10 + 42 * t)
            alpha = int(210 * (1 - t))
            pos = impact["pos"] + offset
            ring = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            color = (240, 210, 80, alpha) if impact["score"] >= 8 else (255, 255, 255, alpha)
            pygame.draw.circle(ring, color, (radius + 2, radius + 2), radius, 3)
            surface.blit(ring, (pos.x - radius - 2, pos.y - radius - 2))
