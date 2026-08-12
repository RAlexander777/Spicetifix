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


if __name__ == "__main__":
    unittest.main()
