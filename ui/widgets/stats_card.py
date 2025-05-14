#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Карточка для отображения статистических показателей в ROYAL_Stats.
"""

import logging
from typing import Any, Optional, Union, Callable

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.StatsCard')


class StatsCard(QFrame):
    """
    Карточка для отображения одного статистического показателя.
    """
    
    def __init__(
        self, 
        title: str, 
        value: Any = "", 
        parent=None, 
        value_color: str = "#2c3e50",
        value_format: str = "{}"
    ):
        """
        Инициализирует карточку статистики.
        
        Args:
            title: Заголовок карточки.
            value: Значение для отображения (опционально).
            parent: Родительский виджет (опционально).
            value_color: Цвет значения в формате HEX (опционально).
            value_format: Формат для отображения значения (опционально).
        """
        super().__init__(parent)
        
        # Настраиваем стиль карточки
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setMinimumSize(100, 80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Задаем цвет фона с градиентом
        self.setStyleSheet(f"""
            QFrame {{
                background-color: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f9fa, stop: 1 #e9ecef
                );
                border-radius: 6px;
                border: 1px solid #dee2e6;
            }}
            QLabel {{
                background-color: transparent;
            }}
        """)
        
        # Создаем layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 10, 7, 10)
        
        # Заголовок
        self.title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: #343a40; font-size: 8pt;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Значение
        self.value_label = QLabel(value_format.format(value))
        value_font = QFont()
        value_font.setPointSize(12)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        self.value_label.setStyleSheet(f"color: {value_color}; font-size: 12pt;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Добавляем виджеты на layout
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        
        # Сохраняем формат для отображения значения
        self.value_format = value_format
    
    def set_value(self, value: Any) -> None:
        """
        Обновляет значение карточки.
        
        Args:
            value: Новое значение для отображения.
        """
        try:
            formatted_value = self.value_format.format(value)
            self.value_label.setText(formatted_value)
        except Exception as e:
            logger.error(f"Ошибка при форматировании значения '{value}': {e}", exc_info=True)
            self.value_label.setText(str(value))
    
    def set_title(self, title: str) -> None:
        """
        Обновляет заголовок карточки.
        
        Args:
            title: Новый заголовок.
        """
        self.title_label.setText(title)
    
    def set_value_color(self, color: str) -> None:
        """
        Обновляет цвет значения.
        
        Args:
            color: Цвет в формате HEX.
        """
        self.value_label.setStyleSheet(f"color: {color}; font-size: 12pt;")
    
    def set_format(self, value_format: str) -> None:
        """
        Обновляет формат отображения значения.
        
        Args:
            value_format: Новый формат (например, "{:.2f}").
        """
        self.value_format = value_format
        # Обновляем текущее значение с новым форматом
        current_value = self.value_label.text()
        try:
            # Пытаемся извлечь исходное значение (без форматирования)
            # Это не всегда возможно, поэтому используем текущий текст в случае ошибки
            original_value = float(current_value.replace('$', '').replace('%', '').replace(',', ''))
            self.set_value(original_value)
        except ValueError:
            # Если не удалось преобразовать, оставляем как есть
            pass