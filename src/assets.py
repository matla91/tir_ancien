import array
import math
import random
from typing import Optional

import pygame

from src.settings import ASSETS_DIR
from src.utils import clamp


class AssetManager:
    def __init__(self) -> None:
        self.images = {}
        self.sounds = {}

    def image(self, relative_path: str, alpha: bool = True) -> Optional[pygame.Surface]:
        if relative_path in self.images:
            return self.images[relative_path]

        path = ASSETS_DIR / relative_path
        if not path.exists():
            return None

        image = pygame.image.load(str(path))
        image = image.convert_alpha() if alpha else image.convert()
        self.images[relative_path] = image
        return image

    def build_flintlock_shot_sound(self) -> Optional[pygame.mixer.Sound]:
        """Génère un son de tir sans fichier externe."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            sample_rate = 44100
            duration = 0.44
            n = int(sample_rate * duration)
            samples = array.array("h")

            for i in range(n):
                t = i / sample_rate
                crack_env = math.exp(-t * 34.0)
                boom_env = math.exp(-t * 8.0)

                noise = random.uniform(-1.0, 1.0) * crack_env
                boom = math.sin(2 * math.pi * 70 * t) * boom_env
                low_tail = math.sin(2 * math.pi * 38 * t) * math.exp(-t * 5.0)

                value = int(clamp((noise * 0.70 + boom * 0.52 + low_tail * 0.22) * 27000, -32767, 32767))
                samples.append(value)

            return pygame.mixer.Sound(buffer=samples.tobytes())
        except Exception:
            return None
