# -*- coding: utf-8 -*-

"""
Представление для отображения списка игровых сессий.
"""

from PyQt6 import QtWidgets, QtCore, QtGui
import logging
from typing import List, Optional

from ui.app_style import setup_table_widget, format_money, apply_cell_color_by_value
from application_service import ApplicationService
from models import Session
from ui.background import thread_manager

logger = logging.getLogger('ROYAL_Stats.SessionView')
logger.setLevel(logging.DEBUG)


class SessionView(QtWidgets.QWidget):
    """Виджет для отображения списка игровых сессий."""
    
    def __init__(self, app_service: ApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        self.sessions: List[Session] = []
        self._data_cache = {}  # Кеш для данных
        self._cache_valid = False  # Флаг валидности кеша
        self._init_ui()
        
    def _init_ui(self):
        """Инициализирует интерфейс."""
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Контейнер для содержимого
        self.content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок
        header = QtWidgets.QLabel("Игровые сессии")
        header.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #FAFAFA;
                margin-bottom: 16px;
            }
        """)
        content_layout.addWidget(header)
        
        # Описание
        description = QtWidgets.QLabel(
            "Сессии группируют турниры, загруженные за один раз. "
            "Это позволяет анализировать результаты отдельных игровых периодов."
        )
        description.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 13px;
                margin-bottom: 16px;
            }
        """)
        description.setWordWrap(True)
        content_layout.addWidget(description)
        
        # Таблица сессий
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Название сессии", "Дата создания", "Турниров", 
            "Бай-ин", "Выплаты", "Профит", "KO", "Ср. место"
        ])
        
        setup_table_widget(self.table)
        
        # Настройка ширины колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        
        # Контекстное меню для таблицы
        self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        content_layout.addWidget(self.table)
        
        # Панель кнопок
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.delete_btn = QtWidgets.QPushButton("Удалить сессию")
        self.delete_btn.setIcon(QtGui.QIcon.fromTheme("edit-delete"))
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete_session)
        self.delete_btn.setStyleSheet("""
            QPushButton:enabled {
                background-color: #DC2626;
            }
            QPushButton:enabled:hover {
                background-color: #EF4444;
            }
        """)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        content_layout.addLayout(button_layout)
        
        # Подключаем сигналы
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
        self.main_layout.addWidget(self.content_widget)
        
        # Создаем loading overlay
        self._create_loading_overlay()
        
    def _create_loading_overlay(self):
        """Создает оверлей загрузки."""
        self.loading_overlay = QtWidgets.QWidget(self)
        self.loading_overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.7);
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self.loading_overlay)
        
        # Контейнер для индикатора
        container = QtWidgets.QWidget()
        container.setMaximumWidth(300)
        container.setStyleSheet("""
            QWidget {
                background-color: #27272A;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        container_layout = QtWidgets.QVBoxLayout(container)
        
        # Индикатор загрузки
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3F3F46;
                border-radius: 6px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 6px;
            }
        """)
        container_layout.addWidget(self.progress_bar)
        
        # Текст загрузки
        self.loading_label = QtWidgets.QLabel("Загрузка сессий...")
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #FAFAFA;
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
            }
        """)
        self.loading_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.loading_label)
        
        layout.addWidget(container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        
        self.loading_overlay.hide()
        
    def show_loading_overlay(self):
        """Показывает оверлей загрузки."""
        self.loading_overlay.resize(self.size())
        self.loading_overlay.raise_()
        self.loading_overlay.show()
        
    def hide_loading_overlay(self):
        """Скрывает оверлей загрузки."""
        self.loading_overlay.hide()
        
    def resizeEvent(self, event):
        """Обрабатывает изменение размера виджета."""
        super().resizeEvent(event)
        # Обновляем размер оверлея при изменении размера виджета
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(self.size())
            
    def invalidate_cache(self):
        """Сбрасывает кеш данных."""
        self._cache_valid = False
        self._data_cache.clear()
        
    def reload(self, show_overlay: bool = True):
        """Перезагружает данные из ApplicationService."""
        logger.debug("Перезагрузка SessionView...")
        self._show_overlay = show_overlay
        if show_overlay:
            self.show_loading_overlay()
        def load_data():
            return self.app_service.get_all_sessions()
        thread_manager.run_in_thread(
            widget_id=str(id(self)),
            fn=load_data,
            callback=self._on_data_loaded,
            error_callback=lambda e: logger.error(f"Ошибка загрузки данных SessionView: {e}"),
            owner=self
        )

    def _on_data_loaded(self, sessions):
        """Применяет загруженные данные к UI."""
        try:
            self.sessions = sessions
            self._cache_valid = True
            self._update_sessions_table()
            logger.debug("Перезагрузка SessionView завершена.")
        finally:
            if getattr(self, "_show_overlay", False):
                self.hide_loading_overlay()
            
    def _load_data(self):
        """Загружает данные из ApplicationService в кеш."""
        logger.debug("Загрузка данных в кеш SessionView...")
        
        # Загружаем все сессии
        self.sessions = self.app_service.get_all_sessions()
        self._data_cache['sessions'] = self.sessions
        
        logger.debug(f"Загружено {len(self.sessions)} сессий")
        
    def _update_sessions_table(self):
        """Обновляет таблицу сессий."""
        self.table.setRowCount(len(self.sessions))
        
        for row, session in enumerate(self.sessions):
            # Название сессии
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(session.session_name))
            
            # Дата создания
            created_date = session.created_at or "-"
            if session.created_datetime:
                created_date = session.created_datetime.strftime("%d.%m.%Y %H:%M")
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(created_date))
            
            # Количество турниров
            tournaments_item = QtWidgets.QTableWidgetItem(str(session.tournaments_count))
            tournaments_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, tournaments_item)
            
            # Бай-ин
            buyin_item = QtWidgets.QTableWidgetItem(format_money(session.total_buy_in))
            buyin_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, buyin_item)
            
            # Выплаты
            payout_item = QtWidgets.QTableWidgetItem(format_money(session.total_prize))
            payout_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, payout_item)
            
            # Профит
            profit = session.total_prize - session.total_buy_in
            profit_item = QtWidgets.QTableWidgetItem(format_money(profit, with_plus=True))
            profit_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(profit_item, profit)
            self.table.setItem(row, 5, profit_item)
            
            # KO
            ko_item = QtWidgets.QTableWidgetItem(str(session.knockouts_count))
            ko_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if session.knockouts_count > 0:
                ko_item.setForeground(QtGui.QBrush(QtGui.QColor("#10B981")))
            self.table.setItem(row, 6, ko_item)
            
            # Среднее место
            avg_place_item = QtWidgets.QTableWidgetItem(f"{session.avg_finish_place:.2f}")
            avg_place_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 7, avg_place_item)
            
            # Сохраняем session_id в строке для дальнейшего использования
            self.table.item(row, 0).setData(QtCore.Qt.ItemDataRole.UserRole, session.session_id)
            
    def _on_selection_changed(self):
        """Обработчик изменения выбора в таблице."""
        selected = self.table.selectedItems()
        self.delete_btn.setEnabled(len(selected) > 0)
        
    def _show_context_menu(self, position):
        """Показывает контекстное меню для таблицы."""
        item = self.table.itemAt(position)
        if not item:
            return
            
        menu = QtWidgets.QMenu(self)
        
        # Действие просмотра турниров сессии
        view_action = menu.addAction(QtGui.QIcon.fromTheme("view-list-details"), "Показать турниры сессии")
        view_action.triggered.connect(lambda: self._view_session_tournaments(item.row()))
        
        # Действие удаления
        delete_action = menu.addAction(QtGui.QIcon.fromTheme("edit-delete"), "Удалить сессию")
        delete_action.triggered.connect(lambda: self._delete_session())
        
        menu.exec(self.table.mapToGlobal(position))
        
    def _view_session_tournaments(self, row: int):
        """Показывает турниры выбранной сессии."""
        # В простой версии просто показываем сообщение
        # В полной версии можно было бы открыть диалог или переключиться на вкладку турниров с фильтром
        session = self.sessions[row]
        QtWidgets.QMessageBox.information(
            self,
            "Турниры сессии",
            f"В сессии '{session.session_name}' сыграно {session.tournaments_count} турниров.\n\n"
            f"Для просмотра турниров перейдите на вкладку 'Турниры' и используйте фильтры."
        )
        
    def _delete_session(self):
        """Удаляет выбранную сессию."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        session = self.sessions[current_row]
        reply = QtWidgets.QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить сессию '{session.session_name}'?\n\n"
            f"Будут удалены:\n"
            f"- {session.tournaments_count} турниров\n"
            f"- Все связанные руки финального стола\n\n"
            "Это действие необратимо!",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.show_loading_overlay()
            self.loading_label.setText("Удаление сессии...")
            def delete_session():
                self.app_service.delete_session(session.session_id)
                self.app_service._update_all_statistics(None)
                return session.session_name
            thread_manager.run_in_thread(
                widget_id=f"{id(self)}_delete",
                fn=delete_session,
                callback=self._on_delete_finished,
                error_callback=self._on_delete_error,
                owner=self
            )

    def _on_delete_finished(self, session_name: str):
        """Вызывается при успешном удалении сессии."""
        self.hide_loading_overlay()
        self.invalidate_cache()
        self.reload()
        QtWidgets.QMessageBox.information(
            self,
            "Успех",
            f"Сессия '{session_name}' и все связанные данные успешно удалены."
        )
        main_window = self.window()
        if hasattr(main_window, 'refresh_all_data'):
            main_window.refresh_all_data()

    def _on_delete_error(self, error):
        """Вызывается при ошибке удаления."""
        self.hide_loading_overlay()
        QtWidgets.QMessageBox.critical(
            self,
            "Ошибка",
            f"Не удалось удалить сессию:\n{str(error)}"
        )

