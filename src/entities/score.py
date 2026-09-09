from typing import List

import pygame

from ..utils import GameConfig
from .entity import Entity


class Score(Entity):
    def __init__(self, config: GameConfig) -> None:
        super().__init__(config)
        self.y = self.config.window.height * 0.1
        self.score = 0

    def reset(self) -> None:
        self.score = 0

    def add(self) -> None:
        self.score += 1
        self.config.sounds.point.play()

    def digit_images(self) -> List[pygame.Surface]:
        """Digit sprites for the current score, left to right.

        Single source for ``rect`` and ``draw``, which used to derive the
        same list independently and could drift apart.
        """
        return [
            self.config.images.numbers[int(digit)] for digit in str(self.score)
        ]

    def digits_origin(self, images: List[pygame.Surface]) -> float:
        """Left edge that centres ``images`` horizontally."""
        width = sum(image.get_width() for image in images)
        return (self.config.window.width - width) / 2

    @property
    def rect(self) -> pygame.Rect:
        images = self.digit_images()
        w = sum(image.get_width() for image in images)
        h = max(image.get_height() for image in images)
        return pygame.Rect(self.digits_origin(images), self.y, w, h)

    def draw(self) -> None:
        """displays score in center of screen"""
        images = self.digit_images()
        x_offset = self.digits_origin(images)

        for image in images:
            self.config.screen.blit(image, (x_offset, self.y))
            x_offset += image.get_width()
