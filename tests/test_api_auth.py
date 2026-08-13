import unittest

from spicetifix import api


def _make_handler(headers=None):
    h = object.__new__(api.SpicetifixAPIHandler)
    h.headers = headers or {}
    h.request = None
    h.client_address = ("127.0.0.1", 1234)
    return h


class TestApiAuth(unittest.TestCase):
    def setUp(self):
        api.set_auth_token("test-secret-token")

    def tearDown(self):
        api.set_auth_token("")

    def test_authorized_with_valid_token(self):
        h = _make_handler({"X-Auth-Token": "test-secret-token"})
        self.assertTrue(h._is_authorized())

    def test_unauthorized_with_wrong_token(self):
        h = _make_handler({"X-Auth-Token": "wrong-token"})
        self.assertFalse(h._is_authorized())

    def test_unauthorized_without_token(self):
        h = _make_handler({})
        self.assertFalse(h._is_authorized())

    def test_open_when_no_token_configured(self):
        api.set_auth_token("")
        h = _make_handler({})
        self.assertTrue(h._is_authorized())


class TestStaticFileTraversal(unittest.TestCase):
    def test_index_resolves(self):
        path = api._resolve_static_file("/")
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "index.html")

    def test_normal_asset_resolves(self):
        path = api._resolve_static_file("/app.js")
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "app.js")

    def test_traversal_rejected(self):
        self.assertIsNone(api._resolve_static_file("/../../../../Windows/win.ini"))

    def test_encoded_traversal_rejected(self):
        self.assertIsNone(api._resolve_static_file("/%2e%2e/%2e%2e/Windows/win.ini"))

    def test_absolute_path_rejected(self):
        self.assertIsNone(api._resolve_static_file("/C:/Windows/win.ini"))

    def test_unknown_file_returns_none(self):
        self.assertIsNone(api._resolve_static_file("/no_such_file_12345"))


class TestApiWorkingState(unittest.TestCase):
    def setUp(self):
        self._was_working = api._is_working
        self._logs = api._install_logs
        self._progress = api._install_progress
        api._is_working = False
        api._install_logs = []
        api._install_progress = 0.0

    def tearDown(self):
        api._is_working = self._was_working
        api._install_logs = self._logs
        api._install_progress = self._progress

    def test_begin_work_claims_slot(self):
        self.assertTrue(api._begin_work())
        self.assertFalse(api._begin_work())

    def test_end_work_releases_slot(self):
        api._begin_work()
        api._append_log("step 1")
        api._set_progress(0.5)
        api._end_work()
        self.assertTrue(api._begin_work())

    def test_begin_work_resets_logs_and_progress(self):
        api._append_log("old")
        api._set_progress(0.9)
        api._begin_work()
        is_working, progress, logs = api._get_state()
        self.assertTrue(is_working)
        self.assertEqual(progress, 0.0)
        self.assertEqual(logs, [])

    def test_get_state_returns_snapshot(self):
        api._begin_work()
        api._append_log("a")
        api._set_progress(0.3)
        is_working, progress, logs = api._get_state()
        self.assertTrue(is_working)
        self.assertEqual(progress, 0.3)
        self.assertEqual(logs, ["a"])


if __name__ == "__main__":
    unittest.main()
