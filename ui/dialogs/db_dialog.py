#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Диалог выбора и создания баз данных для покерного трекера ROYAL_Stats.
"""

import os
import logging
from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QLineEdit, QMessageBox, QFileDialog, QInputDialog,
    QApplication, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.DatabaseDialog')


class DatabaseDialog(QDialog):
    """
    Диалог для выбора существующей или создания новой базы данных.
    """
    
    # Сигналы
    db_selected = pyqtSignal(str)  # Сигнал, содержащий путь к выбранной БД
    
    def __init__(self, db_manager, parent=None):
        """
        Инициализирует диалог выбора БД.
        
        Args:
            db_manager: Экземпляр DatabaseManager
            parent: Родительский виджет
        """
        super().__init__(parent)
        
        self.db_manager = db_manager
        
        self.setWindowTitle("Выбор базы данных")
        self.setMinimumSize(500, 400)
        
        # Настройка стиля диалога
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                color: #212529;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #e9ecef;
            }
            QListWidget::item:selected {
                background-color: #e9ecef;
                color: #212529;
            }
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px 10px;
                color: #212529;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """)
        
        self._init_ui()
        self._load_databases()
    
    def _init_ui(self):
        """
        Инициализирует элементы интерфейса.
        """
        # Основной layout
        main_layout = QVBoxLayout(self)
        
        # Заголовок
        title_label = QLabel("Выберите базу данных или создайте новую")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # Список доступных БД
        self.db_list = QListWidget()
        self.db_list.setAlternatingRowColors(True)
        self.db_list.itemDoubleClicked.connect(self._on_db_double_clicked)
        main_layout.addWidget(self.db_list)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.create_button = QPushButton("Создать")
        self.create_button.clicked.connect(self._on_create_button_clicked)
        buttons_layout.addWidget(self.create_button)
        
        self.import_button = QPushButton("Импортировать")
        self.import_button.clicked.connect(self._on_import_button_clicked)
        buttons_layout.addWidget(self.import_button)
        
        self.delete_button = QPushButton("Удалить")
        self.delete_button.clicked.connect(self._on_delete_button_clicked)
        buttons_layout.addWidget(self.delete_button)
        
        self.select_button = QPushButton("Выбрать")
        self.select_button.clicked.connect(self._on_select_button_clicked)
        self.select_button.setDefault(True)
        buttons_layout.addWidget(self.select_button)
        
        main_layout.addLayout(buttons_layout)
    
    def _load_databases(self):
        """
        Загружает список доступных баз данных.
        """
        self.db_list.clear()
        
        try:
            databases = self.db_manager.get_available_databases()
            
            for db_name in databases:
                item = QListWidgetItem(db_name)
                
                # Добавляем информацию о выбранной БД
                if self.db_manager.current_db_path and os.path.basename(self.db_manager.current_db_path) == db_name:
                    item.setFont(QFont("", weight=QFont.Weight.Bold))
                    item.setText(f"{db_name} (текущая)")
                
                self.db_list.addItem(item)
        except Exception as e:
            logger.error(f"Ошибка при загрузке списка баз данных: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список баз данных: {str(e)}")
    
    def _on_create_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Создать".
        """
        db_name, ok = QInputDialog.getText(
            self, "Новая база данных", 
            "Введите имя для новой базы данных:"
        )
        
        if ok and db_name:
            # Проверяем, что имя базы данных уникально
            if not db_name.endswith('.db'):
                db_name += '.db'
                
            db_path = os.path.join(self.db_manager.db_folder, db_name)
            if os.path.exists(db_path):
                QMessageBox.warning(
                    self, 
                    "Ошибка", 
                    f"База данных с именем {db_name} уже существует!"
                )
                return
                
            # Создаем новую базу данных
            try:
                db_path = self.db_manager.create_database(db_name)
                self._load_databases()
                
                # Выбираем созданную БД в списке
                for i in range(self.db_list.count()):
                    item = self.db_list.item(i)
                    if item.text() == db_name or item.text().startswith(f"{db_name} "):
                        self.db_list.setCurrentItem(item)
                        break
                        
                QMessageBox.information(
                    self,
                    "Успех",
                    f"База данных {db_name} успешно создана!"
                )
            except Exception as e:
                logger.error(f"Ошибка при создании базы данных: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось создать базу данных: {str(e)}"
                )
    
    def _on_import_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Импортировать".
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл базы данных",
            "",
            "SQLite Database (*.db);;All Files (*)"
        )
        
        if file_path:
            # Получаем имя файла
            db_name = os.path.basename(file_path)
            
            # Проверяем, что файл с таким именем не существует
            target_path = os.path.join(self.db_manager.db_folder, db_name)
            if os.path.exists(target_path):
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"База данных с именем {db_name} уже существует!"
                )
                return
                
            # Копируем файл в папку баз данных
            try:
                import shutil
                shutil.copy2(file_path, target_path)
                
                # Проверяем, что это действительно база данных SQLite
                try:
                    import sqlite3
                    conn = sqlite3.connect(target_path)
                    # Проверяем наличие необходимых таблиц
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    
                    # В новой версии имена таблиц могут отличаться
                    required_tables = ['tournaments', 'knockouts', 'sessions']
                    
                    missing_tables = []
                    for table in required_tables:
                        if (table,) not in tables:
                            missing_tables.append(table)
                            
                    conn.close()
                    
                    if missing_tables:
                        # Не все требуемые таблицы найдены
                        reply = QMessageBox.question(
                            self,
                            "Предупреждение",
                            f"Файл не является базой данных ROYAL_Stats 2.0 или имеет неверную структуру. "
                            f"Отсутствуют таблицы: {', '.join(missing_tables)}. "
                            f"\nВы хотите инициализировать базу данных заново?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.Yes
                        )
                        
                        if reply == QMessageBox.StandardButton.Yes:
                            # Инициализируем базу данных
                            self.db_manager.connect(target_path)
                            # В новой версии создание таблиц происходит автоматически при connect
                        else:
                            # Удаляем скопированный файл
                            os.remove(target_path)
                            QMessageBox.information(
                                self,
                                "Информация",
                                "Импорт базы данных отменен."
                            )
                            return
                except Exception as e:
                    # Если возникла ошибка при проверке базы, спрашиваем пользователя
                    reply = QMessageBox.question(
                        self,
                        "Предупреждение",
                        f"Файл не является базой данных SQLite или поврежден. "
                        f"Ошибка: {str(e)}\n"
                        f"\nВы хотите инициализировать базу данных заново?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        # Инициализируем базу данных
                        self.db_manager.connect(target_path)
                        # В новой версии создание таблиц происходит автоматически при connect
                    else:
                        # Удаляем скопированный файл
                        os.remove(target_path)
                        QMessageBox.information(
                            self,
                            "Информация",
                            "Импорт базы данных отменен."
                        )
                        return
                    
                # Обновляем список баз данных
                self._load_databases()
                
                # Выбираем импортированную БД в списке
                for i in range(self.db_list.count()):
                    item = self.db_list.item(i)
                    if item.text() == db_name or item.text().startswith(f"{db_name} "):
                        self.db_list.setCurrentItem(item)
                        break
                        
                QMessageBox.information(
                    self,
                    "Успех",
                    f"База данных {db_name} успешно импортирована!"
                )
            except Exception as e:
                logger.error(f"Ошибка при импорте базы данных: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось импортировать базу данных: {str(e)}"
                )
    
    def _on_delete_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Удалить".
        """
        # Получаем выбранную БД
        current_item = self.db_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите базу данных для удаления!"
            )
            return
            
        db_name = current_item.text()
        # Удаляем " (текущая)" из имени, если есть
        if " (текущая)" in db_name:
            db_name = db_name.replace(" (текущая)", "")
        
        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить базу данных {db_name}?\n"
            f"Это действие невозможно отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Удаляем файл базы данных
            try:
                db_path = os.path.join(self.db_manager.db_folder, db_name)
                
                # Если это текущая база данных, закрываем соединение
                if self.db_manager.current_db_path == db_path:
                    self.db_manager.close()
                    
                # Удаляем файл
                os.remove(db_path)
                
                # Обновляем список
                self._load_databases()
                
                QMessageBox.information(
                    self,
                    "Успех",
                    f"База данных {db_name} успешно удалена!"
                )
            except Exception as e:
                logger.error(f"Ошибка при удалении базы данных: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось удалить базу данных: {str(e)}"
                )
    
    def _on_select_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Выбрать".
        """
        # Получаем выбранную БД
        current_item = self.db_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите базу данных!"
            )
            return
            
        db_name = current_item.text()
        # Удаляем " (текущая)" из имени, если есть
        if " (текущая)" in db_name:
            db_name = db_name.replace(" (текущая)", "")
            
        db_path = os.path.join(self.db_manager.db_folder, db_name)
        
        # Подключаемся к базе данных
        try:
            self.db_manager.connect(db_path)
            
            # Отправляем сигнал с путем к БД
            self.db_selected.emit(db_path)
            
            # Закрываем диалог
            self.accept()
        except Exception as e:
            logger.error(f"Ошибка при подключении к базе данных: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось подключиться к базе данных: {str(e)}"
            )
    
    def _on_db_double_clicked(self, item):
        """
        Обработчик двойного клика на элементе списка.
        """
        # Эмулируем нажатие на кнопку "Выбрать"
        self._on_select_button_clicked()