import random
from typing import Dict, List

import pygame

from ..utils import GameConfig
from .entity import Entity

STREAK_COUNT = 14
# fade out over ~15 frames once the world stops moving
FADE_PER_FRAME = 0.07
MAX_ALPHA = 150


class Wind(Entity):
    """Speed lines drifting behind the pipes.

    Invisible on the first difficulty level and progressively stronger on
    each one after it, so the player *feels* the speed as well as sees it.
    """

    def __init__(self, config: GameConfig) -> None:
        super().__init__(config)
        self.layer = pygame.Surface(
            (config.window.width, int(config.window.viewport_height)),
            pygame.SRCALPHA,
        )
        self.frozen = False
        self.fade = 1.0
        self.streaks: List[Dict[str, float]] = [
            self.make_streak(onscreen=True) for _ in range(STREAK_COUNT)
        ]

    def make_streak(self, onscreen: bool = False) -> Dict[str, float]:
        width = self.config.window.width
        return {
            "x": random.uniform(0, width)
            if onscreen
            else width + random.uniform(0, width * 0.6),
            "y": random.uniform(4, self.config.window.viewport_height - 6),
            "length": random.uniform(12, 44),
            "factor": random.uniform(1.1, 2.0),
        }

    def stop(self) -> None:
        self.frozen = True

    def draw(self) -> None:
        alpha = self.current_alpha()
        if alpha <= 0:
            return

        color = (*self.config.difficulty.color, alpha)
        self.layer.fill((0, 0, 0, 0))

        for streak in self.streaks:
            if not self.frozen:
                streak["x"] -= self.config.difficulty.speed * streak["factor"]
                if streak["x"] + streak["length"] < 0:
                    streak.update(self.make_streak())

            pygame.draw.line(
                self.layer,
                color,
                (streak["x"], streak["y"]),
                (streak["x"] + streak["length"], streak["y"]),
            )

        self.config.screen.blit(self.layer, (0, 0))

    def current_alpha(self) -> int:
        if self.frozen:
            self.fade = max(0.0, self.fade - FADE_PER_FRAME)
        return int(MAX_ALPHA * self.config.difficulty.intensity * self.fade)
