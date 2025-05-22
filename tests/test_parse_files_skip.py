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
        QSize=type('QSize', (), {}),
        pyqtSlot=lambda *a, **k: (lambda f: f),
        pyqtSignal=lambda *a, **k: type('Signal', (), {}),
        QThread=type('QThread', (), {})
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
    app_style.format_money = lambda *a, **k: ''
    app_style.format_percentage = lambda *a, **k: ''
    app_style.apply_cell_color_by_value = lambda *a, **k: None
    sys.modules['ui.app_style'] = app_style

    config = types.ModuleType('config')
    config.APP_TITLE = 'test'
    config.DB_PATH = 'db'
    config.MIN_FINAL_TABLE_BLIND = 50
    config.HERO_NAME = 'Hero'
    config.DEBUG = False
    sys.modules['config'] = config

    sys.modules['db.database'] = types.ModuleType('db.database')
    sys.modules['db.database'].DatabaseManager = type('DB', (), {})
    repo_mod = types.ModuleType('db.repositories')
    class Repo:
        pass
    repo_mod.TournamentRepository = Repo
    repo_mod.SessionRepository = Repo
    repo_mod.StatsRepository = Repo
    repo_mod.OverallStatsRepository = Repo
    repo_mod.PlaceDistributionRepository = Repo
    repo_mod.FinalTableHandRepository = Repo
    sys.modules['db.repositories'] = repo_mod

    for name in ['ui.stats_grid', 'ui.tournament_view', 'ui.session_view']:
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
        mw_mod.application_service.tournament_repo = mw.tournament_repo

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

            with patch.object(mw_mod.application_service, 'hh_parser') as hh_obj, \
                 patch.object(mw_mod.application_service, 'ts_parser') as sum_obj:
                hh_obj.parse.side_effect = [
                    {'tournament_id': None, 'hero_ko_count': 0},
                    {'tournament_id': '333', 'hero_ko_count': 0}
                ]
                sum_obj.parse.return_value = {'tournament_id': None}

                def fake_import(paths, *a, **k):
                    for p in paths:
                        with open(p, 'r') as f:
                            content = f.read()
                        if 'Poker Hand' in content or 'Hand #' in content:
                            data = hh_obj.parse(content)
                        else:
                            data = sum_obj.parse(content, filename=os.path.basename(p))
                        tid = data.get('tournament_id')
                        if tid:
                            mw.tournament_repo.add_or_update_tournament(tid)

                mw_mod.application_service.import_files = fake_import
                mw_mod.application_service.import_files([hh_missing, summary_missing, hh_ok], 's')

        self.assertEqual(mw.tournament_repo.ids, ['333'])


if __name__ == '__main__':
    unittest.main()
