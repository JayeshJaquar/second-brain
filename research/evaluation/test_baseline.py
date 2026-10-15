import unittest
from baseline import BM25, metrics


class RankingChecks(unittest.TestCase):
    def test_partial_recall_and_rank(self):
        self.assertEqual(metrics(["wrong", "a", "other"], ["a", "b"]), (0.5, 0.5))

    def test_empty_results(self):
        self.assertEqual(metrics([], ["a"]), (0, 0))

    def test_duplicate_results_not_double_counted(self):
        self.assertEqual(metrics(["a", "a"], ["a", "b"]), (0.5, 1))

    def test_cutoff(self):
        self.assertEqual(metrics(["x", "y", "a"], ["a"], k=2), (0, 0))

    def test_no_match_and_empty_corpus(self):
        self.assertEqual(BM25([]).search("recursion"), [])
        index = BM25([{"id": "a", "text": "base case recursion"}, {"id": "b", "text": ""}])
        self.assertEqual(index.search("unrelated"), [])
        self.assertEqual(index.search("BASE")[0][0], "a")


if __name__ == "__main__":
    unittest.main()
