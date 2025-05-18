from PyQt6 import QtWidgets, QtGui, QtCore
from ui.app_style import apply_dark_theme
import sys
import config
from db.database import DatabaseManager
from db.repositories import (
    TournamentRepository,
    KnockoutRepository,
    SessionRepository,
    StatsRepository,
)
from ui.stats_grid import StatsGrid
from ui.tournament_view import TournamentView
from ui.knockout_table import KnockoutTable
from ui.session_view import SessionView

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_TITLE)
        self.setMinimumSize(1200, 800)
        self.db_path = config.DB_PATH

        self._init_repos()
        self._init_ui()
        self.refresh_all_data()

    def _init_repos(self):
        """Создаёт менеджер БД и репозитории (пересоздаётся при смене БД)"""
        self.db_manager = DatabaseManager(self.db_path)
        self.tournament_repo = TournamentRepository(self.db_manager)
        self.knockout_repo = KnockoutRepository(self.db_manager)
        self.session_repo = SessionRepository(self.db_manager)
        self.stats_repo = StatsRepository(self.db_manager)

    def _init_ui(self):
        # Главный layout — QTabWidget
        central_widget = QtWidgets.QWidget(self)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # Добавляем строку состояния
        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(f"Подключена база данных: {self.db_path}")

        # Верхняя панель инструментов
        toolbar = QtWidgets.QToolBar("Панель инструментов")
        toolbar.setIconSize(QtCore.QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Кнопки панели инструментов
        refresh_action = QtGui.QAction(QtGui.QIcon.fromTheme("view-refresh"), "Обновить все", self)
        refresh_action.triggered.connect(self.refresh_all_data)
        toolbar.addAction(refresh_action)
        
        db_action = QtGui.QAction(QtGui.QIcon.fromTheme("document-open"), "Открыть БД", self)
        db_action.triggered.connect(self.choose_database)
        toolbar.addAction(db_action)
        
        toolbar.addSeparator()
        
        # Информационные Label с количеством турниров и прибылью
        self.tournaments_info = QtWidgets.QLabel("Турниров: 0")
        self.tournaments_info.setStyleSheet("font-weight: bold; margin: 0 10px;")
        toolbar.addWidget(self.tournaments_info)
        
        self.profit_info = QtWidgets.QLabel("Прибыль: 0.00 ₽")
        self.profit_info.setStyleSheet("font-weight: bold; margin: 0 10px;")
        toolbar.addWidget(self.profit_info)

        # QTabWidget с красивыми иконками на вкладках
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # 1. Дашборд Hero (статы и гистограмма)
        self.stats_grid = StatsGrid(self.stats_repo, self.tournament_repo, self.knockout_repo, self.session_repo)
        self.tabs.addTab(self.stats_grid, QtGui.QIcon.fromTheme("office-chart-bar"), "Дашборд")

        # 2. Турниры Hero
        self.tournament_view = TournamentView(self.tournament_repo)
        self.tabs.addTab(self.tournament_view, QtGui.QIcon.fromTheme("view-list-details"), "Турниры")

        # 3. KO Hero
        self.knockout_table = KnockoutTable(self.knockout_repo)
        self.tabs.addTab(self.knockout_table, QtGui.QIcon.fromTheme("view-media-artist"), "Нокауты")

        # 4. Сессии Hero
        self.session_view = SessionView(self.session_repo)
        self.tabs.addTab(self.session_view, QtGui.QIcon.fromTheme("x-office-calendar"), "Сессии")

        # Подключаем сигнал изменения вкладки
        self.tabs.currentChanged.connect(self.tab_changed)
        
        # Добавляем метку версии в нижний правый угол
        version_layout = QtWidgets.QHBoxLayout()
        version_label = QtWidgets.QLabel(f"v{config.APP_VERSION}")
        version_label.setStyleSheet("color: #777; font-size: 9px;")
        version_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignBottom)
        version_layout.addStretch()
        version_layout.addWidget(version_label)
        main_layout.addLayout(version_layout)

        # Упрощенное меню приложения
        self._init_menu()

    def _init_menu(self):
        """Создает упрощенное главное меню приложения"""
        menubar = self.menuBar()
        
        # Меню "Файл"
        file_menu = menubar.addMenu("&Файл")
        
        # Действие "Открыть БД"
        open_db_action = QtGui.QAction(QtGui.QIcon.fromTheme("document-open"), "&Открыть базу данных...", self)
        open_db_action.setShortcut("Ctrl+O")
        open_db_action.setStatusTip("Открыть другую базу данных")
        open_db_action.triggered.connect(self.choose_database)
        file_menu.addAction(open_db_action)
        
        # Действие "Обновить"
        refresh_action = QtGui.QAction(QtGui.QIcon.fromTheme("view-refresh"), "&Обновить данные", self)
        refresh_action.setShortcut("F5")
        refresh_action.setStatusTip("Обновить все данные")
        refresh_action.triggered.connect(self.refresh_all_data)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        # Действие "Выход"
        exit_action = QtGui.QAction(QtGui.QIcon.fromTheme("application-exit"), "&Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Выйти из приложения")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def choose_database(self):
        # Диалог выбора файла БД
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Открыть базу данных", 
            ".", 
            "SQLite DB (*.db);;Все файлы (*)"
        )
        if fname:
            self.db_path = fname
            config.set_db_path(fname)
            self._init_repos()
            self.refresh_all_data()
            self.statusBar.showMessage(f"Подключена база данных: {self.db_path}")

    def refresh_all_data(self):
        # Показываем индикатор загрузки
        self.statusBar.showMessage("Обновление данных...")
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        
        # Обновить все вкладки
        self.stats_grid.reload()
        self.tournament_view.reload()
        self.knockout_table.reload()
        self.session_view.reload()
        
        # Обновляем информацию в тулбаре
        self._update_toolbar_info()
        
        # Возвращаем курсор и статусную строку
        QtWidgets.QApplication.restoreOverrideCursor()
        self.statusBar.showMessage(f"Данные обновлены. База данных: {self.db_path}", 3000)  # Показываем на 3 секунды

    def _update_toolbar_info(self):
        """Обновляет информацию в панели инструментов"""
        # Получаем данные
        tournaments = self.tournament_repo.get_all_hero_tournaments()
        
        # Обновляем количество турниров
        self.tournaments_info.setText(f"Турниров: {len(tournaments)}")
        
        # Считаем общую прибыль
        total_buyin = sum(float(t.get("buyin", 0)) for t in tournaments)
        total_payout = sum(float(t.get("payout", 0)) for t in tournaments)
        profit = total_payout - total_buyin
        
        # Форматируем и отображаем прибыль
        from ui.app_style import format_money
        self.profit_info.setText(f"Прибыль: {format_money(profit, with_plus=True)}")
        
        # Окрашиваем прибыль
        if profit > 0:
            self.profit_info.setStyleSheet("font-weight: bold; margin: 0 10px; color: #2ecc71;")
        elif profit < 0:
            self.profit_info.setStyleSheet("font-weight: bold; margin: 0 10px; color: #e74c3c;")
        else:
            self.profit_info.setStyleSheet("font-weight: bold; margin: 0 10px;")

    def tab_changed(self, index):
        """Обрабатывает событие изменения активной вкладки"""
        # Можно добавить здесь дополнительную логику при переключении вкладок
        tab_name = self.tabs.tabText(index)
        self.statusBar.showMessage(f"Вкладка: {tab_name}", 2000)

    def run(self):
        # Создаем экземпляр приложения
        app = QtWidgets.QApplication(sys.argv)
        
        # Применяем темную тему
        apply_dark_theme(app)
        
        # Показываем главное окно
        self.show()
        
        # Запускаем цикл событий
        sys.exit(app.exec())

if __name__ == "__main__":
    mw = MainWindow()
    mw.run()