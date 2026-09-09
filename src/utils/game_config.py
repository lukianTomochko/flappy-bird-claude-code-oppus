import os

import pygame

from .difficulty import Difficulty
from .fonts import Fonts
from .highscore import HighScores
from .images import Images
from .sounds import Sounds
from .window import Window

# DEBUG values that switch the overlay on; anything else (including "0",
# "false" and an empty variable) leaves it off
DEBUG_ON = frozenset({"1", "true", "yes", "on"})


class GameConfig:
    def __init__(
        self,
        screen: pygame.Surface,
        clock: pygame.time.Clock,
        fps: int,
        window: Window,
        images: Images,
        sounds: Sounds,
        fonts: Fonts,
        difficulty: Difficulty,
        high_scores: HighScores,
    ) -> None:
        self.screen = screen
        self.clock = clock
        self.fps = fps
        self.window = window
        self.images = images
        self.sounds = sounds
        self.fonts = fonts
        self.difficulty = difficulty
        self.high_scores = high_scores
        self.debug = os.environ.get("DEBUG", "").strip().lower() in DEBUG_ON

    def tick(self) -> None:
        self.clock.tick(self.fps)
