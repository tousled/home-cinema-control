import time

from home_cinema_control.playback.timing import PlaybackStartupTimer


def test_snapshot_returns_total_and_steps_without_mutating_timer():
    timer = PlaybackStartupTimer()

    with timer.measure_step("example"):
        time.sleep(0.001)

    first = timer.snapshot()
    second = timer.snapshot()

    assert first.steps == second.steps
    assert first.steps[0].name == "example"
    assert first.steps[0].elapsed_seconds > 0
    assert second.total_elapsed_seconds >= first.total_elapsed_seconds
