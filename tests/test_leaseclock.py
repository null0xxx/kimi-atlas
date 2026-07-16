import unittest

from scripts import leaseclock


class TestStamp(unittest.TestCase):
    def test_token_and_deadline(self):
        lease = leaseclock.stamp("a", 0, now=1000)
        self.assertEqual(lease["token"], "a#0")
        self.assertEqual(lease["deadline"], 2800)

    def test_default_ttl_is_1800(self):
        lease = leaseclock.stamp("job", 3, now=0.0)
        self.assertEqual(lease["token"], "job#3")
        self.assertEqual(lease["deadline"], 1800)

    def test_custom_ttl(self):
        lease = leaseclock.stamp("x", 1, now=100.0, ttl_s=60)
        self.assertEqual(lease["deadline"], 160)

    def test_token_omits_timestamp_no_rotation(self):
        # Same job_id + attempts stamped at different wall-clocks yields
        # an identical token (the lease no-rotation invariant).
        a = leaseclock.stamp("j", 2, now=1000.0)
        b = leaseclock.stamp("j", 2, now=9999.0)
        self.assertEqual(a["token"], b["token"])


class TestExpired(unittest.TestCase):
    def test_returns_expired_job_ids(self):
        leases = {"a": {"deadline": 2800}, "b": {"deadline": 500}}
        self.assertEqual(leaseclock.expired(leases, now=1000), ["b"])

    def test_boundary_deadline_equals_now_is_expired(self):
        leases = {"a": {"deadline": 1000}}
        self.assertEqual(leaseclock.expired(leases, now=1000), ["a"])

    def test_deterministic_sorted_output(self):
        leases = {
            "zeta": {"deadline": 10},
            "alpha": {"deadline": 10},
            "mid": {"deadline": 10},
        }
        self.assertEqual(
            leaseclock.expired(leases, now=1000),
            ["alpha", "mid", "zeta"],
        )

    def test_none_expired(self):
        leases = {"a": {"deadline": 5000}, "b": {"deadline": 6000}}
        self.assertEqual(leaseclock.expired(leases, now=1000), [])

    def test_empty_leases(self):
        self.assertEqual(leaseclock.expired({}, now=1000), [])

    def test_malformed_lease_degrades_to_expired(self):
        # A lease missing a deadline is treated as already-expired (fail-safe:
        # reap it rather than let an unbounded turn run forever).
        leases = {"a": {}, "b": {"deadline": 9000}}
        self.assertEqual(leaseclock.expired(leases, now=1000), ["a"])


if __name__ == "__main__":
    unittest.main()
