# -*- coding: utf-8 -*-

"""
Главное окно приложения Royal Stats (Hero-only).
Оркестрирует UI компоненты и взаимодействует с ApplicationService.
"""

from PyQt6 import QtWidgets, QtGui, QtCore
import sys
import os
import logging
from typing import List
from datetime import datetime

import config
# Импортируем синглтон ApplicationService
from application_service import application_service, ApplicationService

# Импортируем UI компоненты
from ui.app_style import apply_dark_theme, format_money, format_percentage, apply_cell_color_by_value
from ui.stats_grid import StatsGrid
from ui.tournament_view import TournamentView
from ui.session_view import SessionView

# Импортируем диалог управления БД
from ui.database_management_dialog import DatabaseManagementDialog # Предполагаем, что такой файл будет создан

logger = logging.getLogger('ROYAL_Stats.MainWindow')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)


class MainWindow(QtWidgets.QMainWindow):
    """
    Основное окно приложения с вкладками и панелью инструментов.
    """
    # Сигнал для обновления прогресса импорта
    import_progress_signal = QtCore.pyqtSignal(int, int, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_TITLE)
        self.setMinimumSize(1200, 800)

        # ApplicationService уже проинициализирован как синглтон
        self.app_service = application_service

        # Инициализируем UI
        self._init_ui()

        # Подключаемся к последней использованной БД при старте
        try:
            self.app_service.switch_database(config.LAST_DB_PATH)
            self.statusBar().showMessage(f"Подключена база данных: {os.path.basename(self.app_service.db_path)}")
            self.refresh_all_data() # Обновляем данные после подключения
        except Exception as e:
            logger.error(f"Ошибка при подключении к последней БД {config.LAST_DB_PATH}: {e}")
            self.statusBar().showMessage(f"Ошибка подключения к БД: {e}", 5000)
            # Можно предложить пользователю выбрать или создать БД
            self.manage_databases()


    def _init_ui(self):
        """Инициализирует компоненты пользовательского интерфейса."""
        central_widget = QtWidgets.QWidget(self)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # Строка состояния
        self.setStatusBar(QtWidgets.QStatusBar(self))

        # Панель инструментов
        toolbar = self.addToolBar("Панель инструментов")
        toolbar.setIconSize(QtCore.QSize(24, 24))

        # Кнопки панели инструментов
        refresh_action = QtGui.QAction(QtGui.QIcon.fromTheme("view-refresh"), "Обновить все", self)
        refresh_action.triggered.connect(self.refresh_all_data)
        toolbar.addAction(refresh_action)

        manage_db_action = QtGui.QAction(QtGui.QIcon.fromTheme("preferences-system"), "Управление БД", self)
        manage_db_action.triggered.connect(self.manage_databases)
        toolbar.addAction(manage_db_action)

        toolbar.addSeparator()

        import_files_action = QtGui.QAction(QtGui.QIcon.fromTheme("document-import"), "Импорт файлов...", self)
        import_files_action.triggered.connect(self.import_files)
        toolbar.addAction(import_files_action)

        import_dir_action = QtGui.QAction(QtGui.QIcon.fromTheme("folder"), "Импорт папки...", self)
        import_dir_action.triggered.connect(self.import_directory)
        toolbar.addAction(import_dir_action)

        toolbar.addSeparator()

        # Информационные Label с общей статистикой (будут обновляться)
        self.total_tournaments_label = QtWidgets.QLabel("Турниров: -")
        self.total_tournaments_label.setStyleSheet("font-weight: bold; margin: 0 10px;")
        toolbar.addWidget(self.total_tournaments_label)

        self.total_profit_label = QtWidgets.QLabel("Прибыль: -")
        self.total_profit_label.setStyleSheet("font-weight: bold; margin: 0 10px;")
        toolbar.addWidget(self.total_profit_label)

        self.total_ko_label = QtWidgets.QLabel("KO: -")
        self.total_ko_label.setStyleSheet("font-weight: bold; margin: 0 10px;")
        toolbar.addWidget(self.total_ko_label)

        # QToolBar doesn't have addStretch method, use spacer widget instead
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        toolbar.addWidget(spacer)

        # QTabWidget
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # Создаем экземпляры представлений (Views)
        # Передаем им ApplicationService или ссылки на репозитории через ApplicationService
        # Лучше передавать сам ApplicationService, чтобы Views могли запрашивать у него данные
        self.stats_grid = StatsGrid(self.app_service)
        self.tournament_view = TournamentView(self.app_service)
        self.session_view = SessionView(self.app_service)

        # Добавляем вкладки
        self.tabs.addTab(self.stats_grid, QtGui.QIcon.fromTheme("office-chart-bar"), "Дашборд")
        self.tabs.addTab(self.tournament_view, QtGui.QIcon.fromTheme("view-list-details"), "Турниры")
        self.tabs.addTab(self.session_view, QtGui.QIcon.fromTheme("x-office-calendar"), "Сессии")

        # Подключаем сигнал изменения вкладки
        self.tabs.currentChanged.connect(self.tab_changed)

        # Добавляем метку версии в нижний правый угол
        version_label = QtWidgets.QLabel(f"v{config.APP_VERSION}")
        version_label.setStyleSheet("color: #777; font-size: 9px; margin: 5px;")
        version_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignBottom)
        main_layout.addWidget(version_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignBottom)


    def _init_menu(self):
        """Создает упрощенное главное меню приложения"""
        # Меню инициализируется здесь, если нужно добавить его (обычно toolbar достаточно)
        # Код из оригинального файла можно адаптировать сюда, но пока пропустим для краткости,
        # так как основные действия в тулбаре. Если потребуется, добавим позже.
        pass

    def manage_databases(self):
        """Открывает диалог управления базами данных."""
        dialog = DatabaseManagementDialog(self, self.app_service)
        if dialog.exec(): # Модальное исполнение
            # Диалог уже вызвал app_service.switch_database() если пользователь выбрал другую БД
            # or app_service.create_new_database() if user created a new one.
            self.statusBar().showMessage(f"Подключена база данных: {os.path.basename(self.app_service.db_path)}")
            self.refresh_all_data() # Обновляем UI после смены БД

        dialog.deleteLater() # Удаляем диалог после закрытия

    def import_files(self):
        """Выбор отдельных файлов для импорта."""
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Выбрать файлы для импорта",
            "./", # Начальная директория, можно сохранить последнюю использованную
            "Poker Files (*.txt *.log *.ts *.hh *.summary);;All files (*)",
        )
        if files:
            self._start_import(files)

    def import_directory(self):
        """Выбор директории для импорта."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Выбрать директорию для импорта")
        if directory:
            self._start_import([directory]) # Передаем как список для единообразия с import_files

    def _start_import(self, paths: List[str]):
        """Запускает процесс импорта с прогресс-баром."""
        session_name, ok = QtWidgets.QInputDialog.getText(self, "Имя сессии", "Введите имя для этой игровой сессии:")
        if not ok or not session_name:
             session_name = f"Сессия {datetime.now().strftime('%Y-%m-%d %H:%M')}" # Имя по умолчанию, если не введено

        # Создаем прогресс-диалог
        self.progress_dialog = QtWidgets.QProgressDialog(
            "Импорт и обработка файлов...",
            "Отмена",
            0,
            0, # Установим максимум позже, когда ApplicationService подсчитает файлы
            self
        )
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(True) # Автоматически закрывать по завершении
        self.progress_dialog.setMinimumDuration(0) # Показывать сразу

        # Подключаем сигнал прогресса
        self.import_progress_signal.connect(self._update_progress)
        self.progress_dialog.canceled.connect(self._cancel_import) # Обработка отмены

        # Запускаем импорт в отдельном потоке, чтобы не блокировать UI
        # ApplicationService сам будет вызывать self.import_progress_signal.emit
        self.import_thread = ImportThread(self.app_service, paths, session_name, self.import_progress_signal)
        self.import_thread.finished.connect(self._import_finished)
        self.import_thread.start()

        self.progress_dialog.exec() # Запускаем модальный прогресс-диалог


    @QtCore.pyqtSlot(int, int, str)
    def _update_progress(self, current: int, total: int, text: str):
        """Обновляет прогресс-бар."""
        if self.progress_dialog:
            if self.progress_dialog.maximum() == 0: # Устанавливаем максимум при первом вызове
                 self.progress_dialog.setMaximum(total)
            self.progress_dialog.setValue(current)
            self.progress_dialog.setLabelText(text)
            # QApplication.processEvents() # Может понадобиться для моментального обновления, но exec() в диалоге обычно справляется

    @QtCore.pyqtSlot()
    def _cancel_import(self):
        """Обработка отмены импорта."""
        logger.info("Импорт отменен пользователем.")
        if self.import_thread and self.import_thread.isRunning():
            # Используем безопасный метод отмены через флаг
            self.import_thread.cancel()
            # Обновляем диалог прогресса
            self.progress_dialog.setLabelText("Отмена импорта, пожалуйста подождите...")
            self.statusBar().showMessage("Импорт отменен пользователем", 3000)

    @QtCore.pyqtSlot()
    def _import_finished(self):
        """Вызывается по завершении потока импорта."""
        logger.info("Поток импорта завершен.")
        # progress_dialog закроется автоматически если autoClose=True
        self.refresh_all_data() # Обновляем UI после импорта


    def refresh_all_data(self):
        """
        Обновляет данные во всех представлениях UI.
        Вызывается после импорта или смены БД.
        """
        logger.info("Обновление всех данных в UI...")
        # Обновить общие статы в тулбаре
        self._update_toolbar_info()

        # Обновить все вкладки
        # Вкладки сами должны запросить данные у ApplicationService при вызове reload
        if hasattr(self, 'stats_grid') and self.stats_grid:
             self.stats_grid.reload()
        if hasattr(self, 'tournament_view') and self.tournament_view:
             self.tournament_view.reload()
        if hasattr(self, 'session_view') and self.session_view:
             self.session_view.reload()

        self.statusBar().showMessage(f"Данные обновлены. База данных: {os.path.basename(self.app_service.db_path)}", 3000)


    def _update_toolbar_info(self):
        """Обновляет информационные Label в панели инструментов."""
        stats = self.app_service.get_overall_stats()
        self.total_tournaments_label.setText(f"Турниров: {stats.total_tournaments}")
        self.total_profit_label.setText(f"Прибыль: {format_money(stats.total_prize - stats.total_buy_in, with_plus=True)}")
        apply_cell_color_by_value(self.total_profit_label, stats.total_prize - stats.total_buy_in) # Применяем цвет
        self.total_ko_label.setText(f"KO: {stats.total_knockouts}")


    def tab_changed(self, index):
        """Обрабатывает событие изменения активной вкладки."""
        tab_name = self.tabs.tabText(index)
        self.statusBar().showMessage(f"Вкладка: {tab_name}", 2000)
        # Можно добавить здесь логику для ленивой загрузки данных на вкладке,
        # но для нашей архитектуры Views запрашивают данные при reload()


# Отдельный поток для импорта, чтобы не блокировать GUI
class ImportThread(QtCore.QThread):
    """Поток для выполнения импорта файлов."""
    # Сигнал для отправки прогресса обратно в основной поток (MainWindow)
    progress_update = QtCore.pyqtSignal(int, int, str)

    def __init__(self, app_service: ApplicationService, paths: List[str], session_name: str, progress_signal: QtCore.pyqtSignal):
        super().__init__()
        self.app_service = app_service
        self.paths = paths
        self.session_name = session_name
        self.progress_update = progress_signal # Используем сигнал из MainWindow
        self._is_canceled = False # Флаг для отмены

    def run(self):
        """Метод, выполняемый в потоке."""
        logger.info(f"Поток импорта запущен для {len(self.paths)} путей.")
        try:
            # Передаем progress_update и is_cancelled в ApplicationService
            self.app_service.import_files(
                self.paths,
                self.session_name,
                progress_callback=self._report_progress,
                is_canceled_callback=self._is_import_canceled
            )
        except Exception as e:
            logger.critical(f"Критическая ошибка в потоке импорта: {e}")
            # Можно отправить сигнал об ошибке в UI
            self.progress_update.emit(0, 1, f"Ошибка импорта: {e}")
        logger.info("Поток импорта завершает работу.")
        
    def _is_import_canceled(self):
        """Возвращает статус отмены импорта."""
        return self._is_canceled


    def _report_progress(self, current: int, total: int, text: str):
        """Отправляет сигнал об обновлении прогресса."""
        self.progress_update.emit(current, total, text)

    # Метод для установки флага отмены (вызывается из основного потока)
    def cancel(self):
         self._is_canceled = True
         # TODO: Реализовать проверку флага _is_canceled в ApplicationService.import_files
         # и парсерах, чтобы корректно прервать выполнение.


# Предполагаем, что DatabaseManagementDialog.py будет создан отдельно
# Вот пример его базовой структуры для справки:

# class DatabaseManagementDialog(QtWidgets.QDialog):
#     def __init__(self, parent=None, app_service: ApplicationService = None):
#         super().__init__(parent)
#         self.app_service = app_service
#         self.setWindowTitle("Управление базами данных")
#         # ... UI элементы для выбора/создания БД ...
#         # При выборе/создании: self.app_service.switch_database(selected_path)
#         # или self.app_service.create_new_database(new_name)
#         # Затем self.accept() или self.reject()
#         # ...