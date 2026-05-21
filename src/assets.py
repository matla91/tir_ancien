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
        real_sound = self.sound("sounds/flintlock_shot.ogg") or self.sound("sounds/flintlock_shot.wav")
        if real_sound is not None:
            real_sound.set_volume(0.82)
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

            sound = pygame.mixer.Sound(buffer=samples.tobytes())
            sound.set_volume(0.82)
            return sound
        except Exception:
            return None

    def build_target_hit_sound(self) -> Optional[pygame.mixer.Sound]:
        real_sound = self.sound("sounds/target_hit.ogg") or self.sound("sounds/target_hit.wav")
        if real_sound is not None:
            real_sound.set_volume(1.0)
            return real_sound

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            sample_rate = 44100
            duration = 0.13
            n = int(sample_rate * duration)
            samples = array.array("h")

            for i in range(n):
                t = i / sample_rate
                snap_env = math.exp(-t * 70.0)
                paper_env = math.exp(-t * 26.0)
                low_env = math.exp(-t * 18.0)

                snap = random.uniform(-1.0, 1.0) * snap_env
                paper = random.uniform(-1.0, 1.0) * paper_env
                low = math.sin(2 * math.pi * 180 * t) * low_env

                value = int(clamp((snap * 0.50 + paper * 0.34 + low * 0.22) * 26000, -32767, 32767))
                samples.append(value)

            sound = pygame.mixer.Sound(buffer=samples.tobytes())
            sound.set_volume(1.0)
            return sound
        except Exception:
            return None
