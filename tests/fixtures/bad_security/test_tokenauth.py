import unittest

from tokenauth import verify_token


class TestVerifyToken(unittest.TestCase):
    def test_matching_token_authenticates(self):
        self.assertTrue(verify_token("s3cr3t-token-abc123", "s3cr3t-token-abc123"))

    def test_mismatched_token_is_rejected(self):
        self.assertFalse(verify_token("wrong-token", "s3cr3t-token-abc123"))

    def test_empty_provided_token_is_rejected(self):
        self.assertFalse(verify_token("", "s3cr3t-token-abc123"))

    def test_empty_expected_token_is_rejected(self):
        self.assertFalse(verify_token("s3cr3t-token-abc123", ""))


if __name__ == "__main__":
    unittest.main()
