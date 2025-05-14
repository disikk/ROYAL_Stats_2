#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Диалог для управления сессиями в покерном трекере ROYAL_Stats.
"""

import logging
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QLineEdit, QMessageBox, QInputDialog, QListWidgetItem,
    QFormLayout, QWidget, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.SessionDialog')


class SessionDialog(QDialog):
    """
    Диалог для создания и управления сессиями.
    """
    
    # Сигналы
    session_created = pyqtSignal(str)   # Сигнал создания сессии (передает имя)
    session_selected = pyqtSignal(str)  # Сигнал выбора сессии (передает ID)
    
    def __init__(self, session_repository, parent=None):
        """
        Инициализирует диалог управления сессиями.
        
        Args:
            session_repository: Репозиторий для работы с сессиями.
            parent: Родительский виджет (опционально).
        """
        super().__init__(parent)
        
        self.session_repository = session_repository
        
        self.setWindowTitle("Управление сессиями")
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
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ced4da;
                border-radius: 4px;
                margin-top: 1ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        
        self._init_ui()
        self._load_sessions()
    
    def _init_ui(self):
        """
        Инициализирует элементы интерфейса.
        """
        # Основной layout
        main_layout = QVBoxLayout(self)
        
        # Заголовок
        title_label = QLabel("Управление сессиями")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # Разделяем на две части: слева список сессий, справа форма для создания
        content_layout = QHBoxLayout()
        
        # Левая часть - список сессий
        sessions_group = QGroupBox("Доступные сессии")
        sessions_layout = QVBoxLayout()
        
        self.sessions_list = QListWidget()
        self.sessions_list.setAlternatingRowColors(True)
        self.sessions_list.itemDoubleClicked.connect(self._on_session_double_clicked)
        sessions_layout.addWidget(self.sessions_list)
        
        # Кнопки управления сессиями
        buttons_layout = QHBoxLayout()
        
        self.rename_button = QPushButton("Переименовать")
        self.rename_button.clicked.connect(self._on_rename_button_clicked)
        buttons_layout.addWidget(self.rename_button)
        
        self.delete_button = QPushButton("Удалить")
        self.delete_button.clicked.connect(self._on_delete_button_clicked)
        buttons_layout.addWidget(self.delete_button)
        
        self.select_button = QPushButton("Выбрать")
        self.select_button.clicked.connect(self._on_select_button_clicked)
        buttons_layout.addWidget(self.select_button)
        
        sessions_layout.addLayout(buttons_layout)
        sessions_group.setLayout(sessions_layout)
        
        # Правая часть - форма для создания сессии
        create_group = QGroupBox("Создать новую сессию")
        create_layout = QVBoxLayout()
        
        # Форма для ввода имени сессии
        form_layout = QFormLayout()
        
        self.session_name_edit = QLineEdit()
        form_layout.addRow("Название сессии:", self.session_name_edit)
        
        create_layout.addLayout(form_layout)
        
        # Кнопка создания
        self.create_button = QPushButton("Создать")
        self.create_button.clicked.connect(self._on_create_button_clicked)
        create_layout.addWidget(self.create_button)
        
        # Добавляем растягивающийся пробел
        create_layout.addStretch()
        
        create_group.setLayout(create_layout)
        
        # Добавляем обе части в layout
        content_layout.addWidget(sessions_group, 2)
        content_layout.addWidget(create_group, 1)
        
        main_layout.addLayout(content_layout)
        
        # Добавляем информационную метку в нижнюю часть
        info_label = QLabel(
            "Двойной клик на сессии - выбор. "
            "Сессии группируют загруженные файлы и статистику."
        )
        info_label.setStyleSheet("color: #6c757d; font-style: italic;")
        main_layout.addWidget(info_label)
    
    def _load_sessions(self):
        """
        Загружает список сессий из репозитория.
        """
        self.sessions_list.clear()
        
        try:
            sessions = self.session_repository.get_sessions()
            
            for session in sessions:
                session_name = session['session_name']
                session_id = session['session_id']
                tournaments_count = session.get('tournaments_count', 0)
                
                # Создаем элемент списка с информацией о сессии
                item_text = f"{session_name} ({tournaments_count} турниров)"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, session_id)
                
                self.sessions_list.addItem(item)
        except Exception as e:
            logger.error(f"Ошибка при загрузке списка сессий: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список сессий: {str(e)}")
    
    def _on_create_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Создать".
        """
        session_name = self.session_name_edit.text().strip()
        
        if not session_name:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Введите название для новой сессии!"
            )
            return
            
        try:
            # Создаем сессию в репозитории
            session_id = self.session_repository.create_session(session_name)
            
            # Обновляем список сессий
            self._load_sessions()
            
            # Очищаем поле ввода
            self.session_name_edit.clear()
            
            # Отправляем сигнал о создании сессии
            self.session_created.emit(session_id)
            
            # Выбираем созданную сессию в списке
            for i in range(self.sessions_list.count()):
                item = self.sessions_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == session_id:
                    self.sessions_list.setCurrentItem(item)
                    break
                    
            QMessageBox.information(
                self,
                "Успех",
                f"Сессия '{session_name}' успешно создана!"
            )
        except Exception as e:
            logger.error(f"Ошибка при создании сессии: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось создать сессию: {str(e)}"
            )
    
    def _on_rename_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Переименовать".
        """
        # Получаем выбранную сессию
        current_item = self.sessions_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите сессию для переименования!"
            )
            return
            
        session_id = current_item.data(Qt.ItemDataRole.UserRole)
        session_text = current_item.text()
        
        # Извлекаем имя сессии (без информации о количестве турниров)
        if " (" in session_text:
            current_name = session_text.split(" (")[0]
        else:
            current_name = session_text
            
        # Запрашиваем новое имя
        new_name, ok = QInputDialog.getText(
            self, 
            "Переименование сессии", 
            "Введите новое название для сессии:",
            text=current_name
        )
        
        if ok and new_name:
            try:
                # Обновляем имя сессии в репозитории
                self.session_repository.rename_session(session_id, new_name)
                
                # Обновляем список сессий
                self._load_sessions()
                
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Сессия успешно переименована в '{new_name}'!"
                )
            except Exception as e:
                logger.error(f"Ошибка при переименовании сессии: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось переименовать сессию: {str(e)}"
                )
    
    def _on_delete_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Удалить".
        """
        # Получаем выбранную сессию
        current_item = self.sessions_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите сессию для удаления!"
            )
            return
            
        session_id = current_item.data(Qt.ItemDataRole.UserRole)
        session_text = current_item.text()
        
        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить сессию '{session_text}'?\n"
            f"Это действие невозможно отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Удаляем сессию в репозитории
                self.session_repository.delete_session(session_id)
                
                # Обновляем список сессий
                self._load_sessions()
                
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Сессия успешно удалена!"
                )
            except Exception as e:
                logger.error(f"Ошибка при удалении сессии: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось удалить сессию: {str(e)}"
                )
    
    def _on_select_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Выбрать".
        """
        # Получаем выбранную сессию
        current_item = self.sessions_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите сессию!"
            )
            return
            
        session_id = current_item.data(Qt.ItemDataRole.UserRole)
        
        # Отправляем сигнал о выборе сессии
        self.session_selected.emit(session_id)
        
        # Закрываем диалог
        self.accept()
    
    def _on_session_double_clicked(self, item):
        """
        Обработчик двойного клика на элементе списка.
        """
        # Эмулируем нажатие на кнопку "Выбрать"
        self._on_select_button_clicked()