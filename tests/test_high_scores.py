"""Feature 1: the persisted top 5 high score table."""

import json
import os
from unittest.mock import patch

import pytest

from src.utils.highscore import HighScores


def read_file(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def test_submit_keeps_top_five_sorted_and_persists(scores_path):
    """Normal case: the best five of many runs survive, best first."""
    scores = HighScores(path=scores_path)

    ranks = [scores.submit(value) for value in (10, 3, 50, 7, 22, 1, 31)]

    assert [entry["score"] for entry in scores.top] == [50, 31, 22, 10, 7]
    assert scores.best == 50
    # 50 went straight to the top, 1 never made the table
    assert ranks == [1, 2, 1, 3, 2, None, 2]
    assert scores.last_rank == 2
    assert [entry["score"] for entry in read_file(scores_path)] == [
        50,
        31,
        22,
        10,
        7,
    ]
    # a fresh instance sees exactly what was written
    assert HighScores(path=scores_path).top == scores.top


def test_full_table_rejects_low_score_and_promotes_high_one(
    write_scores_file, scores_path, sample_entries
):
    """Boundary: a full table only moves for a score above its weakest."""
    write_scores_file(sample_entries)
    scores = HighScores(path=scores_path)
    assert [entry["score"] for entry in scores.top] == [41, 33, 27, 18, 9]

    assert scores.submit(9) is None, "ties must not displace the last entry"
    assert scores.submit(0) is None, "a scoreless run is not a high score"
    assert scores.last_rank is None
    assert len(scores.top) == 5

    assert scores.submit(10) == 5
    assert [entry["score"] for entry in scores.top] == [41, 33, 27, 18, 10]

    scores.begin_round()
    assert scores.last_rank is None, "highlight is cleared for the next run"


def test_missing_file_starts_an_empty_table(scores_path):
    """Edge case: the very first launch has nothing on disk."""
    assert not os.path.exists(scores_path)

    scores = HighScores(path=scores_path)

    assert scores.top == []
    assert scores.is_empty and scores.best == 0
    assert scores.error is None, "a first run is not a failure"
    assert not scores.read_only
    assert not os.path.exists(scores_path), "loading must not create the file"


def test_corrupted_file_is_reset_and_moved_aside(
    write_scores_file, scores_path
):
    """Exceptional case: half written or hand mangled JSON."""
    write_scores_file('[{"score": 12, "dat')

    scores = HighScores(path=scores_path)

    assert scores.top == []
    assert "corrupted" in scores.error
    assert os.path.exists(f"{scores_path}.corrupted"), "the bad file is kept"
    # the game keeps going and the next run saves normally
    assert scores.submit(6) == 1
    assert [entry["score"] for entry in read_file(scores_path)] == [6]


@pytest.mark.parametrize(
    "payload, expected",
    [
        ('{"score": 9}', []),  # an object where a list belongs
        ("", []),  # empty file
        ("[]", []),  # valid but empty table
        ("[25, 4]", [25, 4]),  # bare numbers from an older format
        ('[{"score": 8.9}]', [8]),  # floats are truncated
        ('[{"score": -5}, {"score": 0}]', []),  # nothing to celebrate
        ('[true, null, "40", {"score": "x"}]', []),  # junk of every kind
        ('[{"score": 7, "date": 2024}]', [7]),  # wrong type of date
        ('[{"nope": 1}]', []),  # missing the score key
    ],
)
def test_malformed_content_is_sanitized(
    write_scores_file, scores_path, payload, expected
):
    """Exceptional values: the table survives any content in the file."""
    write_scores_file(payload)

    scores = HighScores(path=scores_path)

    assert [entry["score"] for entry in scores.top] == expected
    assert all(isinstance(entry["date"], str) for entry in scores.top)
    assert not scores.read_only, "unreadable content is still writable"


def test_unwritable_file_degrades_to_an_in_memory_table(scores_path):
    """Exceptional case: no permission to write the score file."""
    scores = HighScores(path=scores_path)

    with patch(
        "src.utils.highscore.os.replace",
        side_effect=PermissionError(13, "Access is denied"),
    ) as replace:
        rank = scores.submit(15)

    assert rank == 1, "the run still counts for this session"
    assert scores.best == 15
    assert scores.read_only
    assert "could not save high scores" in scores.error
    assert replace.called
    assert not os.path.exists(scores_path)
    assert os.listdir(os.path.dirname(scores_path)) == [], (
        "the temporary file must be cleaned up"
    )

    # once known unwritable, saving is not retried every single round
    with patch("src.utils.highscore.tempfile.mkstemp") as mkstemp:
        assert scores.save() is False
        mkstemp.assert_not_called()


def test_unreadable_file_is_never_overwritten(
    write_scores_file, scores_path, sample_entries
):
    """Exceptional case: an existing table we are not allowed to read must
    not be clobbered by an empty one."""
    write_scores_file(sample_entries)

    with patch(
        "builtins.open", side_effect=PermissionError(13, "Access is denied")
    ):
        scores = HighScores(path=scores_path)

    assert scores.top == []
    assert scores.read_only
    assert "could not read high scores" in scores.error

    assert scores.submit(99) == 1
    assert scores.save() is False
    # the real file on disk is untouched
    assert [entry["score"] for entry in read_file(scores_path)] == [
        18,
        41,
        9,
        27,
        33,
    ]
