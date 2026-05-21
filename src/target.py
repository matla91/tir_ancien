from dataclasses import dataclass
from typing import Dict, List

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


@dataclass(frozen=True)
class TargetType:
    target_id: str
    name: str
    description: str
    price: int
    difficulty: str
    reward_multiplier: float
    size_multiplier: float


TARGET_CATALOG: Dict[str, TargetType] = {
    "sport_precision": TargetType(
        target_id="sport_precision",
        name="Cible précision papier",
        description="Cible sportive classique : feuille claire, visuel noir, petite taille réaliste.",
        price=0,
        difficulty="Standard",
        reward_multiplier=1.00,
        size_multiplier=1.00,
    ),
    "silhouette_training": TargetType(
        target_id="silhouette_training",
        name="Silhouette d'entraînement",
        description="Forme de buste stylisée, plus lisible mais zones de score moins généreuses.",
        price=180,
        difficulty="Facile",
        reward_multiplier=0.85,
        size_multiplier=1.22,
    ),
    "hostage_drill": TargetType(
        target_id="hostage_drill",
        name="Exercice prise d'otage",
        description="Petite zone utile : toucher la mauvaise zone annule le gain du tir.",
        price=420,
        difficulty="Difficile",
        reward_multiplier=1.55,
        size_multiplier=0.92,
    ),
    "gel_block": TargetType(
        target_id="gel_block",
        name="Bloc de gélatine balistique",
        description="Bloc technique pour tests d'impact : score simple, gros bonus plein centre.",
        price=760,
        difficulty="Technique",
        reward_multiplier=1.30,
        size_multiplier=1.08,
    ),
}


class Target:
    def __init__(self) -> None:
        self.shots: List[Shot] = []
        self.target_id = "sport_precision"

    @property
    def target_type(self) -> TargetType:
        return TARGET_CATALOG[self.target_id]

    def set_type(self, target_id: str) -> None:
        if target_id in TARGET_CATALOG:
            self.target_id = target_id
            self.clear_stage()

    def apparent_scale(self, distance_m: int) -> float:
        """Perspective scale: 50 m appears 2x smaller than 25 m, 100 m 2x smaller than 50 m."""
        return 25.0 / max(1.0, float(distance_m))

    def ground_contact(self, distance_m: int) -> pygame.Vector2:
        scale = self.apparent_scale(distance_m)
        vanish = pygame.Vector2(WIDTH * 0.555, HEIGHT * 0.445)
        near_25m = pygame.Vector2(WIDTH * 0.615, HEIGHT * 0.710)
        return vanish + (near_25m - vanish) * scale

    def center(self, distance_m: int = 25) -> pygame.Vector2:
        scale = self.apparent_scale(distance_m)
        ground = self.ground_contact(distance_m)
        radius = self.radius(distance_m)
        return pygame.Vector2(ground.x, ground.y - radius * 1.22)

    def radius(self, distance_m: int) -> float:
        # Realistic pistol paper target feel: much smaller than the old archery-like target.
        # Strict perspective law: 25 m=34 px, 50 m=17 px, 100 m=8.5 px, 200 m=4.25 px.
        return max(4.0, 34.0 * self.target_type.size_multiplier * self.apparent_scale(distance_m))

    def score_impact(self, impact: pygame.Vector2, distance_m: int) -> Shot:
        center = self.center(distance_m)
        radius = self.radius(distance_m)
        error = impact.distance_to(center)
        normalized = error / max(1.0, radius)

        if self.target_id == "hostage_drill":
            score = self.score_hostage(impact, center, radius)
        elif self.target_id == "silhouette_training":
            score = self.score_silhouette(impact, center, radius)
        elif self.target_id == "gel_block":
            score = self.score_gel_block(impact, center, radius)
        else:
            score = self.score_precision(normalized)

        shot = Shot(impact.x, impact.y, score, distance_m, normalized)
        self.shots.append(shot)
        return shot

    def score_precision(self, normalized: float) -> int:
        if normalized <= 1.0:
            return int(clamp(10 - int(normalized * 10), 1, 10))
        if normalized <= 1.18:
            return 1
        return 0

    def score_silhouette(self, impact: pygame.Vector2, center: pygame.Vector2, radius: float) -> int:
        dx = abs(impact.x - center.x)
        dy = impact.y - center.y
        head = pygame.Vector2(center.x, center.y - radius * 1.35)
        if impact.distance_to(head) <= radius * 0.48:
            return 10
        if -radius * 0.95 <= dy <= radius * 1.55:
            width = radius * (0.95 - 0.22 * clamp((dy + radius * 0.95) / (radius * 2.5), 0, 1))
            if dx <= width:
                core = max(abs(dx) / max(1, width), abs(dy - radius * 0.15) / max(1, radius * 1.25))
                return int(clamp(9 - int(core * 5), 2, 9))
        return 0

    def score_hostage(self, impact: pygame.Vector2, center: pygame.Vector2, radius: float) -> int:
        no_shoot = pygame.Rect(center.x - radius * 1.20, center.y - radius * 1.10, radius * 0.78, radius * 2.20)
        if no_shoot.collidepoint(impact.x, impact.y):
            return 0
        threat_center = pygame.Vector2(center.x + radius * 0.42, center.y)
        normalized = impact.distance_to(threat_center) / max(1.0, radius * 0.82)
        return self.score_precision(normalized)

    def score_gel_block(self, impact: pygame.Vector2, center: pygame.Vector2, radius: float) -> int:
        rect = pygame.Rect(center.x - radius * 1.45, center.y - radius * 0.85, radius * 2.9, radius * 1.7)
        if not rect.collidepoint(impact.x, impact.y):
            return 0
        normalized = max(abs(impact.x - center.x) / (radius * 1.45), abs(impact.y - center.y) / (radius * 0.85))
        if normalized <= 0.18:
            return 10
        return int(clamp(9 - int(normalized * 7), 1, 9))

    def clear_stage(self) -> None:
        self.shots.clear()

    def draw(self, surface: pygame.Surface, distance_m: int) -> None:
        center = self.center(distance_m)
        radius = self.radius(distance_m)
        scale = self.apparent_scale(distance_m)
        ground = self.ground_contact(distance_m)

        self.draw_stand(surface, center, radius, scale, ground)

        if self.target_id == "silhouette_training":
            self.draw_silhouette(surface, center, radius, scale)
        elif self.target_id == "hostage_drill":
            self.draw_hostage(surface, center, radius, scale)
        elif self.target_id == "gel_block":
            self.draw_gel_block(surface, center, radius, scale)
        else:
            self.draw_precision_target(surface, center, radius, scale)

        self.draw_shot_marks(surface, radius)

    def draw_stand(self, surface: pygame.Surface, center: pygame.Vector2, radius: float, scale: float, ground: pygame.Vector2) -> None:
        stand_width = max(1, int(5 * scale))
        rail_height = max(1, int(6 * scale))
        leg_offset = radius * 0.88
        leg_spread = radius * 0.35

        pygame.draw.line(surface, WOOD, (center.x - leg_offset, center.y + radius * 1.10), (ground.x - leg_offset - leg_spread, ground.y), stand_width)
        pygame.draw.line(surface, WOOD, (center.x + leg_offset, center.y + radius * 1.10), (ground.x + leg_offset + leg_spread, ground.y), stand_width)
        pygame.draw.rect(surface, WOOD, (center.x - radius * 1.25, center.y + radius * 1.10, radius * 2.5, rail_height))

    def draw_precision_target(self, surface: pygame.Surface, center: pygame.Vector2, radius: float, scale: float) -> None:
        paper = pygame.Rect(center.x - radius * 1.42, center.y - radius * 1.42, radius * 2.84, radius * 2.84)
        pygame.draw.rect(surface, (238, 235, 222), paper)
        pygame.draw.rect(surface, BLACK, paper, max(1, int(1.4 * scale)))

        for i in range(10, 0, -1):
            ring_r = radius * i / 10
            if i <= 7:
                pygame.draw.circle(surface, BLACK, center, ring_r)
                ring_color = (230, 230, 220)
            else:
                ring_color = BLACK
            pygame.draw.circle(surface, ring_color, center, ring_r, max(1, int(1 * scale)))

        pygame.draw.circle(surface, (238, 235, 222), center, max(1, radius * 0.10))

    def draw_silhouette(self, surface: pygame.Surface, center: pygame.Vector2, radius: float, scale: float) -> None:
        color = (28, 28, 26)
        pygame.draw.circle(surface, color, (center.x, center.y - radius * 1.35), radius * 0.48)
        body = pygame.Rect(center.x - radius * 0.95, center.y - radius * 0.70, radius * 1.9, radius * 2.25)
        pygame.draw.ellipse(surface, color, body)
        pygame.draw.rect(surface, (235, 232, 218), (center.x - radius * 0.22, center.y - radius * 0.20, radius * 0.44, radius * 0.70), max(1, int(1 * scale)))
        pygame.draw.circle(surface, YELLOW, center, max(1, radius * 0.13))

    def draw_hostage(self, surface: pygame.Surface, center: pygame.Vector2, radius: float, scale: float) -> None:
        paper = pygame.Rect(center.x - radius * 1.65, center.y - radius * 1.45, radius * 3.3, radius * 2.9)
        pygame.draw.rect(surface, (236, 233, 219), paper)
        pygame.draw.rect(surface, BLACK, paper, max(1, int(1 * scale)))

        no_shoot = pygame.Rect(center.x - radius * 1.20, center.y - radius * 1.10, radius * 0.78, radius * 2.20)
        pygame.draw.rect(surface, (215, 215, 202), no_shoot)
        pygame.draw.rect(surface, RED, no_shoot, max(1, int(1.5 * scale)))

        threat_center = pygame.Vector2(center.x + radius * 0.42, center.y)
        pygame.draw.circle(surface, BLACK, threat_center, radius * 0.82)
        pygame.draw.circle(surface, (236, 233, 219), threat_center, radius * 0.23, max(1, int(1 * scale)))
        pygame.draw.circle(surface, YELLOW, threat_center, max(1, radius * 0.10))

    def draw_gel_block(self, surface: pygame.Surface, center: pygame.Vector2, radius: float, scale: float) -> None:
        rect = pygame.Rect(center.x - radius * 1.45, center.y - radius * 0.85, radius * 2.9, radius * 1.7)
        pygame.draw.rect(surface, (168, 215, 224), rect, border_radius=max(1, int(4 * scale)))
        pygame.draw.rect(surface, (50, 100, 112), rect, max(1, int(2 * scale)), border_radius=max(1, int(4 * scale)))
        pygame.draw.line(surface, (235, 250, 250), (rect.left + radius * 0.30, rect.top + radius * 0.25), (rect.right - radius * 0.35, rect.top + radius * 0.25), max(1, int(2 * scale)))
        pygame.draw.circle(surface, YELLOW, center, max(1, radius * 0.12))

    def draw_shot_marks(self, surface: pygame.Surface, radius: float) -> None:
        mark_radius_outer = max(2, int(radius * 0.055))
        mark_radius_inner = max(1, int(radius * 0.034))
        for shot in self.shots:
            p = pygame.Vector2(shot.x, shot.y)
            pygame.draw.circle(surface, BLACK, p, mark_radius_outer)
            pygame.draw.circle(surface, YELLOW if shot.score >= 8 else WHITE, p, mark_radius_inner)
