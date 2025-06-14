# -*- coding: utf-8 -*-

"""
Главное окно приложения Royal Stats (Hero-only).
Оркестрирует UI компоненты и взаимодействует с ``AppFacade``.
"""

from PyQt6 import QtWidgets, QtGui, QtCore
import sys
import os
import logging
from typing import List, Optional
from datetime import datetime

from services.app_config import app_config
# Импортируем типы для AppFacade
from services import AppFacade

# Импортируем UI компоненты
from ui.app_style import apply_dark_theme, format_money, format_percentage, apply_cell_color_by_value
from ui.stats_grid import StatsGrid
from ui.tournament_view import TournamentView
from ui.session_view import SessionView
from ui.session_select_dialog import SessionSelectDialog
from ui.custom_icons import CustomIcons  # Импортируем кастомные иконки
from ui.background import thread_manager
from models import OverallStats
from ui.gradient_label import GradientLabel

# Импортируем диалог управления БД
from ui.database_management_dialog import DatabaseManagementDialog # Предполагаем, что такой файл будет создан

logger = logging.getLogger('ROYAL_Stats.MainWindow')
logger.setLevel(logging.DEBUG if app_config.debug else logging.INFO)


class MainWindow(QtWidgets.QMainWindow):
    """
    Основное окно приложения с вкладками и панелью инструментов.
    """
    # Сигнал для обновления прогресса импорта
    import_progress_signal = QtCore.pyqtSignal(int, int, str)

    def __init__(self, app_facade: AppFacade):
        super().__init__()
        self.setWindowTitle(app_config.app_title)
        self.setMinimumSize(1300, 930)

        # Используем переданный AppFacade
        self.app_service = app_facade
        
        # Флаги для отслеживания загруженности вкладок
        self._tab_loaded = {'stats': False, 'tournaments': False, 'sessions': False}
        self._initial_load_done = False

        # Инициализируем UI
        self._init_ui()

        # Загружаем данные после отображения окна, чтобы не блокировать GUI
        QtCore.QTimer.singleShot(0, self._load_initial_data)

    def _load_initial_data(self):
        """Подключает последнюю БД и запускает обновление статистики."""
        try:
            self.app_service.switch_database(app_config.current_db_path, load_stats=False)
            self._update_db_label()
            self.statusBar().showMessage(
                f"Подключена база данных: {os.path.basename(self.app_service.db_path)}"
            )
        except Exception as e:
            logger.error(f"Ошибка при подключении к последней БД {app_config.current_db_path}: {e}")
            self.statusBar().showMessage(f"Ошибка подключения к БД: {e}", 5000)
            self.manage_databases()
            return

        # Статистика будет подсчитана асинхронно с задержкой
        QtCore.QTimer.singleShot(100, self.refresh_all_data)


    def _init_ui(self):
        """Инициализирует компоненты пользовательского интерфейса."""
        central_widget = QtWidgets.QWidget(self)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # Строка состояния. Оставляем небольшую высоту для сообщений.
        self.setStatusBar(QtWidgets.QStatusBar(self))
        self.statusBar().setStyleSheet(
            "padding: 2px 4px; margin: 0; height: 16px; font-size: 12px;"
        )
        self.statusBar().setSizeGripEnabled(False)

        # Метка с информацией о текущей БД (будет размещена в тулбаре)
        # Используем градиентный текст и увеличиваем размер на 50%
        self.db_status_label = GradientLabel("")
        self.db_status_label.setStyleSheet(
            "font-weight: bold; font-size: 150%; margin-right: 8px;"
        )

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
        screenshot_action = QtGui.QAction(CustomIcons.screenshot_icon("#F87171"), "Скриншот", self)
        screenshot_action.setToolTip("Сохранить скриншот окна в буфер обмена")
        screenshot_action.triggered.connect(self.take_screenshot)
        self.toolbar.addAction(screenshot_action)
        # Увеличиваем иконку скриншота на 20% относительно стандартного размера
        screenshot_btn = self.toolbar.widgetForAction(screenshot_action)
        base_size = self.toolbar.iconSize()
        enlarged = QtCore.QSize(int(base_size.width() * 1.2), int(base_size.height() * 1.2))
        screenshot_btn.setIconSize(enlarged)

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

        self.pre_ft_chipev_label = QtWidgets.QLabel("Rush chips / T: -")
        self.pre_ft_chipev_label.setStyleSheet("font-weight: bold; margin: 0 10px;")
        self.toolbar.addWidget(self.pre_ft_chipev_label)

        # QToolBar doesn't have addStretch method, use spacer widget instead
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.toolbar.addWidget(spacer)

        # Метка с именем подключенной базы данных и версией приложения в правой части тулбара
        self.toolbar.addWidget(self.db_status_label)
        version_label = QtWidgets.QLabel(f"v{app_config.app_version}")
        version_label.setStyleSheet("color: #777; font-size: 9px; margin-right: 4px;")
        self.toolbar.addWidget(version_label)

        # QTabWidget
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # Создаем экземпляры представлений (Views)
        # Передаем им AppFacade или ссылки на репозитории через него
        # Лучше передавать сам AppFacade, чтобы Views могли запрашивать у него данные
        self.stats_grid = StatsGrid(self.app_service)
        self.stats_grid.overallStatsChanged.connect(self._update_toolbar_info)
        self.tournament_view = TournamentView(self.app_service)
        self.session_view = SessionView(self.app_service)

        # Добавляем вкладки с иконками
        self.tabs.addTab(self.stats_grid, CustomIcons.chart_icon("#10B981"), "Дашборд")
        self.tabs.addTab(self.tournament_view, CustomIcons.list_icon("#3B82F6"), "Турниры")
        self.tabs.addTab(self.session_view, CustomIcons.calendar_icon("#F59E0B"), "Сессии")

        # Подключаем сигнал изменения вкладки
        self.tabs.currentChanged.connect(self.tab_changed)

        # Место под версию и название БД сверху освободило нижнюю область окна


    def _init_menu(self):
        """Создает упрощенное главное меню приложения"""
        # Меню инициализируется здесь, если нужно добавить его (обычно toolbar достаточно)
        # Код из оригинального файла можно адаптировать сюда, но пока пропустим для краткости,
        # так как основные действия в тулбаре. Если потребуется, добавим позже.
        pass

    def manage_databases(self):
        """Открывает диалог управления базами данных."""
        dialog = DatabaseManagementDialog(self, self.app_service)
        current_path = self.app_service.db_path
        if dialog.exec():  # Модальное исполнение
            new_path = self.app_service.db_path
            if new_path != current_path:
                # Отменяем все фоновые операции перед сменой БД
                thread_manager.cancel_all()
                # Прячем возможные оверлеи загрузки, которые могли остаться
                if hasattr(self, 'stats_grid') and self.stats_grid:
                    self.stats_grid.hide_loading_overlay()
                if hasattr(self, 'tournament_view') and self.tournament_view:
                    self.tournament_view.hide_loading_overlay()
                if hasattr(self, 'session_view') and self.session_view:
                    self.session_view.hide_loading_overlay()

                app_config.set_current_db_path(new_path)
                # Сбрасываем кеши и запускаем асинхронную загрузку данных
                self.invalidate_all_caches()
                self.refresh_all_data()
            self._update_db_label()
            self.statusBar().showMessage(
                f"Подключена база данных: {os.path.basename(self.app_service.db_path)}"
            )
        dialog.deleteLater()

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
            0, # Установим максимум позже, когда AppFacade подсчитает файлы
            self
        )
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        # Отключаем автоматическое закрытие, чтобы диалог не "мигал"
        # при изменении максимального значения
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setMinimumDuration(0) # Показывать сразу

        # Подключаем сигнал прогресса
        self.import_progress_signal.connect(self._update_progress)
        self.progress_dialog.canceled.connect(self._cancel_import) # Обработка отмены

        # Запускаем импорт в отдельном потоке, чтобы не блокировать UI
        # AppFacade сам будет вызывать self.import_progress_signal.emit
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
        dialog = self.progress_dialog
        if dialog:
            if total != dialog.maximum() and total != 0:
                dialog.setMaximum(total)
            elif dialog.maximum() == 0:
                dialog.setMaximum(total)
            dialog.setValue(current)
            dialog.setLabelText(text)
            # QApplication.processEvents() # Может понадобиться для моментального обновления, но exec() в диалоге обычно справляется

    @QtCore.pyqtSlot()
    def _cancel_import(self):
        """Обработка отмены импорта."""
        logger.info("Импорт отменен пользователем.")
        if self.import_thread and self.import_thread.isRunning():
            # Используем безопасный метод отмены через флаг
            self.import_thread.cancel()
            # Отключаем обновление прогресса, чтобы диалог не появлялся снова
            try:
                self.import_progress_signal.disconnect(self._update_progress)
            except TypeError:
                pass
            # Закрываем диалог, чтобы он не показывался снова
            if self.progress_dialog:
                # Сначала сохраняем ссылку и обнуляем атрибут,
                # чтобы повторный сигнал canceled не привёл к ошибке
                dialog = self.progress_dialog
                self.progress_dialog = None
                try:
                    dialog.canceled.disconnect(self._cancel_import)
                except TypeError:
                    pass
                dialog.close()
                dialog.deleteLater()
            self.statusBar().showMessage("Импорт отменен пользователем", 3000)

    @QtCore.pyqtSlot()
    def _import_finished(self):
        """Вызывается по завершении потока импорта."""
        logger.debug("Поток импорта завершен.")
        # Без гарантированного закрытия прогресс-диалога иногда возникал
        # сценарий, когда диалог оставался открытым из-за ошибки в потоке
        # импорта и блокировал главный цикл событий. Поэтому дополнительно
        # закрываем диалог принудительно.
        if hasattr(self, "progress_dialog") and self.progress_dialog:
            dialog = self.progress_dialog
            self.progress_dialog = None
            try:
                dialog.canceled.disconnect(self._cancel_import)
            except TypeError:
                pass
            dialog.close()
            dialog.deleteLater()

        # Дожидаемся завершения потока и очищаем ссылки
        if hasattr(self, "import_thread") and self.import_thread:
            self.import_thread.wait()
            self.import_thread.deleteLater()
            self.import_thread = None
        # Диалог мы закрываем вручную, так как автоматическое закрытие
        # отключено для предотвращения мигания.
        
        # По завершении импорта сразу обновляем UI
        self._update_toolbar_info()
        self.invalidate_all_caches()
        self.refresh_all_views(show_overlay=False)
        self._update_db_label()

        self.statusBar().showMessage(
            f"Импорт завершен. База данных: {os.path.basename(self.app_service.db_path)}",
            3000,
        )


    def invalidate_all_caches(self):
        """Инвалидирует кеш данных во всех view компонентах."""
        self._tab_loaded = {'stats': False, 'tournaments': False, 'sessions': False}
        if hasattr(self, 'stats_grid') and self.stats_grid:
            self.stats_grid.invalidate_cache()
        if hasattr(self, 'tournament_view') and self.tournament_view:
            self.tournament_view.invalidate_cache()
        if hasattr(self, 'session_view') and self.session_view:
            self.session_view.invalidate_cache()

    def refresh_all_views(self, show_overlay: bool = True, force_all: bool = False):
        """
        Обновляет view компоненты.
        Args:
            show_overlay: Показывать ли индикатор загрузки
            force_all: Если True, обновляет все вкладки. Иначе только текущую.
        """
        if force_all:
            if hasattr(self, 'stats_grid') and self.stats_grid:
                self.stats_grid.reload(show_overlay=show_overlay)
                self._tab_loaded['stats'] = True
            if hasattr(self, 'tournament_view') and self.tournament_view:
                self.tournament_view.reload(show_overlay=show_overlay)
                self._tab_loaded['tournaments'] = True
            if hasattr(self, 'session_view') and self.session_view:
                self.session_view.reload(show_overlay=show_overlay)
                self._tab_loaded['sessions'] = True
        else:
            self._load_current_tab(show_overlay)

    def refresh_all_data(self):
        """
        Обновляет данные во всех представлениях UI асинхронно.
        Используется для принудительного обновления (например, после импорта).
        """
        logger.info("Запуск полного обновления данных...")
        self._tab_loaded = {'stats': False, 'tournaments': False, 'sessions': False}
        # Сбрасываем кеши сразу, чтобы избежать отображения устаревших данных
        self.invalidate_all_caches()
        self._refresh_all_data_async(force_all=True)

    def _refresh_all_data_async(self, force_all: bool = False):
        """
        Внутренний метод для асинхронного обновления данных.
        """
        # Блокируем кнопку обновления на время операции
        if hasattr(self, 'refresh_action'):
            self.refresh_action.setEnabled(False)
        self.statusBar().showMessage("Обновление данных...")
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
        logger.debug("Асинхронное обновление данных завершено")
        self._update_toolbar_info()
        self.invalidate_all_caches()
        self.refresh_all_views(force_all=True)
        if hasattr(self, 'refresh_action'):
            self.refresh_action.setEnabled(True)
        self._update_db_label()
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


    def _update_toolbar_info(self, stats: Optional[OverallStats] = None):
        """Обновляет информационные Label в панели инструментов."""
        if stats is None:
            stats = self.app_service.get_overall_stats()
        self.total_tournaments_label.setText(f"Турниров: {stats.total_tournaments}")
        self.total_profit_label.setText(f"Прибыль: {format_money(stats.total_prize - stats.total_buy_in, with_plus=True)}")
        apply_cell_color_by_value(self.total_profit_label, stats.total_prize - stats.total_buy_in) # Применяем цвет
        self.total_ko_label.setText(f"KO: {stats.total_knockouts:.1f}")
        chipev_value = stats.pre_ft_chipev if stats.pre_ft_chipev is not None else 0.0
        self.pre_ft_chipev_label.setText(f"Rush chips / T: {chipev_value:.0f}")
        apply_cell_color_by_value(self.pre_ft_chipev_label, chipev_value)
        if chipev_value == 0:
            self.pre_ft_chipev_label.setStyleSheet("font-weight: bold; margin: 0 10px; color: white;")

    def _update_db_label(self):
        """Отображает имя текущей базы данных в правой части тулбара."""
        self.db_status_label.setText(
            f"БД: {os.path.basename(self.app_service.db_path)}"
        )

    def take_screenshot(self):
        """Сохраняет скриншот окна в буфер обмена."""
        pixmap = self.grab()
        QtWidgets.QApplication.clipboard().setPixmap(pixmap)
        self.statusBar().showMessage("Скриншот сохранён в буфер обмена", 2000)


    def tab_changed(self, index):
        """Обрабатывает событие изменения активной вкладки с ленивой загрузкой."""
        self._load_current_tab(show_overlay=True)

    def _load_current_tab(self, show_overlay: bool = True):
        """Загружает данные текущей вкладки, если они еще не загружены."""
        index = self.tabs.currentIndex()
        if index == 0 and not self._tab_loaded['stats']:
            self.stats_grid.reload(show_overlay=show_overlay)
            self._tab_loaded['stats'] = True
        elif index == 1 and not self._tab_loaded['tournaments']:
            self.tournament_view.reload(show_overlay=show_overlay)
            self._tab_loaded['tournaments'] = True
        elif index == 2 and not self._tab_loaded['sessions']:
            self.session_view.reload(show_overlay=show_overlay)
            self._tab_loaded['sessions'] = True

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Корректно завершает все фоновые потоки перед закрытием окна."""
        logger.debug("Закрытие окна, останавливаем фоновые потоки")
        try:
            thread_manager.cancel_all()
        except Exception as e:
            logger.warning(f"Ошибка при отмене фоновых операций: {e}")

        if hasattr(self, "import_thread") and self.import_thread:
            if self.import_thread.isRunning():
                self.import_thread.cancel()
                self.import_thread.wait()

        if hasattr(self, "refresh_thread") and self.refresh_thread:
            if self.refresh_thread.isRunning():
                self.refresh_thread.quit()
                self.refresh_thread.wait()

        super().closeEvent(event)


# Отдельный поток для импорта, чтобы не блокировать GUI
class ImportThread(QtCore.QThread):
    """Поток для выполнения импорта файлов."""
    # Сигнал для отправки прогресса обратно в основной поток (MainWindow)
    progress_update = QtCore.pyqtSignal(int, int, str)

    def __init__(
        self,
        app_service: AppFacade,
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
            # Передаем progress_update и is_cancelled в AppFacade
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
        finally:
            # Явно закрываем SQLite-соединение этого потока,
            # чтобы избежать его закрытия из другого потока при сборке мусора.
            try:
                self.app_service.db_manager.close_connection()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии соединения в потоке импорта: {e}")
            # Сбрасываем флаг отмены на случай повторного использования потока
            self._is_canceled = False

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
         # TODO: Реализовать проверку флага _is_canceled в AppFacade.import_files
         # и парсерах, чтобы корректно прервать выполнение.


class RefreshThread(QtCore.QThread):
    """Поток для обновления данных без блокировки GUI."""
    progress_update = QtCore.pyqtSignal(str)  # Сигнал для обновления статуса
    progress_percent = QtCore.pyqtSignal(int)  # Сигнал для обновления процентов
    finished_update = QtCore.pyqtSignal()     # Сигнал завершения
    error_occurred = QtCore.pyqtSignal(str)   # Сигнал ошибки
    
    def __init__(self, app_service: AppFacade):
        super().__init__()
        self.app_service = app_service
        
    def run(self):
        """Выполняет обновление данных в отдельном потоке."""
        try:
            self.progress_update.emit("Обновление общей статистики...")
            self.progress_percent.emit(0)

            # Пересчитываем статистику только при первом открытии базы данных
            self.app_service.ensure_overall_stats_cached(
                progress_callback=self._report_progress
            )

            self.progress_update.emit("Данные обновлены")
            self.progress_percent.emit(100)
            self.finished_update.emit()
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных: {e}")
            self.error_occurred.emit(str(e))
    
    def _report_progress(self, step: int, total: int, text: str = ""):
        """Отправляет прогресс в процентах через сигналы Qt."""
        if total > 0:
            percent = int((step / total) * 100)
            self.progress_percent.emit(percent)

            # Используем переданный text или определяем по проценту
            if text:
                self.progress_update.emit(text)
            else:
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
#     def __init__(self, parent=None, app_service: AppFacade = None):
#         super().__init__(parent)
#         self.app_service = app_service
#         self.setWindowTitle("Управление базами данных")
#         # ... UI элементы для выбора/создания БД ...
#         # При выборе/создании: self.app_service.switch_database(selected_path)
#         # или self.app_service.create_new_database(new_name)
#         # Затем self.accept() или self.reject()
#         # ...