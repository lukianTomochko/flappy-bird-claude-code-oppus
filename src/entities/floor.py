from ..utils import GameConfig
from .entity import Entity


class Floor(Entity):
    def __init__(self, config: GameConfig) -> None:
        super().__init__(config, config.images.base, 0, config.window.vh)
        self.stopped = False
        self.vel_x = config.difficulty.floor_speed
        self.x_extra = self.w - config.window.w

    def stop(self) -> None:
        self.stopped = True
        self.vel_x = 0

    def draw(self) -> None:
        if not self.stopped:
            # scroll in step with the pipes so the parallax stays believable
            self.vel_x = self.config.difficulty.floor_speed
        self.x = -((-self.x + self.vel_x) % self.x_extra)
        super().draw()
