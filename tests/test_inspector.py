import unittest

from suite.inspector import metric, top_by_metric


class MetricTests(unittest.TestCase):

    def test_passes_int_through(self):
        self.assertEqual(metric(42), 42)

    def test_passes_float_through(self):
        self.assertEqual(metric(1.5), 1.5)

    def test_returns_zero_for_bool(self):
        # bool is a subclass of int in Python; True would otherwise sort as 1.
        self.assertEqual(metric(True), 0)
        self.assertEqual(metric(False), 0)

    def test_returns_zero_for_none_string_dict(self):
        self.assertEqual(metric(None), 0)
        self.assertEqual(metric("nope"), 0)
        self.assertEqual(metric({}), 0)
        self.assertEqual(metric([]), 0)


class TopByMetricTests(unittest.TestCase):

    def test_sorts_desc_by_primary(self):
        rows = [
            {"task_id": "a", "score": 1},
            {"task_id": "b", "score": 9},
            {"task_id": "c", "score": 5},
        ]
        result = top_by_metric(rows, "score")
        self.assertEqual([r["task_id"] for r in result], ["b", "c", "a"])

    def test_uses_secondary_for_ties(self):
        rows = [
            {"task_id": "a", "primary": 5, "secondary": 1},
            {"task_id": "b", "primary": 5, "secondary": 9},
            {"task_id": "c", "primary": 5, "secondary": 3},
        ]
        result = top_by_metric(rows, "primary", secondary_keys=("secondary",))
        self.assertEqual([r["task_id"] for r in result], ["b", "c", "a"])

    def test_uses_tiebreak_key_for_full_tie(self):
        # When all metrics tie, reverse=True on the sort tuple means
        # alphabetical-later wins (e.g. "z" before "a"). This preserves the
        # hand-rolled behavior of the original code.
        rows = [
            {"task_id": "alpha", "score": 5},
            {"task_id": "zeta", "score": 5},
            {"task_id": "mid", "score": 5},
        ]
        result = top_by_metric(rows, "score")
        self.assertEqual([r["task_id"] for r in result], ["zeta", "mid", "alpha"])

    def test_respects_limit(self):
        rows = [{"task_id": str(i), "score": i} for i in range(10)]
        result = top_by_metric(rows, "score", limit=3)
        self.assertEqual(len(result), 3)
        self.assertEqual([r["task_id"] for r in result], ["9", "8", "7"])

    def test_handles_missing_keys(self):
        rows = [
            {"task_id": "a", "score": 5},
            {"task_id": "b"},  # missing 'score'
            {"task_id": "c", "score": 3},
        ]
        result = top_by_metric(rows, "score")
        # Missing key -> metric() returns 0 -> sorts to bottom.
        # Tiebreak among missing-score rows uses reverse-alphabetical task_id.
        self.assertEqual([r["task_id"] for r in result], ["a", "c", "b"])

    def test_returns_empty_for_empty_input(self):
        self.assertEqual(top_by_metric([], "score"), [])


if __name__ == "__main__":
    unittest.main()
