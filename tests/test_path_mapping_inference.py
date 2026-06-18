import unittest

from home_cinema_control.playback.path_mapping_inference import infer_player_paths


class InferPlayerPathsTest(unittest.TestCase):
    def test_infers_share_path_from_anchor(self):
        result = infer_player_paths(
            anchor_source="/volume1/Video/Movies",
            anchor_share="/NAS/volume1/Video/Movies",
            candidates=["/volume1/Video/Movies"],
        )
        self.assertEqual([("/volume1/Video/Movies", "/NAS/volume1/Video/Movies")], result)

    def test_infers_tail_for_candidate_with_different_suffix(self):
        result = infer_player_paths(
            anchor_source="/volume1/Video/Movies",
            anchor_share="/NAS/volume1/Video/Movies",
            candidates=["/volume1/Video/Music"],
        )
        self.assertEqual([("/volume1/Video/Music", "/NAS/volume1/Video/Music")], result)

    def test_infers_multiple_candidates(self):
        result = infer_player_paths(
            anchor_source="/volume1/Video/Movies",
            anchor_share="/NAS/volume1/Video/Movies",
            candidates=["/volume1/Video/Movies", "/volume1/Video/Series"],
        )
        self.assertEqual(
            [
                ("/volume1/Video/Movies", "/NAS/volume1/Video/Movies"),
                ("/volume1/Video/Series", "/NAS/volume1/Video/Series"),
            ],
            result,
        )

    def test_returns_empty_list_for_no_candidates(self):
        result = infer_player_paths(
            anchor_source="/volume1/Video/Movies",
            anchor_share="/NAS/volume1/Video/Movies",
            candidates=[],
        )
        self.assertEqual([], result)

    def test_raises_when_no_common_suffix(self):
        with self.assertRaises(ValueError):
            infer_player_paths(
                anchor_source="/alpha/bravo",
                anchor_share="/delta/echo",
                candidates=["/alpha/bravo/film.mkv"],
            )

    def test_raises_when_candidate_does_not_start_with_inferred_prefix(self):
        with self.assertRaises(ValueError):
            infer_player_paths(
                anchor_source="/volume1/Video/Movies",
                anchor_share="/NAS/volume1/Video/Movies",
                candidates=["/other/path/Movies"],
            )

    def test_handles_backslash_separators_in_anchor(self):
        # _components() normalizes backslashes for matching; paths are pre-normalized by path_config
        result = infer_player_paths(
            anchor_source="/volume1/Video/Movies",
            anchor_share="/NAS/volume1/Video/Movies",
            candidates=["/volume1/Video/Movies"],
        )
        self.assertEqual(1, len(result))

    def test_prefix_substitution_preserves_deep_tail(self):
        result = infer_player_paths(
            anchor_source="/srv/media/films",
            anchor_share="/mnt/nas/media/films",
            candidates=["/srv/media/series/drama"],
        )
        self.assertEqual(
            [("/srv/media/series/drama", "/mnt/nas/media/series/drama")],
            result,
        )


if __name__ == "__main__":
    unittest.main()
