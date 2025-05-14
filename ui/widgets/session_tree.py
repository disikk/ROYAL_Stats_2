#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Дерево сессий для отображения в ROYAL_Stats.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Callable

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, 
    QWidget, QVBoxLayout, QLabel, 
    QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QIcon, QFont

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.SessionTree')


class SessionTree(QTreeWidget):
    """
    Дерево для отображения и управления сессиями.
    """
    
    # Сигналы
    session_selected = pyqtSignal(str)  # Сигнал выбора сессии (передает ID)
    session_created = pyqtSignal(str)   # Сигнал создания сессии (передает ID)
    session_renamed = pyqtSignal(str)   # Сигнал переименования сессии (передает ID)
    session_deleted = pyqtSignal(str)   # Сигнал удаления сессии (передает ID)
    
    def __init__(self, parent=None):
        """
        Инициализирует дерево сессий.
        
        Args:
            parent: Родительский виджет (опционально).
        """
        super().__init__(parent)
        
        # Настройка внешнего вида
        self.setHeaderLabels(["Сессии"])
        self.setMinimumWidth(200)
        
        # Установка стиля для дерева
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
            }
            QTreeWidget::item {
                padding: 5px;
                border-bottom: 1px solid #e9ecef;
            }
            QTreeWidget::item:selected {
                background-color: #e9ecef;
                color: #212529;
            }
        """)
        
        # Настройка контекстного меню
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Подключение сигнала выбора элемента
        self.itemClicked.connect(self.on_item_clicked)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # Добавляем элемент "Все сессии"
        self.all_sessions_item = QTreeWidgetItem(["Все сессии"])
        self.all_sessions_item.setData(0, Qt.ItemDataRole.UserRole, "all")
        font = self.all_sessions_item.font(0)
        font.setBold(True)
        self.all_sessions_item.setFont(0, font)
        self.addTopLevelItem(self.all_sessions_item)
        
        # Текущий выбранный ID сессии
        self.current_session_id = None
        
        # Развернуть все элементы
        self.expandAll()
    
    def update_sessions(self, sessions: List[Dict[str, Any]]) -> None:
        """
        Обновляет список сессий.
        
        Args:
            sessions: Список словарей с информацией о сессиях.
                Каждый словарь должен содержать ключи:
                - 'session_id': Идентификатор сессии
                - 'session_name': Название сессии
                - 'tournaments_count': Количество турниров в сессии (опционально)
        """
        # Сохраняем текущий ID сессии
        old_session_id = self.current_session_id
        
        # Очищаем текущие сессии, кроме "Все сессии"
        for i in range(self.topLevelItemCount() - 1, 0, -1):
            self.takeTopLevelItem(i)
        
        # Добавляем новые сессии
        for session in sessions:
            session_name = session['session_name']
            session_id = session['session_id']
            
            # Формируем текст элемента с учетом количества турниров
            if 'tournaments_count' in session and session['tournaments_count'] > 0:
                item_text = f"{session_name} ({session['tournaments_count']} турниров)"
            else:
                item_text = session_name
                
            # Создаем элемент
            session_item = QTreeWidgetItem([item_text])
            session_item.setData(0, Qt.ItemDataRole.UserRole, session_id)
            
            # Добавляем в дерево
            self.addTopLevelItem(session_item)
        
        # Восстанавливаем выбор
        if old_session_id:
            self.set_current_session(old_session_id)
        
        # Разворачиваем дерево
        self.expandAll()
    
    def set_current_session(self, session_id: str) -> None:
        """
        Устанавливает текущую сессию.
        
        Args:
            session_id: Идентификатор сессии.
        """
        self.current_session_id = session_id
        
        # Ищем соответствующий элемент
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == session_id:
                self.setCurrentItem(item)
                break
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """
        Обработчик клика на элементе дерева.
        
        Args:
            item: Выбранный элемент.
            column: Номер колонки (не используется).
        """
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.current_session_id = session_id
        self.session_selected.emit(session_id)
    
    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """
        Обработчик двойного клика на элементе дерева.
        
        Args:
            item: Выбранный элемент.
            column: Номер колонки (не используется).
        """
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Двойной клик на "Все сессии" не делает ничего
        if session_id == "all":
            return
            
        # Для остальных элементов вызываем диалог переименования
        self.rename_session(session_id)
    
    def show_context_menu(self, position: QPoint) -> None:
        """
        Показывает контекстное меню.
        
        Args:
            position: Позиция клика.
        """
        # Получаем элемент под курсором
        item = self.itemAt(position)
        if not item:
            return
            
        # Получаем ID сессии
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Создаем меню
        menu = QMenu(self)
        
        # Добавляем пункты в зависимости от типа элемента
        if session_id == "all":
            # Для "Все сессии" только пункт "Создать сессию"
            create_action = menu.addAction("Создать сессию")
            
            # Выполнение действия
            action = menu.exec(self.mapToGlobal(position))
            if action == create_action:
                self.create_session()
        else:
            # Для обычных сессий
            rename_action = menu.addAction("Переименовать")
            delete_action = menu.addAction("Удалить")
            
            # Выполнение действия
            action = menu.exec(self.mapToGlobal(position))
            if action == rename_action:
                self.rename_session(session_id)
            elif action == delete_action:
                self.delete_session(session_id)
    
    def create_session(self) -> None:
        """
        Создает новую сессию.
        """
        # Запрашиваем имя сессии
        name, ok = QInputDialog.getText(
            self, "Новая сессия", "Введите название для новой сессии:"
        )
        
        if ok and name:
            # Генерируем сигнал создания сессии
            self.session_created.emit(name)
    
    def rename_session(self, session_id: str) -> None:
        """
        Переименовывает сессию.
        
        Args:
            session_id: Идентификатор сессии.
        """
        # Находим соответствующий элемент
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == session_id:
                # Получаем текущее имя
                current_name = item.text(0)
                
                # Удаляем информацию о количестве турниров из имени
                if " (" in current_name:
                    current_name = current_name.split(" (")[0]
                
                # Запрашиваем новое имя
                new_name, ok = QInputDialog.getText(
                    self, "Переименование сессии", 
                    "Введите новое название для сессии:",
                    text=current_name
                )
                
                if ok and new_name:
                    # Генерируем сигнал переименования сессии
                    self.session_renamed.emit(f"{session_id}:{new_name}")
                
                break
    
    def delete_session(self, session_id: str) -> None:
        """
        Удаляет сессию.
        
        Args:
            session_id: Идентификатор сессии.
        """
        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            "Вы уверены, что хотите удалить эту сессию?\n"
            "Это действие невозможно отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Генерируем сигнал удаления сессии
            self.session_deleted.emit(session_id)