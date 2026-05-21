from dataclasses import dataclass
from typing import List

import pygame

from src.settings import BLACK, BLUE, RED, WHITE, WOOD, YELLOW, WIDTH, HEIGHT
from src.utils import clamp


@dataclass
class Shot:
    x: float
    y: float
    score: int
    distance: int
    ring_error: float


class Target:
    def __init__(self) -> None:
        self.shots: List[Shot] = []

    def center(self, distance_m: int = 25) -> pygame.Vector2:
        t = clamp((distance_m - 25) / 175, 0, 1)
        return pygame.Vector2(WIDTH * (0.58 + 0.035 * t), HEIGHT * (0.36 - 0.075 * t))

    def radius(self, distance_m: int) -> float:
        return clamp(126 * (25 / distance_m) ** 0.42, 34, 126)

    def score_impact(self, impact: pygame.Vector2, distance_m: int) -> Shot:
        center = self.center(distance_m)
        radius = self.radius(distance_m)
        error = impact.distance_to(center)
        normalized = error / radius

        if normalized <= 1.0:
            score = int(clamp(10 - int(normalized * 10), 1, 10))
        elif normalized <= 1.16:
            score = 1
        else:
            score = 0

        shot = Shot(impact.x, impact.y, score, distance_m, normalized)
        self.shots.append(shot)
        return shot

    def clear_stage(self) -> None:
        self.shots.clear()

    def draw(self, surface: pygame.Surface, distance_m: int) -> None:
        center = self.center(distance_m)
        radius = self.radius(distance_m)

        pygame.draw.line(surface, WOOD, (center.x - radius * 0.85, center.y + radius), (center.x - radius * 1.15, center.y + radius + 150), 6)
        pygame.draw.line(surface, WOOD, (center.x + radius * 0.85, center.y + radius), (center.x + radius * 1.15, center.y + radius + 150), 6)
        pygame.draw.rect(surface, WOOD, (center.x - radius * 1.05, center.y + radius - 4, radius * 2.1, 8))

        pygame.draw.circle(surface, WHITE, center, radius)
        pygame.draw.circle(surface, BLACK, center, radius, 2)

        for i in range(10, 0, -1):
            ring_r = radius * i / 10
            if i <= 3:
                color = RED
            elif i <= 6:
                color = BLUE
            else:
                color = WHITE

            if i <= 6:
                pygame.draw.circle(surface, color, center, ring_r)
            pygame.draw.circle(surface, BLACK, center, ring_r, 1)

        pygame.draw.circle(surface, RED, center, radius * 0.12)
        pygame.draw.circle(surface, BLACK, center, radius * 0.12, 1)

        for shot in self.shots:
            p = pygame.Vector2(shot.x, shot.y)
            pygame.draw.circle(surface, BLACK, p, 5)
            pygame.draw.circle(surface, YELLOW if shot.score >= 8 else WHITE, p, 3)
