import unittest
from parsers.tournament_summary import TournamentSummaryParser


class TestTournamentSummaryParser(unittest.TestCase):
    def test_parse_returns_expected_keys(self):
        content = (
            "PokerStars Tournament #1234567 $10\n"
            "You finished the tournament in 2nd place\n"
            "You received a total of $20\n"
            "Tournament started 2023/05/20 18:00:00\n"
        )
        parser = TournamentSummaryParser()
        result = parser.parse(content, filename="Tournament #1234567 Summary.txt")
        expected_keys = {"tournament_id", "place", "payout", "buyin", "date"}
        self.assertEqual(set(result.keys()), expected_keys)
        self.assertEqual(result["tournament_id"], "1234567")
        self.assertEqual(result["place"], 2)
        self.assertEqual(result["payout"], 20.0)
        self.assertEqual(result["buyin"], 10.0)
        self.assertEqual(result["date"], "2023/05/20 18:00:00")


if __name__ == "__main__":
    unittest.main()
