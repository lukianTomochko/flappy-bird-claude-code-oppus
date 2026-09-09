"""Feature 2: dynamic difficulty and its visual indicator."""

import pytest

from src.entities import Floor, Pipes
from src.utils import Difficulty
from src.utils.difficulty import FLOOR_SPEED_RATIO


def settle(difficulty, limit=1000):
    """Runs frames until the eased speed reaches its target."""
    frames = 0
    while difficulty.speed != difficulty.target_speed and frames < limit:
        difficulty.tick()
        frames += 1
    return frames


@pytest.mark.parametrize(
    "pipes_passed, level, name",
    [
        (0, 1, "CRUISING"),  # start of the game
        (4, 1, "CRUISING"),  # one short of the first step up
        (5, 2, "BREEZY"),  # exactly on the boundary
        (9, 2, "BREEZY"),
        (10, 3, "GUSTY"),
        (25, 6, "INSANITY"),  # last level defined
        (500, 6, "INSANITY"),  # far beyond it, clamped
    ],
)
def test_level_advances_every_five_pipes(pipes_passed, level, name):
    """Normal and boundary cases for the every-5-pipes rule."""
    difficulty = Difficulty()

    difficulty.update(pipes_passed)

    assert (difficulty.level, difficulty.name) == (level, name)
    assert difficulty.progress == pytest.approx(
        1.0 if difficulty.is_max_level else (pipes_passed % 5) / 5
    )
    assert 0.0 <= difficulty.intensity <= 1.0


def test_update_reports_level_ups_and_ignores_going_backwards():
    """Edge cases: the level-up signal fires once, and a score that
    somehow arrives lower must never demote the player."""
    difficulty = Difficulty()

    assert difficulty.update(4) is False
    assert difficulty.update(5) is True, "crossing 5 pipes is a level up"
    assert difficulty.update(6) is False, "no repeat signal inside a level"
    assert difficulty.update(10) is True

    assert difficulty.update(2) is False
    assert difficulty.level == 3, "a stale score cannot lower the level"

    difficulty.reset()
    assert (difficulty.level, difficulty.pipes_passed) == (1, 0)
    assert difficulty.speed == difficulty.base_speed


def test_speed_eases_up_smoothly_instead_of_jumping():
    """The point of the feature: no instant jump when the level changes."""
    difficulty = Difficulty()
    start = difficulty.speed

    difficulty.update(5)
    assert difficulty.speed == start, "the target moves before the speed does"

    difficulty.tick()
    first_step = difficulty.speed - start
    assert 0 < first_step < 0.2, "the first frame is a nudge, not a jump"

    speeds = [difficulty.speed]
    for _ in range(20):
        difficulty.tick()
        speeds.append(difficulty.speed)
    assert all(
        later > earlier for earlier, later in zip(speeds, speeds[1:])
    ), "speed only ever climbs towards the target"
    assert difficulty.speed < difficulty.target_speed, "still easing in"

    frames = settle(difficulty)
    assert 30 <= frames <= 240, f"reached the target in {frames} frames"
    assert difficulty.speed == difficulty.target_speed
    assert difficulty.speed_multiplier == pytest.approx(6.0 / 5.0)

    # the easing is stable once it has arrived
    difficulty.tick()
    assert difficulty.speed == difficulty.target_speed


def test_pipes_and_floor_follow_the_difficulty_speed(fake_config):
    """Integration: difficulty is the single source of truth for speed,
    and stopping the world is not undone by the next frame."""
    difficulty = fake_config.difficulty
    pipes = Pipes(fake_config)
    floor = Floor(fake_config)

    pipes.tick()
    floor.tick()
    assert {pipe.vel_x for pipe in pipes.upper + pipes.lower} == {
        -difficulty.speed
    }
    assert floor.vel_x == pytest.approx(difficulty.speed * FLOOR_SPEED_RATIO)

    difficulty.update(10)
    settle(difficulty)
    pipes.tick()
    floor.tick()
    assert {pipe.vel_x for pipe in pipes.upper + pipes.lower} == {-7.0}
    assert floor.vel_x == pytest.approx(7.0 * FLOOR_SPEED_RATIO)

    pipes.stop()
    floor.stop()
    pipes.tick()
    floor.tick()
    assert {pipe.vel_x for pipe in pipes.upper + pipes.lower} == {0}
    assert floor.vel_x == 0, "a stopped world stays stopped"


def test_pipes_spawn_wearing_the_current_level_colour(fake_config):
    """The visual indicator: new pipes are recoloured per level, and the
    recoloured sprites are cached rather than rebuilt for every pipe."""
    difficulty = fake_config.difficulty
    colors_used = fake_config.images.pipes_colored

    Pipes(fake_config)
    assert colors_used.call_args_list, "initial pipes ask for a colour"
    assert {call.args[0] for call in colors_used.call_args_list} == {
        difficulty.color
    }

    colors_used.reset_mock()
    difficulty.update(15)
    pipes = Pipes(fake_config)
    assert {call.args[0] for call in colors_used.call_args_list} == {
        difficulty.color
    }
    assert difficulty.color != Difficulty().color, "level 4 is not level 1"

    # pipes already on screen keep the colour they spawned with
    before = [pipe.image for pipe in pipes.upper]
    difficulty.update(20)
    pipes.tick()
    assert [pipe.image for pipe in pipes.upper][: len(before)] == before
