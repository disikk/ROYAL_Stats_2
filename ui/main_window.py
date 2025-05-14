#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Главное окно приложения ROYAL_Stats 2.0.

Управляет отображением статистики и взаимодействием с пользователем.
Поддерживает модульную систему статистики.
"""

import os
import logging
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar,
    QStatusBar, QSplitter, QTreeWidget, QTreeWidgetItem, QMenu,
    QDialog, QInputDialog, QHeaderView, QTableWidget, QTableWidgetItem,
    QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt, QThreadPool, QRunnable, pyqtSignal, pyqtSlot, QObject, QSize
from PyQt6.QtGui import QFont, QAction

# Импорт диалогов и виджетов
from ui.dialogs.db_dialog import DatabaseDialog
from ui.dialogs.session_dialog import SessionDialog
from ui.widgets.stats_grid import StatsGrid
from ui.widgets.session_tree import SessionTree

# Импорт сервисов
from services.file_import import FileImportService
from services.data_analysis import DataAnalysisService


# Сигналы для выполнения задач в отдельном потоке
class WorkerSignals(QObject):
    """
    Сигналы для рабочего потока.
    """
    started = pyqtSignal()
    finished = pyqtSignal()
    progress = pyqtSignal(int, int)  # текущий, всего
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    cancel = pyqtSignal()


class Worker(QRunnable):
    """
    Класс для выполнения задач в отдельном потоке.
    """
    
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        
        self.fn = fn
        self.args = args
        self.kwargs = kwargs 
        self.signals = WorkerSignals()
        self.is_cancelled = False
        
        # Логгер для этого класса
        self.logger = logging.getLogger('ROYAL_Stats.Worker')
        
    @pyqtSlot()
    def run(self):
        """
        Выполняет функцию в отдельном потоке.
        """
        try:
            self.signals.started.emit()
            self.logger.debug(f"Worker начал выполнение функции {self.fn.__name__}")
            
            # Добавляем сигналы и флаг отмены в аргументы функции
            kwargs = self.kwargs.copy()
            kwargs['worker_signals'] = self.signals
            kwargs['is_cancelled'] = lambda: self.is_cancelled
            
            result = self.fn(*self.args, **kwargs)
            
            if not self.is_cancelled:
                self.signals.result.emit(result)
                self.logger.debug(f"Worker успешно выполнил функцию {self.fn.__name__}")
            else:
                self.logger.debug(f"Worker был отменен для функции {self.fn.__name__}")
            
        except Exception as e:
            self.logger.error(f"Ошибка в Worker при выполнении {self.fn.__name__}: {str(e)}", 
                            exc_info=True)
            self.signals.error.emit(str(e))
            
        finally:
            self.signals.finished.emit()
            self.logger.debug(f"Worker завершил выполнение функции {self.fn.__name__}")
    
    def cancel(self):
        """
        Отмена выполнения задачи.
        """
        self.is_cancelled = True
        self.signals.cancel.emit()
        self.logger.debug(f"Запрошена отмена для функции {self.fn.__name__}")


class MainWindow(QMainWindow):
    """
    Главное окно приложения ROYAL_Stats 2.0.
    """
    
    def __init__(self, db_manager, plugin_manager, settings):
        super().__init__()
        
        # Инициализация атрибутов
        self.db_manager = db_manager
        self.plugin_manager = plugin_manager
        self.settings = settings
        
        # Инициализация сервисов
        self.file_import_service = FileImportService(db_manager)
        self.data_analysis_service = DataAnalysisService(db_manager)
        
        # Менеджер потоков для фоновых задач
        self.threadpool = QThreadPool()
        
        # Текущая сессия и рабочий поток
        self.current_session_id = None
        self.current_db_path = None
        self.current_worker = None
        
        # Логгер для этого класса
        self.logger = logging.getLogger('ROYAL_Stats.MainWindow')
        self.logger.info("Инициализация главного окна")
        
        # Инициализация UI
        self._init_ui()
        
        # Показать диалог выбора базы данных
        self._show_database_dialog()
        
    def _init_ui(self):
        """
        Инициализирует элементы интерфейса.
        """
        self.setWindowTitle("ROYAL_Stats 2.0")
        self.setMinimumSize(1200, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        
        # Верхняя панель с кнопками
        toolbar_layout = QHBoxLayout()
        
        # Кнопка выбора базы данных
        self.db_button = QPushButton("Выбрать БД")
        self.db_button.clicked.connect(self._show_database_dialog)
        toolbar_layout.addWidget(self.db_button)
        
        # Кнопка загрузки файлов
        self.load_files_button = QPushButton("Загрузить файлы")
        self.load_files_button.clicked.connect(self._load_files)
        self.load_files_button.setEnabled(False)
        toolbar_layout.addWidget(self.load_files_button)
        
        # Кнопка управления модулями
        self.modules_button = QPushButton("Модули статистики")
        self.modules_button.clicked.connect(self._show_modules_dialog)
        self.modules_button.setEnabled(False)
        toolbar_layout.addWidget(self.modules_button)
        
        # Метка с названием текущей базы данных
        self.db_name_label = QLabel("База данных не выбрана")
        self.db_name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        font = QFont()
        font.setBold(True)
        self.db_name_label.setFont(font)
        toolbar_layout.addWidget(self.db_name_label)
        
        main_layout.addLayout(toolbar_layout)
        
        # Разделитель (сплиттер) для дерева сессий и вкладок
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Дерево сессий
        self.sessions_tree = SessionTree()
        self.sessions_tree.setMinimumWidth(250)
        self.sessions_tree.session_selected.connect(self._on_session_selected)
        splitter.addWidget(self.sessions_tree)
        
        # Вкладки статистики и турниров
        self.tabs = QTabWidget()
        
        # Вкладка с динамическими модулями статистики
        self.stats_tabs = QTabWidget()
        
        # Вкладка с таблицей турниров
        self.tournaments_tab = QWidget()
        tournaments_layout = QVBoxLayout(self.tournaments_tab)
        
        # Таблица турниров
        self.tournaments_table = QTableWidget()
        self.tournaments_table.setColumnCount(7)
        self.tournaments_table.setHorizontalHeaderLabels([
            "ID турнира", "Buy-in", "Место", "Выигрыш", "Нокаутов", "x10 Нокауты", "Дата"
        ])
        self.tournaments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tournaments_layout.addWidget(self.tournaments_table)
        
        # Добавляем вкладки
        self.tabs.addTab(self.stats_tabs, "Статистика")
        self.tabs.addTab(self.tournaments_tab, "Турниры")
        
        splitter.addWidget(self.tabs)
        splitter.setSizes([250, 950])
        main_layout.addWidget(splitter)
        
        # Контейнер для прогресс-бара и метки прогресса
        progress_container = QVBoxLayout()
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_container.addWidget(self.progress_bar)
        
        # Метка для отображения статуса обработки файлов
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setVisible(False)
        progress_container.addWidget(self.progress_label)
        
        # Кнопка отмены загрузки
        self.cancel_button = QPushButton("Отменить загрузку")
        self.cancel_button.clicked.connect(self._cancel_loading)
        self.cancel_button.setVisible(False)
        progress_container.addWidget(self.cancel_button)
        
        main_layout.addLayout(progress_container)
        
        # Строка состояния
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")
        
        # Создание меню
        self._create_menu()
        
    def _create_menu(self):
        """
        Создает главное меню приложения.
        """
        # Меню "Файл"
        file_menu = self.menuBar().addMenu("Файл")
        
        select_db_action = QAction("Выбрать базу данных", self)
        select_db_action.triggered.connect(self._show_database_dialog)
        file_menu.addAction(select_db_action)
        
        load_files_action = QAction("Загрузить файлы", self)
        load_files_action.triggered.connect(self._load_files)
        file_menu.addAction(load_files_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню "Сессия"
        session_menu = self.menuBar().addMenu("Сессия")
        
        new_session_action = QAction("Новая сессия", self)
        new_session_action.triggered.connect(self._create_new_session)
        session_menu.addAction(new_session_action)
        
        rename_session_action = QAction("Переименовать сессию", self)
        rename_session_action.triggered.connect(self._rename_selected_session)
        session_menu.addAction(rename_session_action)
        
        delete_session_action = QAction("Удалить сессию", self)
        delete_session_action.triggered.connect(self._delete_selected_session)
        session_menu.addAction(delete_session_action)
        
        # Меню "Инструменты"
        tools_menu = self.menuBar().addMenu("Инструменты")
        
        modules_action = QAction("Модули статистики", self)
        modules_action.triggered.connect(self._show_modules_dialog)
        tools_menu.addAction(modules_action)
        
        update_stats_action = QAction("Обновить статистику", self)
        update_stats_action.triggered.connect(self._update_statistics)
        tools_menu.addAction(update_stats_action)
        
        clear_data_action = QAction("Очистить все данные", self)
        clear_data_action.triggered.connect(self._clear_all_data)
        tools_menu.addAction(clear_data_action)
        
    def _show_database_dialog(self):
        """
        Показывает диалог выбора базы данных.
        """
        dialog = DatabaseDialog(self.db_manager, self)
        dialog.db_selected.connect(self._on_database_selected)
        dialog.exec()
        
    def _on_database_selected(self, db_path):
        """
        Обработчик выбора базы данных.
        
        Args:
            db_path: Путь к выбранной базе данных
        """
        self.current_db_path = db_path
        db_name = os.path.basename(db_path)
        
        self.db_name_label.setText(f"База данных: {db_name}")
        self.load_files_button.setEnabled(True)
        self.modules_button.setEnabled(True)
        
        try:
            # Подключаемся к базе данных
            self.db_manager.connect(db_path)
            
            # Загружаем список сессий
            self._load_sessions()
            
            # Загружаем статистику
            self._update_statistics()
            
            self.status_bar.showMessage(f"Подключено к базе данных {db_name}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при подключении к базе данных: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к базе данных: {str(e)}")
            
            self.load_files_button.setEnabled(False)
            self.modules_button.setEnabled(False)
            self.db_name_label.setText("Ошибка подключения к БД")
            
    def _load_sessions(self):
        """
        Загружает список сессий из базы данных и обновляет дерево сессий.
        """
        try:
            # Получаем список сессий из БД
            sessions = self.data_analysis_service.get_sessions()
            
            # Обновляем дерево сессий
            self.sessions_tree.update_sessions(sessions)
            
            # Выбираем "Все сессии" по умолчанию
            self.sessions_tree.select_all_sessions()
            
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке сессий: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список сессий: {str(e)}")
            
    def _on_session_selected(self, session_id):
        """
        Обработчик выбора сессии в дереве.
        
        Args:
            session_id: ID выбранной сессии или None для "Все сессии"
        """
        self.current_session_id = session_id
        
        # Обновляем статистику для выбранной сессии
        self._update_statistics(session_id)
        
        # Загружаем список турниров для выбранной сессии
        if session_id:
            self._load_session_tournaments(session_id)
        else:
            self._load_all_tournaments()
            
    def _create_new_session(self):
        """
        Создает новую сессию.
        
        Returns:
            ID созданной сессии или None, если сессия не была создана
        """
        if not self.db_manager.is_connected():
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите базу данных!")
            return None
            
        # Показываем диалог создания новой сессии
        dialog = SessionDialog(self)
        if dialog.exec():
            session_name = dialog.get_session_name()
            
            try:
                # Создаем новую сессию
                session_id = self.data_analysis_service.create_session(session_name)
                
                # Обновляем список сессий
                self._load_sessions()
                
                # Выбираем созданную сессию
                self.sessions_tree.select_session(session_id)
                
                self.status_bar.showMessage(f"Создана новая сессия: {session_name}")
                return session_id
                
            except Exception as e:
                self.logger.error(f"Ошибка при создании сессии: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать сессию: {str(e)}")
                
        return None
        
    def _rename_selected_session(self):
        """
        Переименовывает выбранную сессию.
        """
        session_id = self.current_session_id
        if not session_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите сессию для переименования!")
            return
            
        # Получаем информацию о сессии
        session_info = self.data_analysis_service.get_session_info(session_id)
        if not session_info:
            QMessageBox.warning(self, "Предупреждение", "Сессия не найдена!")
            return
            
        # Показываем диалог переименования сессии
        dialog = SessionDialog(self, session_name=session_info.get('session_name', ''))
        if dialog.exec():
            new_name = dialog.get_session_name()
            
            try:
                # Переименовываем сессию
                self.data_analysis_service.rename_session(session_id, new_name)
                
                # Обновляем список сессий
                self._load_sessions()
                
                # Выбираем переименованную сессию
                self.sessions_tree.select_session(session_id)
                
                self.status_bar.showMessage(f"Сессия переименована в '{new_name}'")
                
            except Exception as e:
                self.logger.error(f"Ошибка при переименовании сессии: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать сессию: {str(e)}")
                
    def _delete_selected_session(self):
        """
        Удаляет выбранную сессию.
        """
        session_id = self.current_session_id
        if not session_id:
            QMessageBox.warning(self, "Предупреждение", "Выберите сессию для удаления!")
            return
            
        # Получаем информацию о сессии
        session_info = self.data_analysis_service.get_session_info(session_id)
        if not session_info:
            QMessageBox.warning(self, "Предупреждение", "Сессия не найдена!")
            return
            
        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self, 
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить сессию '{session_info.get('session_name', '')}'?\n"
            "Все данные этой сессии будут удалены безвозвратно!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Удаляем сессию
                self.data_analysis_service.delete_session(session_id)
                
                # Обновляем список сессий
                self._load_sessions()
                
                # Выбираем "Все сессии"
                self.sessions_tree.select_all_sessions()
                
                self.status_bar.showMessage("Сессия успешно удалена")
                
            except Exception as e:
                self.logger.error(f"Ошибка при удалении сессии: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить сессию: {str(e)}")
                
    def _show_modules_dialog(self):
        """
        Показывает диалог управления модулями статистики.
        """
        # В будущем здесь будет диалог управления модулями
        # Пока просто выводим информацию о доступных модулях
        modules = self.plugin_manager.get_all_modules()
        active_modules = self.plugin_manager.get_active_modules()
        
        message = "Доступные модули статистики:\n\n"
        for module in modules:
            status = "Активен" if module.name in [m.name for m in active_modules] else "Неактивен"
            message += f"- {module.display_name} ({module.name}): {status}\n"
            
        QMessageBox.information(self, "Модули статистики", message)
        
    def _load_files(self):
        """
        Загружает файлы истории рук и сводки турниров.
        """
        if not self.db_manager.is_connected():
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите базу данных!")
            return
            
        # Выбор между файлами и папкой
        choice_dialog = QDialog(self)
        choice_dialog.setWindowTitle("Выбор источника файлов")
        choice_layout = QVBoxLayout(choice_dialog)
        
        instruction_label = QLabel("Выберите способ загрузки файлов:")
        choice_layout.addWidget(instruction_label)
        
        files_button = QPushButton("Выбрать файлы")
        folder_button = QPushButton("Выбрать папку")
        
        choice_layout.addWidget(files_button)
        choice_layout.addWidget(folder_button)
        
        file_paths_to_process = []
        choice_dialog_result = [False]
        
        def on_files_clicked():
            dialog = QFileDialog(self)
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setWindowTitle("Выберите файлы истории")
            dialog.setNameFilter("Текстовые файлы (*.txt)")
            if dialog.exec():
                nonlocal file_paths_to_process
                file_paths_to_process = dialog.selectedFiles()
                choice_dialog_result[0] = True
                choice_dialog.accept()
        
        def on_folder_clicked():
            dialog = QFileDialog(self)
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
            dialog.setWindowTitle("Выберите папку с файлами истории")
            if dialog.exec():
                nonlocal file_paths_to_process
                selected_folder = dialog.selectedFiles()[0]
                for root, _, files in os.walk(selected_folder):
                    for file in files:
                        if file.endswith('.txt'):
                            file_paths_to_process.append(os.path.join(root, file))
                choice_dialog_result[0] = True
                choice_dialog.accept()
        
        files_button.clicked.connect(on_files_clicked)
        folder_button.clicked.connect(on_folder_clicked)
        
        # Показываем диалог выбора
        choice_dialog.exec()
        
        # Если выбор не был сделан или список файлов пуст, выходим
        if not choice_dialog_result[0] or not file_paths_to_process:
            return
        
        # Проверяем, нужна ли новая сессия
        session_id_for_processing = self.current_session_id
        if not session_id_for_processing:
            session_id_for_processing = self._create_new_session()
            if not session_id_for_processing:
                return
        
        # Настраиваем прогресс-бар и связанные элементы
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(file_paths_to_process))
        self.progress_bar.setValue(0)
        
        self.progress_label.setText(f"Обработано 0 из {len(file_paths_to_process)} файлов")
        self.progress_label.setVisible(True)
        
        self.cancel_button.setVisible(True)
        self.load_files_button.setEnabled(False)
        
        # Создаем и запускаем Worker
        worker = Worker(
            self.file_import_service.process_files,
            file_paths_to_process,
            session_id_for_processing
        )
        self.current_worker = worker
        
        worker.signals.started.connect(lambda: self.status_bar.showMessage("Обработка файлов..."))
        worker.signals.finished.connect(self._on_files_processing_finished)
        worker.signals.error.connect(self._on_files_processing_error)
        worker.signals.result.connect(self._on_files_processing_result)
        worker.signals.progress.connect(self._update_progress)
        
        # Запускаем Worker
        self.threadpool.start(worker)
        
    def _cancel_loading(self):
        """
        Отменяет текущую операцию загрузки файлов.
        """
        if self.current_worker:
            self.current_worker.cancel()
            self.status_bar.showMessage("Загрузка отменена пользователем", 5000)
            
    def _update_progress(self, value, total):
        """
        Обновляет прогресс-бар и метку прогресса.
        
        Args:
            value: Текущее значение прогресса
            total: Общее количество элементов
        """
        if self.progress_bar.isVisible():
            self.progress_bar.setValue(value)
            self.progress_label.setText(f"Обработано {value} из {total} файлов")
            
    def _on_files_processing_result(self, results):
        """
        Обработчик успешного завершения обработки файлов.
        
        Args:
            results: Результаты обработки файлов
        """
        if not isinstance(results, dict):
            self.logger.error(f"Получен некорректный результат обработки файлов: {results}")
            QMessageBox.critical(self, "Ошибка", "Внутренняя ошибка при обработке файлов.")
            return

        if results.get('cancelled'):
            self.status_bar.showMessage("Операция была отменена пользователем", 5000)
            return
            
        if results.get('errors'):
            error_message = "При обработке файлов возникли ошибки:\n\n"
            error_message += "\n".join(results['errors'][:5])
            if len(results['errors']) > 5:
                error_message += f"\n\n...и еще {len(results['errors']) - 5} ошибок."
            QMessageBox.warning(self, "Предупреждение", error_message)
        
        stats_message = (
            f"Всего файлов: {results.get('total_files', 0)}, "
            f"Сводок: {results.get('tournament_summary_files_found', 0)}, "
            f"Историй: {results.get('hand_history_files_found', 0)}, "
            f"Обработано турниров: {results.get('processed_tournaments',0)}, "
            f"Нокаутов: {results.get('processed_knockouts',0)}"
        )
        
        self.status_bar.showMessage(stats_message, 10000)
        
    def _on_files_processing_finished(self):
        """
        Обработчик завершения обработки файлов.
        """
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.cancel_button.setVisible(False)
        self.load_files_button.setEnabled(True)
        self.current_worker = None
        
        # Обновляем интерфейс
        self._load_sessions()
        self._update_statistics(self.current_session_id)
        
    def _on_files_processing_error(self, error_message):
        """
        Обработчик ошибки при обработке файлов.
        
        Args:
            error_message: Сообщение об ошибке
        """
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.cancel_button.setVisible(False)
        self.load_files_button.setEnabled(True)
        self.current_worker = None
        
        QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке файлов: {error_message}")
        
        # Обновляем интерфейс
        self._load_sessions()
        self._update_statistics(self.current_session_id)
        
    def _update_statistics(self, session_id=None):
        """
        Обновляет статистику и графики для указанной сессии.
        
        Args:
            session_id: ID сессии для фильтрации (None для всех сессий)
        """
        try:
            # Обновляем общую статистику
            self.data_analysis_service.update_statistics(session_id)
            
            # Получаем активные модули статистики
            active_modules = self.plugin_manager.get_active_modules()
            
            # Создаем виджеты для активных модулей
            self._create_stats_widgets(active_modules, session_id)
            
            self.status_bar.showMessage("Статистика обновлена", 3000)
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении статистики: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить статистику: {str(e)}")
            
    def _create_stats_widgets(self, modules, session_id=None):
        """
        Создает виджеты для всех активных модулей статистики.
        
        Args:
            modules: Список модулей статистики
            session_id: ID сессии для фильтрации данных (опционально)
        """
        # Очищаем контейнер с вкладками
        self.stats_tabs.clear()
        
        # Получаем статистику для всех модулей
        stats_results = self.plugin_manager.calculate_statistics(session_id)
        
        # Создаем вкладку для каждого модуля
        for module in modules:
            # Получаем результаты вычислений
            results = stats_results.get(module.name, {})
            
            # Создаем вкладку
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            
            # Создаем сетку карточек
            cards_config = module.get_cards_config()
            cards_grid = StatsGrid()
            cards_grid.create_cards(cards_config)
            cards_grid.update_values(results)
            tab_layout.addWidget(cards_grid)
            
            # Создаем график
            chart_widget = module.create_chart_widget(results)
            if chart_widget:
                tab_layout.addWidget(chart_widget)
            
            # Добавляем вкладку
            self.stats_tabs.addTab(tab, module.display_name)
            
    def _load_all_tournaments(self):
        """
        Загружает список всех турниров из базы данных.
        """
        try:
            tournaments = self.data_analysis_service.get_all_tournaments()
            self._update_tournaments_table(tournaments)
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке турниров: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить турниры: {str(e)}")
            
    def _load_session_tournaments(self, session_id):
        """
        Загружает список турниров указанной сессии.
        
        Args:
            session_id: ID сессии
        """
        try:
            tournaments = self.data_analysis_service.get_session_tournaments(session_id)
            self._update_tournaments_table(tournaments)
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке турниров сессии: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить турниры сессии: {str(e)}")
            
    def _update_tournaments_table(self, tournaments):
        """
        Обновляет таблицу турниров.
        
        Args:
            tournaments: Список турниров
        """
        self.tournaments_table.setRowCount(0)
        
        for row_idx, tournament in enumerate(tournaments):
            self.tournaments_table.insertRow(row_idx)
            
            self.tournaments_table.setItem(row_idx, 0, QTableWidgetItem(str(tournament.get('tournament_id', 'N/A'))))
            
            buy_in = tournament.get('buy_in', 0)
            self.tournaments_table.setItem(row_idx, 1, QTableWidgetItem(f"${buy_in:.2f}" if buy_in is not None else 'N/A'))
            
            self.tournaments_table.setItem(row_idx, 2, QTableWidgetItem(str(tournament.get('finish_place', 'N/A'))))
            
            prize = tournament.get('prize', 0)
            self.tournaments_table.setItem(row_idx, 3, QTableWidgetItem(f"${prize:.2f}" if prize is not None else 'N/A'))
            
            knockouts_count = tournament.get('knockouts_count', 0)
            self.tournaments_table.setItem(row_idx, 4, QTableWidgetItem(str(knockouts_count)))
            
            knockouts_x10 = tournament.get('knockouts_x10', 0)
            self.tournaments_table.setItem(row_idx, 5, QTableWidgetItem(str(knockouts_x10)))
            
            start_time = tournament.get('start_time', 'N/A')
            self.tournaments_table.setItem(row_idx, 6, QTableWidgetItem(start_time))
            
    def _clear_all_data(self):
        """
        Очищает все данные в текущей базе.
        """
        if not self.db_manager.is_connected():
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите базу данных!")
            return
            
        reply = QMessageBox.question(
            self, 
            "Подтверждение очистки",
            "Вы уверены, что хотите очистить все данные в базе?\n"
            "Это действие невозможно отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data_analysis_service.clear_all_data()
                
                # Обновляем интерфейс
                self._load_sessions()
                self._update_statistics()
                self.tournaments_table.setRowCount(0)
                
                self.status_bar.showMessage("Все данные успешно очищены")
                
            except Exception as e:
                self.logger.error(f"Ошибка при очистке данных: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", f"Не удалось очистить данные: {str(e)}")
                
    def closeEvent(self, event):
        """
        Обработчик закрытия окна приложения.
        """
        self.logger.info("Закрытие приложения.")
        
        # Ожидаем завершения всех потоков
        self.threadpool.waitForDone()
        
        # Закрываем соединение с БД
        if self.db_manager:
            self.db_manager.close()
            
        event.accept()