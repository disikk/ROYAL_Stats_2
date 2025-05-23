# -*- coding: utf-8 -*-

"""
Диалог управления базами данных для Royal Stats.
Позволяет переключаться между БД, создавать новые и удалять существующие.
"""

from PyQt6 import QtWidgets, QtCore, QtGui
import os
import logging
from typing import Optional, List

import config
from application_service import ApplicationService

logger = logging.getLogger('ROYAL_Stats.DatabaseDialog')


class DatabaseManagementDialog(QtWidgets.QDialog):
    """Диалог для управления базами данных."""
    
    def __init__(self, parent=None, app_service: ApplicationService = None):
        super().__init__(parent)
        self.app_service = app_service
        self.selected_db_path = None
        self._init_ui()
        self._load_databases()
        
    def _init_ui(self):
        """Инициализирует интерфейс диалога."""
        self.setWindowTitle("Управление базами данных")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        header = QtWidgets.QLabel("Выберите базу данных или создайте новую")
        header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #FAFAFA;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(header)
        
        # Список баз данных
        self.db_list = QtWidgets.QListWidget()
        self.db_list.setStyleSheet("""
            QListWidget {
                background-color: #27272A;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #3B82F6;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #3F3F46;
            }
        """)
        self.db_list.itemDoubleClicked.connect(self._on_db_double_clicked)
        layout.addWidget(self.db_list)
        
        # Информация о выбранной БД
        self.info_label = QtWidgets.QLabel("")
        self.info_label.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 12px;
                padding: 8px;
                background-color: #27272A;
                border-radius: 4px;
                border: 1px solid #3F3F46;
            }
        """)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Кнопки управления
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.new_db_btn = QtWidgets.QPushButton("Создать новую БД")
        self.new_db_btn.setIcon(QtGui.QIcon.fromTheme("document-new"))
        self.new_db_btn.clicked.connect(self._create_new_database)
        button_layout.addWidget(self.new_db_btn)
        
        self.delete_db_btn = QtWidgets.QPushButton("Удалить БД")
        self.delete_db_btn.setIcon(QtGui.QIcon.fromTheme("edit-delete"))
        self.delete_db_btn.clicked.connect(self._delete_database)
        self.delete_db_btn.setEnabled(False)  # Активируется при выборе БД
        self.delete_db_btn.setStyleSheet("""
            QPushButton:enabled {
                background-color: #DC2626;
            }
            QPushButton:enabled:hover {
                background-color: #EF4444;
            }
        """)
        button_layout.addWidget(self.delete_db_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Разделитель
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { background-color: #3F3F46; max-height: 1px; }")
        layout.addWidget(separator)
        
        # Кнопки диалога
        dialog_buttons = QtWidgets.QHBoxLayout()
        
        self.select_btn = QtWidgets.QPushButton("Выбрать")
        self.select_btn.setDefault(True)
        self.select_btn.clicked.connect(self._select_database)
        self.select_btn.setEnabled(False)  # Активируется при выборе БД
        dialog_buttons.addWidget(self.select_btn)
        
        self.cancel_btn = QtWidgets.QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(self.cancel_btn)
        
        layout.addLayout(dialog_buttons)
        
        # Подключаем сигналы
        self.db_list.itemSelectionChanged.connect(self._on_selection_changed)
        
    def _load_databases(self):
        """Загружает список доступных баз данных."""
        self.db_list.clear()
        db_files = self.app_service.get_available_databases()
        current_db = self.app_service.db_path
        
        for db_path in db_files:
            db_name = os.path.basename(db_path)
            item = QtWidgets.QListWidgetItem(db_name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, db_path)
            
            # Помечаем текущую БД
            if db_path == current_db:
                item.setText(f"{db_name} (текущая)")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                
            self.db_list.addItem(item)
            
        # Если есть БД, выбираем первую
        if self.db_list.count() > 0:
            self.db_list.setCurrentRow(0)
            
    def _on_selection_changed(self):
        """Обработчик изменения выбора в списке."""
        current_item = self.db_list.currentItem()
        if current_item:
            db_path = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
            self.selected_db_path = db_path
            
            # Обновляем информацию о БД
            try:
                file_size = os.path.getsize(db_path) / 1024 / 1024  # В МБ
                file_time = os.path.getmtime(db_path)
                from datetime import datetime
                mod_date = datetime.fromtimestamp(file_time).strftime("%d.%m.%Y %H:%M")
                
                self.info_label.setText(
                    f"Путь: {db_path}\n"
                    f"Размер: {file_size:.2f} МБ\n"
                    f"Изменен: {mod_date}"
                )
            except Exception as e:
                self.info_label.setText(f"Ошибка получения информации: {e}")
            
            # Активируем кнопки
            self.select_btn.setEnabled(True)
            # Не разрешаем удалять текущую БД
            is_current = db_path == self.app_service.db_path
            self.delete_db_btn.setEnabled(not is_current)
        else:
            self.selected_db_path = None
            self.info_label.setText("")
            self.select_btn.setEnabled(False)
            self.delete_db_btn.setEnabled(False)
            
    def _on_db_double_clicked(self, item):
        """Обработчик двойного клика по БД."""
        if item:
            self._select_database()
            
    def _select_database(self):
        """Выбирает БД и закрывает диалог."""
        if self.selected_db_path and self.selected_db_path != self.app_service.db_path:
            try:
                self.app_service.switch_database(self.selected_db_path)
                self.accept()
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Ошибка", 
                    f"Не удалось переключиться на базу данных:\n{e}"
                )
        else:
            self.accept()
            
    def _create_new_database(self):
        """Создает новую базу данных."""
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Новая база данных",
            "Введите имя для новой базы данных:",
            QtWidgets.QLineEdit.EchoMode.Normal,
            f"royal_stats_{QtCore.QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.db"
        )
        
        if ok and name:
            # Убеждаемся, что имя заканчивается на .db
            if not name.endswith('.db'):
                name += '.db'
                
            try:
                self.app_service.create_new_database(name)
                self._load_databases()  # Перезагружаем список
                
                # Выбираем новую БД
                for i in range(self.db_list.count()):
                    item = self.db_list.item(i)
                    if os.path.basename(item.data(QtCore.Qt.ItemDataRole.UserRole)) == name:
                        self.db_list.setCurrentItem(item)
                        break
                        
                QtWidgets.QMessageBox.information(
                    self,
                    "Успех",
                    f"База данных '{name}' успешно создана и выбрана."
                )
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось создать базу данных:\n{e}"
                )
                
    def _delete_database(self):
        """Удаляет выбранную базу данных."""
        current_item = self.db_list.currentItem()
        if not current_item:
            return
            
        db_path = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
        db_name = os.path.basename(db_path)
        
        # Подтверждение удаления
        reply = QtWidgets.QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить базу данных '{db_name}'?\n\n"
            "Это действие необратимо!",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                # Удаляем файл
                os.remove(db_path)
                
                # Обновляем список
                self._load_databases()
                
                QtWidgets.QMessageBox.information(
                    self,
                    "Успех",
                    f"База данных '{db_name}' успешно удалена."
                )
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось удалить базу данных:\n{e}"
                )