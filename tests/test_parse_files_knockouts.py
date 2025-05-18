import os
import tempfile
import unittest
from unittest.mock import patch

from tests.test_parse_files_skip import load_main_window_with_stubs


class TestParseFilesKnockouts(unittest.TestCase):
    def test_adds_knockouts_from_hh(self):
        mw_mod = load_main_window_with_stubs()
        MainWindow = mw_mod.MainWindow
        mw = MainWindow.__new__(MainWindow)

        class DummyTRepo:
            def get_hero_tournament(self, *a, **k):
                return {}
            def add_or_update_tournament(self, *a, **k):
                pass
        class DummyKORepo:
            def __init__(self):
                self.calls = []
            def add_knockout(self, tournament_id, hand_idx, split=False):
                self.calls.append((tournament_id, hand_idx, split))
        mw.tournament_repo = DummyTRepo()
        mw.knockout_repo = DummyKORepo()
        mw.refresh_all_data = lambda: None

        with tempfile.TemporaryDirectory() as tmpdir:
            hh_file = os.path.join(tmpdir, 'hh.txt')
            with open(hh_file, 'w') as f:
                f.write('Poker Hand #1\n')
            with patch.object(mw_mod, 'HandHistoryParser') as hh_cls, \
                 patch.object(mw_mod, 'TournamentSummaryParser') as sum_cls:
                hh_instance = hh_cls.return_value
                hh_instance.parse.return_value = {
                    'tournament_id': '123',
                    'hero_ko_count': 3,
                    'hands': [
                        {'hand_idx': 0, 'hero_ko': 2},
                        {'hand_idx': 1, 'hero_ko': 1},
                    ],
                }
                sum_cls.return_value.parse.return_value = {'tournament_id': None}

                mw._parse_files([hh_file])

        self.assertEqual(mw.knockout_repo.calls,
                         [('123', 0, False), ('123', 0, False), ('123', 1, False)])


if __name__ == '__main__':
    unittest.main()
