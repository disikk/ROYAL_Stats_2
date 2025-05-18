import os
import sys
import tempfile
import types
import importlib
import unittest
from unittest.mock import patch


def load_main_window_with_stubs():
    qtw = types.SimpleNamespace()
    class Dummy:
        def __init__(self, *a, **k):
            pass
        def setWindowModality(self, *a, **k):
            pass
        def setMinimumDuration(self, *a, **k):
            pass
        def setMaximum(self, *a, **k):
            pass
        def wasCanceled(self):
            return False
        def setLabelText(self, *a, **k):
            pass
        def setValue(self, *a, **k):
            pass
        def close(self):
            pass

    for name in [
        'QProgressDialog', 'QDialog', 'QWidget', 'QVBoxLayout',
        'QListWidget', 'QLabel', 'QPushButton', 'QHBoxLayout', 'QLineEdit',
        'QListWidgetItem', 'QMessageBox', 'QMainWindow', 'QStatusBar',
        'QToolBar', 'QTabWidget', 'QFileDialog', 'QInputDialog'
    ]:
        setattr(qtw, name, type(name, (Dummy,), {}))

    class QApplication(Dummy):
        @staticmethod
        def processEvents(*a, **k):
            pass

    qtw.QApplication = QApplication
    qtcore = types.SimpleNamespace(
        Qt=types.SimpleNamespace(WindowModality=types.SimpleNamespace(WindowModal=1)),
        QSize=type('QSize', (), {})
    )
    qtgui = types.SimpleNamespace(QIcon=type('QIcon', (), {}))
    qtmod = types.ModuleType('PyQt6')
    qtmod.QtWidgets = qtw
    qtmod.QtGui = qtgui
    qtmod.QtCore = qtcore
    sys.modules['PyQt6'] = qtmod
    sys.modules['PyQt6.QtWidgets'] = qtw
    sys.modules['PyQt6.QtGui'] = qtgui
    sys.modules['PyQt6.QtCore'] = qtcore

    app_style = types.ModuleType('ui.app_style')
    app_style.apply_dark_theme = lambda *a, **k: None
    sys.modules['ui.app_style'] = app_style

    config = types.ModuleType('config')
    config.APP_TITLE = 'test'
    config.DB_PATH = 'db'
    config.MIN_FINAL_TABLE_BLIND = 50
    config.HERO_NAME = 'Hero'
    sys.modules['config'] = config

    sys.modules['db.database'] = types.ModuleType('db.database')
    sys.modules['db.database'].DatabaseManager = type('DB', (), {})
    repo_mod = types.ModuleType('db.repositories')
    class Repo:
        pass
    repo_mod.TournamentRepository = Repo
    repo_mod.KnockoutRepository = Repo
    repo_mod.SessionRepository = Repo
    repo_mod.StatsRepository = Repo
    sys.modules['db.repositories'] = repo_mod

    for name in ['ui.stats_grid', 'ui.tournament_view', 'ui.knockout_table', 'ui.session_view']:
        mod = types.ModuleType(name)
        setattr(mod, name.split('.')[-1].title().replace('_', ''), type('X', (), {}))
        sys.modules[name] = mod

    return importlib.import_module('ui.main_window')


class TestParseFilesSkip(unittest.TestCase):
    def test_skips_files_without_id(self):
        mw_mod = load_main_window_with_stubs()
        MainWindow = mw_mod.MainWindow
        mw = MainWindow.__new__(MainWindow)

        class DummyRepo:
            def __init__(self):
                self.ids = []
            def get_hero_tournament(self, *a, **k):
                return {}
            def add_or_update_tournament(self, tournament_id, **kwargs):
                self.ids.append(tournament_id)
        mw.tournament_repo = DummyRepo()
        mw.refresh_all_data = lambda: None

        with tempfile.TemporaryDirectory() as tmpdir:
            hh_missing = os.path.join(tmpdir, 'hh_missing.txt')
            with open(hh_missing, 'w') as f:
                f.write('Poker Hand #1\nNo tid')
            summary_missing = os.path.join(tmpdir, 'summary_missing.txt')
            with open(summary_missing, 'w') as f:
                f.write('No id here')
            hh_ok = os.path.join(tmpdir, 'hh_ok.txt')
            with open(hh_ok, 'w') as f:
                f.write('Poker Hand #2\n')

            with patch.object(mw_mod, 'HandHistoryParser') as hh_cls, \
                 patch.object(mw_mod, 'TournamentSummaryParser') as sum_cls:
                hh_instance = hh_cls.return_value
                hh_instance.parse.side_effect = [
                    {'tournament_id': None, 'hero_ko_count': 0},
                    {'tournament_id': '333', 'hero_ko_count': 0}
                ]
                sum_cls.return_value.parse.return_value = {'tournament_id': None}

                mw._parse_files([hh_missing, summary_missing, hh_ok])

        self.assertEqual(mw.tournament_repo.ids, ['333'])


if __name__ == '__main__':
    unittest.main()
