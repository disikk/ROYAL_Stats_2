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

logger = logging.getLogger('ROYAL_Stats.SessionView')
logger.setLevel(logging.DEBUG)


class SessionView(QtWidgets.QWidget):
    """Виджет для отображения списка игровых сессий."""
    
    def __init__(self, app_service: ApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        self.sessions: List[Session] = []
        self._init_ui()
        
    def _init_ui(self):
        """Инициализирует интерфейс."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
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
        layout.addWidget(header)
        
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
        layout.addWidget(description)
        
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
        
        layout.addWidget(self.table)
        
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
        
        layout.addLayout(button_layout)
        
        # Подключаем сигналы
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        
    def reload(self):
        """Перезагружает данные из ApplicationService."""
        logger.debug("Перезагрузка SessionView...")
        
        # Загружаем все сессии
        self.sessions = self.app_service.get_all_sessions()
        
        # Обновляем таблицу
        self._update_sessions_table()
        
        logger.debug("Перезагрузка SessionView завершена.")
        
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
        
        # Подтверждение удаления
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
            try:
                # Удаляем сессию через ApplicationService
                self.app_service.delete_session(session.session_id)
                
                # Перезагружаем данные
                self.reload()
                
                # Оповещаем пользователя
                QtWidgets.QMessageBox.information(
                    self,
                    "Успех",
                    f"Сессия '{session.session_name}' и все связанные данные успешно удалены."
                )
                
                # Оповещаем родительское окно о необходимости обновить все данные
                main_window = self.window()  # Получаем главное окно
                if hasattr(main_window, 'refresh_all_data'):
                    main_window.refresh_all_data()
                    
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось удалить сессию:\n{e}"
                )