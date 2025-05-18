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
import os
from ui.stats_grid import StatsGrid
from ui.tournament_view import TournamentView
from ui.knockout_table import KnockoutTable
from ui.session_view import SessionView

# --- Парсеры ---
from parsers.hand_history import HandHistoryParser
from parsers.tournament_summary import TournamentSummaryParser

import sqlite3
import re # Ensure re is imported

class DatabaseManagementDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, current_db_path=""):
        super().__init__(parent)
        self.setWindowTitle("Управление базами данных")
        self.parent_window = parent
        self.current_db_path = current_db_path
        self.selected_db_to_open = None
        self.new_db_to_create = None

        layout = QtWidgets.QVBoxLayout(self)

        # List existing databases
        self.db_list_widget = QtWidgets.QListWidget()
        self.populate_db_list()
        self.db_list_widget.itemDoubleClicked.connect(self.accept_selection) # Double click to open
        layout.addWidget(QtWidgets.QLabel("Существующие базы данных (в папке 'databases'):"))
        layout.addWidget(self.db_list_widget)

        # Select and Open button
        self.open_button = QtWidgets.QPushButton("Открыть выбранную")
        self.open_button.clicked.connect(self.accept_selection)
        layout.addWidget(self.open_button)
        
        layout.addSpacing(20)

        # Create new database
        new_db_layout = QtWidgets.QHBoxLayout()
        self.new_db_name_edit = QtWidgets.QLineEdit()
        self.new_db_name_edit.setPlaceholderText("Имя новой БД (например, my_new_stats)")
        new_db_layout.addWidget(self.new_db_name_edit)
        
        self.create_db_button = QtWidgets.QPushButton("Создать новую БД")
        self.create_db_button.clicked.connect(self.accept_creation)
        new_db_layout.addWidget(self.create_db_button)
        layout.addWidget(QtWidgets.QLabel("Создать новую базу данных:"))
        layout.addLayout(new_db_layout)

        # Dialog buttons (OK/Cancel are implicit via accept/reject)
        # Adding a close button for clarity if no action is taken
        self.close_button = QtWidgets.QPushButton("Закрыть")
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)
        
        # Delete selected database (not current)
        self.delete_button = QtWidgets.QPushButton("Удалить выбранную БД")
        self.delete_button.clicked.connect(self.delete_selected_db)
        layout.addWidget(self.delete_button)
        
        self.setMinimumWidth(400)
        self.resize(450, 300) # Initial size

    def populate_db_list(self):
        self.db_list_widget.clear()
        db_dir = os.path.join(os.getcwd(), config.DEFAULT_DB_DIR)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        try:
            for item in os.listdir(db_dir):
                if item.endswith(".db"):
                    list_item = QtWidgets.QListWidgetItem(item)
                    if os.path.join(db_dir, item) == self.current_db_path:
                        font = list_item.font()
                        font.setBold(True)
                        list_item.setFont(font)
                        list_item.setText(f"{item} (текущая)")
                    self.db_list_widget.addItem(list_item)
        except FileNotFoundError:
            # Folder might not exist yet if app just started and config created it
            pass


    def accept_selection(self):
        selected_items = self.db_list_widget.selectedItems()
        if selected_items:
            # Remove " (текущая)" suffix if present
            db_name = selected_items[0].text().replace(" (текущая)", "").strip()
            self.selected_db_to_open = os.path.join(os.getcwd(), config.DEFAULT_DB_DIR, db_name)
            self.accept()

    def accept_creation(self):
        new_name = self.new_db_name_edit.text().strip()
        if new_name:
            if not new_name.endswith(".db"):
                new_name += ".db"
            self.new_db_to_create = new_name # Just the name, path constructed in MainWindow
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите имя для новой базы данных.")

    def delete_selected_db(self):
        selected_items = self.db_list_widget.selectedItems()
        if not selected_items:
            return
        db_name = selected_items[0].text().replace(" (текущая)", "").strip()
        db_path = os.path.join(os.getcwd(), config.DEFAULT_DB_DIR, db_name)
        if db_path == self.current_db_path:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Нельзя удалить открытую в данный момент базу.")
            return
        reply = QtWidgets.QMessageBox.question(
            self,
            "Подтвердите удаление",
            f"Удалить БД '{db_name}'? Это действие необратимо.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                os.remove(db_path)
                self.populate_db_list()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось удалить файл: {e}")


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
        
        # Единая кнопка управления БД
        manage_db_action = QtGui.QAction(QtGui.QIcon.fromTheme("preferences-system"), "Управление БД", self)
        manage_db_action.triggered.connect(self.manage_databases)
        toolbar.addAction(manage_db_action)

        toolbar.addSeparator()

        # Импорт файлов / папки
        import_files_action = QtGui.QAction(QtGui.QIcon.fromTheme("document-import"), "Импорт файлов", self)
        import_files_action.triggered.connect(self.import_files)
        toolbar.addAction(import_files_action)

        import_dir_action = QtGui.QAction(QtGui.QIcon.fromTheme("folder"), "Импорт папки", self)
        import_dir_action.triggered.connect(self.import_directory)
        toolbar.addAction(import_dir_action)
        
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

    def _update_views_with_new_repos(self):
        """Обновляет ссылки на репозитории во всех представлениях (view)."""
        if hasattr(self, 'stats_grid'):
            self.stats_grid.stats_repo = self.stats_repo
            self.stats_grid.tournament_repo = self.tournament_repo
            self.stats_grid.knockout_repo = self.knockout_repo
            self.stats_grid.session_repo = self.session_repo
        
        if hasattr(self, 'tournament_view') and self.tournament_view:
            self.tournament_view.tournament_repo = self.tournament_repo
        
        if hasattr(self, 'knockout_table') and self.knockout_table:
            self.knockout_table.knockout_repo = self.knockout_repo
            
        if hasattr(self, 'session_view') and self.session_view:
            self.session_view.session_repo = self.session_repo

    def _init_menu(self):
        """Создает упрощенное главное меню приложения"""
        menubar = self.menuBar()
        
        # Меню "Файл"
        file_menu = menubar.addMenu("&Файл")
        
        # Действие "Управление БД"
        manage_db_action_menu = QtGui.QAction(QtGui.QIcon.fromTheme("preferences-system"), "&Управление базами данных...", self)
        manage_db_action_menu.setStatusTip("Открыть существующую или создать новую базу данных")
        manage_db_action_menu.triggered.connect(self.manage_databases)
        file_menu.addAction(manage_db_action_menu)
        
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

        # Действие "Импорт файлов"
        import_files_action_menu = QtGui.QAction(QtGui.QIcon.fromTheme("document-import"), "Импорт файлов", self)
        import_files_action_menu.triggered.connect(self.import_files)
        file_menu.addAction(import_files_action_menu)

        # Действие "Импорт директории"
        import_dir_action_menu = QtGui.QAction(QtGui.QIcon.fromTheme("folder"), "Импорт папки", self)
        import_dir_action_menu.triggered.connect(self.import_directory)
        file_menu.addAction(import_dir_action_menu)

    def choose_database(self):
        # Диалог выбора файла БД
        # This specific dialog is no longer directly invoked by a dedicated button.
        # Retain for compatibility or internal use if needed, or refactor out.
        # For now, keep it but it won't be called from UI directly.
        default_dir = os.path.join(os.getcwd(), config.DEFAULT_DB_DIR)
        os.makedirs(default_dir, exist_ok=True)
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Открыть базу данных", 
            default_dir, 
            "SQLite DB (*.db);;Все файлы (*)"
        )
        if fname:
            self.db_path = fname
            config.set_db_path(fname)
            self._init_repos()
            self._update_views_with_new_repos()
            self.refresh_all_data()
            self.statusBar.showMessage(f"Подключена база данных: {self.db_path}")

    def create_new_database(self, db_name_from_dialog=None):
        """Создаёт новую пустую БД внутри каталога databases."""
        name_to_create = db_name_from_dialog
        
        if not name_to_create: # Should not happen if called from dialog
            # Fallback if called directly, though UI now uses dialog
            name, ok = QtWidgets.QInputDialog.getText(self, "Новая база данных", "Введите имя файла (без расширения):")
            if not ok or not name:
                return
            name_to_create = name
            if not name_to_create.endswith(".db"):
                name_to_create += ".db"
        
        db_dir = os.path.join(os.getcwd(), config.DEFAULT_DB_DIR)
        os.makedirs(db_dir, exist_ok=True)
        new_path = os.path.join(db_dir, name_to_create)

        if os.path.exists(new_path):
            QtWidgets.QMessageBox.warning(self, "Файл уже существует", f"Файл '{name_to_create}' уже существует в '{db_dir}'.")
            return False # Indicate failure

        try:
            conn = sqlite3.connect(new_path)
            # Initialize schema for the new DB
            temp_db_manager = DatabaseManager(new_path)
            # Assuming TournamentRepository has _ensure_table or similar, 
            # or we need a generic schema init method.
            # For now, creating repos will attempt to create tables.
            temp_tournament_repo = TournamentRepository(temp_db_manager)
            temp_tournament_repo._ensure_table() # Explicitly ensure tables are made.
            # Add similar for other repos if they have schema creation
            
            conn.close() # Close the initial connection used for creation/schema check
            
            self.db_path = new_path
            config.set_db_path(new_path)
            self._init_repos()
            self._update_views_with_new_repos()
            self.refresh_all_data()
            self.statusBar.showMessage(f"Создана и подключена новая БД: {self.db_path}")
            return True # Indicate success
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось создать БД '{name_to_create}': {e}")
            return False # Indicate failure

    def manage_databases(self):
        dialog = DatabaseManagementDialog(self, current_db_path=self.db_path)
        if dialog.exec(): # Modal execution, blocks until dialog.accept() or dialog.reject()
            if dialog.selected_db_to_open:
                db_to_open_path = dialog.selected_db_to_open
                if db_to_open_path != self.db_path:
                    self.db_path = db_to_open_path
                    config.set_db_path(self.db_path)
                    self._init_repos()
                    self._update_views_with_new_repos()
                    self.refresh_all_data()
                    self.statusBar.showMessage(f"Подключена база данных: {self.db_path}")
            elif dialog.new_db_to_create:
                self.create_new_database(db_name_from_dialog=dialog.new_db_to_create)
        dialog.deleteLater()

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

    # === Импорт и парсинг ===
    def import_files(self):
        """Выбор и импорт отдельных файлов."""
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Выбрать файлы для импорта",
            "./",
            "Text files (*.txt *.log *.ts *.hh *.summary *.txt);;Все файлы (*)",
        )
        if files:
            self._parse_files(files)

    def import_directory(self):
        """Выбор директории и импорт всех текстовых файлов рекурсивно."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Выбрать директорию с файлами")
        if directory:
            text_files = []
            for root, _, filenames in os.walk(directory):
                for fname in filenames:
                    if fname.lower().endswith((".txt", ".log", ".hh", ".summary")):
                        text_files.append(os.path.join(root, fname))
            if text_files:
                self._parse_files(text_files)

    def _parse_files(self, files):
        """Парсит список файлов с отображением прогресса."""
        progress = QtWidgets.QProgressDialog("Парсинг файлов...", "Отмена", 0, len(files), self)
        progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        hh_parser = HandHistoryParser()
        sum_parser = TournamentSummaryParser()

        # Сначала обрабатываем HH-файлы, затем summary, чтобы итоговые выплаты перекрыли данные KO
        hh_files = []
        summary_files = []
        file_types = {}
        for p in files:
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    first_chunk = f.read(512)

                # Определяем тип файла по наличию "Hand #<id>". Старое условие
                # искало только "Poker Hand #" и пропускало форматы вроде
                # "Poker Hand #BR123" от разных румов, из-за чего HH могли
                # ошибочно классифицироваться как summary.
                is_hh = bool(re.search(r"Hand #[A-Za-z0-9]+", first_chunk))
                file_types[p] = is_hh
                if is_hh:
                    hh_files.append(p)
                else:
                    summary_files.append(p)
            except Exception:
                summary_files.append(p)
                file_types[p] = False

        ordered_files = hh_files + summary_files

        progress.setMaximum(len(ordered_files))

        for i, path in enumerate(ordered_files):
            if progress.wasCanceled():
                break
            progress.setLabelText(f"Обработка: {os.path.basename(path)} ({i+1}/{len(ordered_files)})")
            QtWidgets.QApplication.processEvents()

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                is_hh = file_types.get(path, False)
                if is_hh:
                    res = hh_parser.parse(content)
                    ko_count = res.get("hero_ko_count", 0)
                    parsed_tournament_id = res.get("tournament_id")
                    
                    if not parsed_tournament_id:
                        # Attempt to get ID from filename as a secondary for HH if content fails
                        fn_match_hh = re.search(r"Tournament #(\d+)", os.path.basename(path))
                        if fn_match_hh:
                            parsed_tournament_id = fn_match_hh.group(1)
                        else:
                            print(f"WARNING: No Tournament ID in HH content or filename pattern: {path}. Skipping.")
                            continue
                    
                    current_tournament_id = parsed_tournament_id
                    
                    existing = self.tournament_repo.get_hero_tournament(current_tournament_id) if hasattr(self.tournament_repo, "get_hero_tournament") else None
                    self.tournament_repo.add_or_update_tournament(
                        current_tournament_id,
                        place=existing.get("place", 0) if existing else 0,
                        payout=existing.get("payout", 0.0) if existing else 0.0,
                        buyin=existing.get("buyin", 0.0) if existing else 0.0,
                        ko_count=ko_count,
                        date=res.get("date", existing.get("date") if existing else None),
                    )
                else:
                    res = sum_parser.parse(content, filename=os.path.basename(path))
                    parsed_tournament_id = res.get("tournament_id") # Summary parser already tries filename then content

                    if not parsed_tournament_id:
                        # If summary parser (which tries filename and content) still fails, then skip.
                        print(f"WARNING: No Tournament ID from Summary parser (content/filename): {path}. Skipping.")
                        continue
                        
                    current_tournament_id = parsed_tournament_id
                    
                    existing = self.tournament_repo.get_hero_tournament(current_tournament_id) if hasattr(self.tournament_repo, "get_hero_tournament") else None
                    ko_existing = existing.get("ko_count", 0) if existing else 0
                    self.tournament_repo.add_or_update_tournament(
                        current_tournament_id,
                        place=(res.get("place") if res.get("place") is not None else (existing.get("place", 0) if existing else 0)),
                        payout=(res.get("payout") if res.get("payout") is not None else (existing.get("payout", 0.0) if existing else 0.0)),
                        buyin=res.get("buyin", existing.get("buyin", 0.0) if existing else 0.0),
                        ko_count=ko_existing,
                        date=res.get("date", existing.get("date") if existing else None),
                    )
            except Exception as e:
                print(f"Ошибка парсинга {path}: {e}")

            progress.setValue(i + 1)
            QtWidgets.QApplication.processEvents()

        progress.close()
        self.refresh_all_data()

if __name__ == "__main__":
    mw = MainWindow()
    mw.run()
