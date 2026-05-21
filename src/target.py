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

    def apparent_scale(self, distance_m: int) -> float:
        """Perspective scale for an object at a given range.

        A target at 50 m is visually half the size of the same target at 25 m,
        a target at 100 m is half the size of the 50 m target, etc.
        """
        return 25.0 / max(1.0, float(distance_m))

    def ground_contact(self, distance_m: int) -> pygame.Vector2:
        """Approximate where the target stand touches the sandy lane.

        This is a light camera-perspective model fitted to the generated range
        background. The target foot moves toward the image vanishing area as the
        distance increases. It is not hand-placing each target independently: the
        same formula drives all distances.
        """
        scale = self.apparent_scale(distance_m)

        # Estimated vanishing/ground line of background_1 at the distant backstop.
        vanish = pygame.Vector2(WIDTH * 0.555, HEIGHT * 0.445)

        # Where a 25 m target should visibly stand on the sandy lane.
        near_25m = pygame.Vector2(WIDTH * 0.615, HEIGHT * 0.710)

        # Linear perspective convergence on the ground plane.
        return vanish + (near_25m - vanish) * scale

    def center(self, distance_m: int = 25) -> pygame.Vector2:
        scale = self.apparent_scale(distance_m)
        ground = self.ground_contact(distance_m)

        # Target center sits a scaled distance above the stand contact point.
        base_radius_25m = 96.0
        radius = base_radius_25m * scale
        stand_to_center_25m = base_radius_25m * 1.05
        return pygame.Vector2(ground.x, ground.y - stand_to_center_25m * scale + radius * 0.08)

    def radius(self, distance_m: int) -> float:
        # Exact visual law requested: apparent size halves when distance doubles.
        # 25m=96px, 50m=48px, 100m=24px, 200m=12px.
        return max(10.0, 96.0 * self.apparent_scale(distance_m))

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
        scale = self.apparent_scale(distance_m)
        ground = self.ground_contact(distance_m)

        stand_width = max(1, int(6 * scale))
        rail_height = max(1, int(8 * scale))
        leg_offset = radius * 0.75
        leg_spread = radius * 0.28

        pygame.draw.line(
            surface,
            WOOD,
            (center.x - leg_offset, center.y + radius * 0.90),
            (ground.x - leg_offset - leg_spread, ground.y),
            stand_width,
        )
        pygame.draw.line(
            surface,
            WOOD,
            (center.x + leg_offset, center.y + radius * 0.90),
            (ground.x + leg_offset + leg_spread, ground.y),
            stand_width,
        )
        pygame.draw.rect(
            surface,
            WOOD,
            (center.x - radius * 1.02, center.y + radius - rail_height / 2, radius * 2.04, rail_height),
        )

        pygame.draw.circle(surface, WHITE, center, radius)
        pygame.draw.circle(surface, BLACK, center, radius, max(1, int(2 * scale)))

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
            pygame.draw.circle(surface, BLACK, center, ring_r, max(1, int(1 * scale)))

        pygame.draw.circle(surface, RED, center, max(2, radius * 0.12))
        pygame.draw.circle(surface, BLACK, center, max(2, radius * 0.12), 1)

        mark_radius_outer = max(2, int(radius * 0.045))
        mark_radius_inner = max(1, int(radius * 0.028))
        for shot in self.shots:
            p = pygame.Vector2(shot.x, shot.y)
            pygame.draw.circle(surface, BLACK, p, mark_radius_outer)
            pygame.draw.circle(surface, YELLOW if shot.score >= 8 else WHITE, p, mark_radius_inner)
