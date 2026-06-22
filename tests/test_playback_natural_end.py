import unittest

from home_cinema_control.playback.during.natural_end import (
    DEFAULT_NATURAL_END_MINIMUM_TOTAL_SECONDS,
    is_oppo_end_of_content,
    is_oppo_next_title_started,
    was_content_played,
)


class IsOppoEndOfContentTest(unittest.TestCase):
    def test_true_when_current_within_tolerance_of_total(self):
        self.assertTrue(
            is_oppo_end_of_content(
                current_seconds=9648,
                total_seconds=9658,
                tolerance_seconds=10,
                minimum_total_seconds=300,
            )
        )

    def test_true_when_current_at_or_past_total(self):
        self.assertTrue(
            is_oppo_end_of_content(
                current_seconds=9658,
                total_seconds=9658,
                tolerance_seconds=10,
                minimum_total_seconds=300,
            )
        )

    def test_false_when_current_before_tolerance_window(self):
        self.assertFalse(
            is_oppo_end_of_content(
                current_seconds=9000,
                total_seconds=9658,
                tolerance_seconds=10,
                minimum_total_seconds=300,
            )
        )

    def test_false_below_minimum_total_floor_even_at_end(self):
        # A 60s disc menu loop reaching its own end is not feature content.
        self.assertFalse(
            is_oppo_end_of_content(
                current_seconds=60,
                total_seconds=60,
                tolerance_seconds=10,
                minimum_total_seconds=300,
            )
        )

    def test_false_when_total_unknown(self):
        self.assertFalse(
            is_oppo_end_of_content(
                current_seconds=0,
                total_seconds=0,
                tolerance_seconds=10,
                minimum_total_seconds=300,
            )
        )


class IsOppoNextTitleStartedTest(unittest.TestCase):
    def test_true_when_total_changes_after_feature_near_end(self):
        # OPPO auto-advanced to a different file after the feature finished.
        self.assertTrue(
            is_oppo_next_title_started(
                previous_position_seconds=7754,
                previous_total_seconds=7756,
                current_total_seconds=5813,
                tolerance_seconds=10,
                minimum_total_seconds=300,
            )
        )

    def test_false_when_total_unchanged(self):
        # Same title still playing (e.g. a position blip) -> not a rollover.
        self.assertFalse(
            is_oppo_next_title_started(
                previous_position_seconds=7754,
                previous_total_seconds=7756,
                current_total_seconds=7756,
                tolerance_seconds=10,
                minimum_total_seconds=300,
            )
        )

    def test_false_when_previous_was_not_near_end(self):
        # Total changed mid-feature (not near the end) -> do not finish.
        self.assertFalse(
            is_oppo_next_title_started(
                previous_position_seconds=3000,
                previous_total_seconds=7756,
                current_total_seconds=5813,
                tolerance_seconds=10,
                minimum_total_seconds=300,
            )
        )

    def test_false_when_previous_below_floor(self):
        # A short menu/reel rolling onto something else is not a feature end.
        self.assertFalse(
            is_oppo_next_title_started(
                previous_position_seconds=60,
                previous_total_seconds=60,
                current_total_seconds=7756,
                tolerance_seconds=10,
                minimum_total_seconds=300,
            )
        )


class WasContentPlayedTest(unittest.TestCase):
    def test_true_at_or_above_threshold(self):
        # 90% of a 2h feature -> stopping anywhere in the credits counts.
        self.assertTrue(
            was_content_played(
                current_seconds=6480,
                total_seconds=7200,
                minimum_total_seconds=300,
                fraction_threshold=0.90,
            )
        )

    def test_false_below_threshold(self):
        self.assertFalse(
            was_content_played(
                current_seconds=3600,
                total_seconds=7200,
                minimum_total_seconds=300,
                fraction_threshold=0.90,
            )
        )

    def test_false_below_minimum_total_floor(self):
        # 59/60 of a menu loop is 98% but must not be marked watched.
        self.assertFalse(
            was_content_played(
                current_seconds=59,
                total_seconds=60,
                minimum_total_seconds=300,
                fraction_threshold=0.90,
            )
        )

    def test_false_when_total_unknown(self):
        self.assertFalse(
            was_content_played(
                current_seconds=0,
                total_seconds=0,
                minimum_total_seconds=300,
                fraction_threshold=0.90,
            )
        )

    def test_natural_end_position_is_also_played(self):
        # A natural-end position (within 10s of total) is always >= 90%.
        total = DEFAULT_NATURAL_END_MINIMUM_TOTAL_SECONDS
        self.assertTrue(
            was_content_played(
                current_seconds=total - 10,
                total_seconds=total,
            )
        )


if __name__ == "__main__":
    unittest.main()
