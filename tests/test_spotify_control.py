import unittest
from unittest.mock import patch

from spicetifix.core import spotify_control as sc


class TestMediaKeys(unittest.TestCase):
    @patch("spicetifix.core.spotify_control._send_key")
    def test_play_pause_sends_play_pause_key(self, mock_send):
        sc.play_pause()
        mock_send.assert_called_once_with(sc.VK_MEDIA_PLAY_PAUSE)

    @patch("spicetifix.core.spotify_control._send_key")
    def test_next_and_prev_send_their_keys(self, mock_send):
        sc.next_track()
        mock_send.assert_called_with(sc.VK_MEDIA_NEXT_TRACK)
        sc.prev_track()
        mock_send.assert_called_with(sc.VK_MEDIA_PREV_TRACK)


class TestNonWindowsBehaviour(unittest.TestCase):
    @patch("spicetifix.core.spotify_control.sys")
    def test_send_key_is_a_noop(self, mock_sys):
        mock_sys.platform = "linux"
        sc._send_key(sc.VK_MEDIA_PLAY_PAUSE)  # must not raise

    @patch("spicetifix.core.spotify_control.sys")
    def test_now_playing_reports_inactive(self, mock_sys):
        mock_sys.platform = "linux"
        res = sc.get_spotify_now_playing()
        self.assertFalse(res["playing"])
        self.assertEqual(res["raw"], "")
        self.assertIn("title", res)


if __name__ == "__main__":
    unittest.main()
