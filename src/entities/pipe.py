import random
from typing import List

from ..utils import GameConfig
from .entity import Entity


class Pipe(Entity):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.vel_x = -self.config.difficulty.speed

    def draw(self) -> None:
        self.x += self.vel_x
        super().draw()


class Pipes(Entity):
    upper: List[Pipe]
    lower: List[Pipe]

    def __init__(self, config: GameConfig) -> None:
        super().__init__(config)
        self.pipe_gap = 120
        self.top = 0
        self.bottom = self.config.window.viewport_height
        self.stopped = False
        self.upper = []
        self.lower = []
        self.spawn_initial_pipes()

    def tick(self) -> None:
        if self.can_spawn_pipes():
            self.spawn_new_pipes()
        self.remove_old_pipes()
        self.sync_speed()

        for up_pipe, low_pipe in zip(self.upper, self.lower):
            up_pipe.tick()
            low_pipe.tick()

    def sync_speed(self) -> None:
        """Difficulty owns the pipe speed, pipes just follow it."""
        if self.stopped:
            return

        vel_x = -self.config.difficulty.speed
        for pipe in self.upper + self.lower:
            pipe.vel_x = vel_x

    def stop(self) -> None:
        self.stopped = True
        for pipe in self.upper + self.lower:
            pipe.vel_x = 0

    def can_spawn_pipes(self) -> bool:
        if not self.upper:
            return True

        last = self.upper[-1]
        return self.config.window.width - (last.x + last.w) > last.w * 2.5

    def spawn_new_pipes(self):
        # add new pipe when first pipe is about to touch left of screen
        upper, lower = self.make_random_pipes()
        self.upper.append(upper)
        self.lower.append(lower)

    def remove_old_pipes(self) -> None:
        """Drops the pipes that have scrolled off the left of the screen.

        Both lists are rebuilt from one decision instead of being filtered
        in place: removing from a list while iterating it skips the next
        element, and if the two lists ever dropped different counts they
        would desync, which ``tick``'s ``zip`` would silently hide.
        """
        keep = [
            index for index, pipe in enumerate(self.upper) if pipe.x >= -pipe.w
        ]
        if len(keep) == len(self.upper):
            return

        self.upper = [self.upper[index] for index in keep]
        self.lower = [self.lower[index] for index in keep]

    def spawn_initial_pipes(self):
        upper_1, lower_1 = self.make_random_pipes()
        upper_1.x = self.config.window.width + upper_1.w * 3
        lower_1.x = self.config.window.width + upper_1.w * 3
        self.upper.append(upper_1)
        self.lower.append(lower_1)

        upper_2, lower_2 = self.make_random_pipes()
        upper_2.x = upper_1.x + upper_1.w * 3.5
        lower_2.x = upper_1.x + upper_1.w * 3.5
        self.upper.append(upper_2)
        self.lower.append(lower_2)

    def make_random_pipes(self):
        """returns a randomly generated pipe"""
        # y of gap between upper and lower pipe
        base_y = self.config.window.viewport_height

        gap_y = random.randrange(0, int(base_y * 0.6 - self.pipe_gap))
        gap_y += int(base_y * 0.2)
        # pipes wear the colour of the difficulty level they spawned on, so
        # the level change washes across the screen instead of snapping
        upper_image, lower_image = self.config.images.pipes_colored(
            self.config.difficulty.color
        )
        pipe_height = upper_image.get_height()
        pipe_x = self.config.window.width + 10

        upper_pipe = Pipe(
            self.config,
            upper_image,
            pipe_x,
            gap_y - pipe_height,
        )

        lower_pipe = Pipe(
            self.config,
            lower_image,
            pipe_x,
            gap_y + self.pipe_gap,
        )

        return upper_pipe, lower_pipe
