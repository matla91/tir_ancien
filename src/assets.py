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

    def sound(self, relative_path: str) -> Optional[pygame.mixer.Sound]:
        if relative_path in self.sounds:
            return self.sounds[relative_path]

        path = ASSETS_DIR / relative_path
        if not path.exists():
            return None

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            sound = pygame.mixer.Sound(str(path))
            self.sounds[relative_path] = sound
            return sound
        except Exception:
            return None

    def build_flintlock_shot_sound(self) -> Optional[pygame.mixer.Sound]:
        """Charge un vrai son de tir si présent, sinon génère un fallback.

        Place ton fichier ici, dans l'un de ces formats :
        - assets/sounds/flintlock_shot.ogg
        - assets/sounds/flintlock_shot.wav

        OGG est recommandé pour GitHub : plus léger qu'un WAV.
        """
        real_sound = self.sound("sounds/flintlock_shot.ogg") or self.sound("sounds/flintlock_shot.wav")
        if real_sound is not None:
            return real_sound

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
