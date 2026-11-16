import unittest
from unittest.mock import patch

import main


class TestSingleInstance(unittest.TestCase):
    @patch("main.sys")
    def test_never_second_instance_off_windows(self, mock_sys):
        mock_sys.platform = "linux"
        self.assertFalse(main._is_second_instance())


if __name__ == "__main__":
    unittest.main()
