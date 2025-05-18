import os
import unittest
from parsers.hand_history import HandHistoryParser
from parsers.tournament_summary import TournamentSummaryParser


class TestTournamentIDExamples(unittest.TestCase):
    def test_hand_history_example_has_correct_id(self):
        path = os.path.join('hh_examples', 'GG20250515-2149 - 11 - 0.4 - 0.8 - 9max.txt')
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        result = HandHistoryParser().parse(content)
        self.assertEqual(result['tournament_id'], '206997317')

    def test_summary_example_has_correct_id(self):
        path = os.path.join('hh_examples', 'GG20250515 - Tournament #206881959 - Mystery Battle Royale 10.txt')
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        result = TournamentSummaryParser().parse(content, filename=os.path.basename(path))
        self.assertEqual(result['tournament_id'], '206881959')


if __name__ == '__main__':
    unittest.main()
