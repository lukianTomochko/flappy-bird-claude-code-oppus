"""Dynamic difficulty: pipes get faster every few pipes passed.

Pure logic on purpose (no pygame import) so entities can read it and the
game loop can drive it without either owning the rules.
"""

from typing import NamedTuple, Sequence, Tuple


class Level(NamedTuple):
    name: str
    color: Tuple[int, int, int]
    pipe_speed: float


# pipes passed before the next level kicks in
PIPES_PER_LEVEL = 5
# floor scrolls slightly slower than the pipes, as in the original game (4/5)
FLOOR_SPEED_RATIO = 0.8
# fraction of the remaining speed gap closed per frame: eases the speed up
# over roughly a second instead of jumping the moment the level changes
SPEED_SMOOTHING = 0.045

LEVELS: Sequence[Level] = (
    Level("CRUISING", (96, 196, 104), 5.0),
    Level("BREEZY", (74, 176, 214), 6.0),
    Level("GUSTY", (232, 196, 62), 7.0),
    Level("STORMY", (232, 138, 48), 8.2),
    Level("FURIOUS", (222, 74, 74), 9.4),
    Level("INSANITY", (172, 92, 216), 10.6),
)


class Difficulty:
    def __init__(
        self,
        levels: Sequence[Level] = LEVELS,
        pipes_per_level: int = PIPES_PER_LEVEL,
        smoothing: float = SPEED_SMOOTHING,
    ) -> None:
        self.levels = levels
        self.pipes_per_level = max(1, pipes_per_level)
        self.smoothing = smoothing
        self.reset()

    def reset(self) -> None:
        self.index = 0
        self.pipes_passed = 0
        self.speed = self.levels[0].pipe_speed

    # ------------------------------------------------------------------
    # driving
    # ------------------------------------------------------------------
    def update(self, pipes_passed: int) -> bool:
        """Feeds the current score in; True when a new level just started."""
        self.pipes_passed = max(self.pipes_passed, int(pipes_passed))
        index = min(
            self.pipes_passed // self.pipes_per_level, len(self.levels) - 1
        )
        leveled_up = index > self.index
        self.index = index
        return leveled_up

    def tick(self) -> None:
        """Eases the live speed towards the current level's target speed."""
        gap = self.target_speed - self.speed
        if abs(gap) < 0.01:
            self.speed = self.target_speed
        else:
            self.speed += gap * self.smoothing

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------
    @property
    def level(self) -> int:
        return self.index + 1

    @property
    def name(self) -> str:
        return self.levels[self.index].name

    @property
    def color(self) -> Tuple[int, int, int]:
        return self.levels[self.index].color

    @property
    def target_speed(self) -> float:
        return self.levels[self.index].pipe_speed

    @property
    def base_speed(self) -> float:
        return self.levels[0].pipe_speed

    @property
    def floor_speed(self) -> float:
        return self.speed * FLOOR_SPEED_RATIO

    @property
    def speed_multiplier(self) -> float:
        return self.speed / self.base_speed

    @property
    def intensity(self) -> float:
        """0.0 on the first level, 1.0 on the last one."""
        if len(self.levels) < 2:
            return 1.0
        return self.index / (len(self.levels) - 1)

    @property
    def is_max_level(self) -> bool:
        return self.index >= len(self.levels) - 1

    @property
    def progress(self) -> float:
        """Progress towards the next level, in 0..1."""
        if self.is_max_level:
            return 1.0
        return (self.pipes_passed % self.pipes_per_level) / self.pipes_per_level

    @property
    def pipes_to_next_level(self) -> int:
        if self.is_max_level:
            return 0
        return self.pipes_per_level - (
            self.pipes_passed % self.pipes_per_level
        )
