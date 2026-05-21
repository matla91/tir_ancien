import math
from typing import Tuple

import pygame


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    pos: Tuple[float, float],
    color: Tuple[int, int, int],
    center: bool = False,
) -> None:
    image = font.render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(image, rect)


def safe_load_json(path):
    import json

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def vec_or_default(vector: pygame.Vector2, fallback: pygame.Vector2) -> pygame.Vector2:
    if vector.length_squared() == 0:
        return pygame.Vector2(fallback)
    return pygame.Vector2(vector)
