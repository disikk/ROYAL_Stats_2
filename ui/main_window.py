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
from ui.session_select_dialog import SessionSelectDialog
from ui.custom_icons import CustomIcons  # Импортируем кастомные иконки

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
        self.setMinimumSize(1200, 880)

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
        self.toolbar = self.addToolBar("Панель инструментов")
        self.toolbar.setIconSize(QtCore.QSize(20, 20))  # Размер иконок
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #18181B;
                border: none;
                padding: 8px;
                spacing: 8px;
            }
            QToolButton {
                background-color: transparent;
                border-radius: 8px;
                padding: 8px;
                margin: 0 4px;
                color: #E4E4E7;
                font-size: 14px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #27272A;
            }
            QToolButton:pressed {
                background-color: #3F3F46;
            }
        """)

        # Кнопки панели инструментов с кастомными SVG иконками
        refresh_action = QtGui.QAction(CustomIcons.refresh_icon("#10B981"), "Обновить", self)
        refresh_action.setToolTip("Обновить все данные")
        refresh_action.triggered.connect(self.refresh_all_data)
        self.toolbar.addAction(refresh_action)
        # Сохраняем ссылку на refresh action для блокировки
        self.refresh_action = refresh_action

        manage_db_action = QtGui.QAction(CustomIcons.database_icon("#3B82F6"), "База данных", self)
        manage_db_action.setToolTip("Управление базами данных")
        manage_db_action.triggered.connect(self.manage_databases)
        self.toolbar.addAction(manage_db_action)

        self.toolbar.addSeparator()

        import_files_action = QtGui.QAction(CustomIcons.file_icon("#F59E0B"), "Файлы", self)
        import_files_action.setToolTip("Импорт отдельных файлов")
        import_files_action.triggered.connect(self.import_files)
        self.toolbar.addAction(import_files_action)

        import_dir_action = QtGui.QAction(CustomIcons.folder_icon("#8B5CF6"), "Папка", self)
        import_dir_action.setToolTip("Импорт целой папки")
        import_dir_action.triggered.connect(self.import_directory)
        self.toolbar.addAction(import_dir_action)

        self.toolbar.addSeparator()

        # Информационные Label с общей статистикой (будут обновляться)
        self.total_tournaments_label = QtWidgets.QLabel("Турниров: -")
        self.total_tournaments_label.setStyleSheet("font-weight: bold; margin: 0 10px;")
        self.toolbar.addWidget(self.total_tournaments_label)

        self.total_profit_label = QtWidgets.QLabel("Прибыль: -")
        self.total_profit_label.setStyleSheet("font-weight: bold; margin: 0 10px;")
        self.toolbar.addWidget(self.total_profit_label)

        self.total_ko_label = QtWidgets.QLabel("KO: -")
        self.total_ko_label.setStyleSheet("font-weight: bold; margin: 0 10px;")
        self.toolbar.addWidget(self.total_ko_label)

        # QToolBar doesn't have addStretch method, use spacer widget instead
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.toolbar.addWidget(spacer)

        # QTabWidget
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # Создаем экземпляры представлений (Views)
        # Передаем им ApplicationService или ссылки на репозитории через ApplicationService
        # Лучше передавать сам ApplicationService, чтобы Views могли запрашивать у него данные
        self.stats_grid = StatsGrid(self.app_service)
        self.tournament_view = TournamentView(self.app_service)
        self.session_view = SessionView(self.app_service)

        # Добавляем вкладки с иконками
        self.tabs.addTab(self.stats_grid, CustomIcons.chart_icon("#10B981"), "Дашборд")
        self.tabs.addTab(self.tournament_view, CustomIcons.list_icon("#3B82F6"), "Турниры")
        self.tabs.addTab(self.session_view, CustomIcons.calendar_icon("#F59E0B"), "Сессии")

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
        dialog = SessionSelectDialog(self.app_service, self)
        if not dialog.exec():
            return
        session_id, session_name = dialog.get_result()
        if session_id is None and not session_name:
            session_name = f"Сессия {datetime.now().strftime('%Y-%m-%d %H:%M')}"  # Имя по умолчанию, если не введено

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
        self.import_thread = ImportThread(
            self.app_service,
            paths,
            session_name,
            self.import_progress_signal,
            existing_session_id=session_id,
        )
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
        
        # Запускаем асинхронное обновление статистики
        self.statusBar().showMessage("Обновление статистики...")
        
        # Создаем и запускаем поток обновления статистики после импорта
        self.post_import_refresh_thread = RefreshThread(self.app_service)
        self.post_import_refresh_thread.progress_update.connect(self._on_refresh_progress)
        self.post_import_refresh_thread.progress_percent.connect(self._on_refresh_percent)
        self.post_import_refresh_thread.finished_update.connect(self._on_post_import_refresh_finished)
        self.post_import_refresh_thread.error_occurred.connect(self._on_refresh_error)
        self.post_import_refresh_thread.start()

    @QtCore.pyqtSlot()
    def _on_post_import_refresh_finished(self):
        """Вызывается по завершении обновления статистики после импорта."""
        logger.info("Обновление статистики после импорта завершено")
        
        # Обновляем UI компоненты в основном потоке
        self._update_toolbar_info()
        
        # Инвалидируем кеш и обновляем вкладки
        self.invalidate_all_caches()
        self.refresh_all_views()
        
        self.statusBar().showMessage(f"Импорт завершен. База данных: {os.path.basename(self.app_service.db_path)}", 3000)

    def invalidate_all_caches(self):
        """Инвалидирует кеш данных во всех view компонентах."""
        if hasattr(self, 'stats_grid') and self.stats_grid:
            self.stats_grid.invalidate_cache()
        if hasattr(self, 'tournament_view') and self.tournament_view:
            self.tournament_view.invalidate_cache()
        if hasattr(self, 'session_view') and self.session_view:
            self.session_view.invalidate_cache()

    def refresh_all_views(self):
        """Обновляет все view компоненты."""
        if hasattr(self, 'stats_grid') and self.stats_grid:
            self.stats_grid.reload()
        if hasattr(self, 'tournament_view') and self.tournament_view:
            self.tournament_view.reload()
        if hasattr(self, 'session_view') and self.session_view:
            self.session_view.reload()

    def refresh_all_data(self):
        """
        Обновляет данные во всех представлениях UI асинхронно.
        """
        logger.info("Запуск асинхронного обновления данных...")
        
        # Блокируем кнопку обновления на время операции
        if hasattr(self, 'refresh_action'):
            self.refresh_action.setEnabled(False)
        
        # Показываем индикатор загрузки в статусбаре
        self.statusBar().showMessage("Обновление данных...")
        
        # Создаем и запускаем поток обновления
        self.refresh_thread = RefreshThread(self.app_service)
        self.refresh_thread.progress_update.connect(self._on_refresh_progress)
        self.refresh_thread.progress_percent.connect(self._on_refresh_percent)
        self.refresh_thread.finished_update.connect(self._on_refresh_finished)
        self.refresh_thread.error_occurred.connect(self._on_refresh_error)
        self.refresh_thread.start()

    @QtCore.pyqtSlot(str)
    def _on_refresh_progress(self, message: str):
        """Обновляет статусбар во время обновления данных."""
        self.statusBar().showMessage(message)

    @QtCore.pyqtSlot(int)
    def _on_refresh_percent(self, percent: int):
        """Обновляет прогресс в статусбаре."""
        if hasattr(self, 'refresh_action'):
            # Можно добавить прогресс-бар в статусбар или показать процент в тексте
            message = f"Обновление данных... {percent}%"
            self.statusBar().showMessage(message)

    @QtCore.pyqtSlot()
    def _on_refresh_finished(self):
        """Вызывается по завершении обновления данных."""
        logger.info("Асинхронное обновление данных завершено")
        
        # Обновляем UI компоненты в основном потоке
        self._update_toolbar_info()
        
        # Инвалидируем кеш и обновляем вкладки
        self.invalidate_all_caches()
        self.refresh_all_views()
        
        # Восстанавливаем кнопку обновления
        if hasattr(self, 'refresh_action'):
            self.refresh_action.setEnabled(True)
        
        self.statusBar().showMessage(f"Данные обновлены. База данных: {os.path.basename(self.app_service.db_path)}", 3000)

    @QtCore.pyqtSlot(str)
    def _on_refresh_error(self, error_message: str):
        """Обработка ошибок при обновлении данных."""
        logger.error(f"Ошибка обновления: {error_message}")
        
        # Восстанавливаем кнопку обновления
        if hasattr(self, 'refresh_action'):
            self.refresh_action.setEnabled(True)
        
        self.statusBar().showMessage(f"Ошибка обновления: {error_message}", 5000)
        
        QtWidgets.QMessageBox.critical(
            self,
            "Ошибка обновления",
            f"Не удалось обновить данные:\n{error_message}"
        )


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

    def __init__(
        self,
        app_service: ApplicationService,
        paths: List[str],
        session_name: str,
        progress_signal: QtCore.pyqtSignal,
        existing_session_id: str | None = None,
    ):
        super().__init__()
        self.app_service = app_service
        self.paths = paths
        self.session_name = session_name
        self.existing_session_id = existing_session_id
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
                session_id=self.existing_session_id,
                progress_callback=self._report_progress,
                is_canceled_callback=self._is_import_canceled,
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


class RefreshThread(QtCore.QThread):
    """Поток для обновления данных без блокировки GUI."""
    progress_update = QtCore.pyqtSignal(str)  # Сигнал для обновления статуса
    progress_percent = QtCore.pyqtSignal(int)  # Сигнал для обновления процентов
    finished_update = QtCore.pyqtSignal()     # Сигнал завершения
    error_occurred = QtCore.pyqtSignal(str)   # Сигнал ошибки
    
    def __init__(self, app_service: ApplicationService):
        super().__init__()
        self.app_service = app_service
        
    def run(self):
        """Выполняет обновление данных в отдельном потоке."""
        try:
            self.progress_update.emit("Обновление общей статистики...")
            self.progress_percent.emit(0)
            
            # Вызываем метод обновления статистики с callback для прогресса
            self.app_service._update_all_statistics(None, progress_callback=self._report_progress)
            
            self.progress_update.emit("Данные обновлены")
            self.progress_percent.emit(100)
            self.finished_update.emit()
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных: {e}")
            self.error_occurred.emit(str(e))
    
    def _report_progress(self, step: int, total: int):
        """Отправляет прогресс в процентах через сигналы Qt."""
        if total > 0:
            percent = int((step / total) * 100)
            self.progress_percent.emit(percent)

            # Меняем текст в зависимости от процента прогресса
            if percent < 25:
                self.progress_update.emit("Обновление общей статистики...")
            elif percent < 50:
                self.progress_update.emit("Обновление распределения мест...")
            elif percent < 75:
                self.progress_update.emit("Подсчет нокаутов...")
            else:
                self.progress_update.emit("Обновление статистики сессий...")


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