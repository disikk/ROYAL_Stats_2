#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сетка карточек для отображения статистических показателей в ROYAL_Stats.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Callable

from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, 
    QGroupBox, QLabel, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QSize

from ui.widgets.stats_card import StatsCard

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.StatsGrid')


class StatsGrid(QWidget):
    """
    Сетка карточек с основными статистическими показателями.
    """
    
    def __init__(self, parent=None, columns: int = 3):
        """
        Инициализирует сетку карточек.
        
        Args:
            parent: Родительский виджет (опционально).
            columns: Количество колонок в сетке (опционально).
        """
        super().__init__(parent)
        
        # Словарь карточек {id_карточки: экземпляр_StatsCard}
        self.cards = {}
        
        # Количество колонок
        self.columns = columns
        
        # Инициализация UI
        self._init_ui()
    
    def _init_ui(self):
        """
        Инициализирует элементы интерфейса.
        """
        # Создаем основной layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Область прокрутки для карточек
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Виджет-контейнер для карточек
        container = QWidget()
        self.grid_layout = QGridLayout(container)
        self.grid_layout.setHorizontalSpacing(10)
        self.grid_layout.setVerticalSpacing(10)
        
        # Привязываем контейнер к области прокрутки
        scroll_area.setWidget(container)
        
        # Добавляем область прокрутки в основной layout
        self.main_layout.addWidget(scroll_area)
    
    def create_cards(self, cards_config: List[Dict[str, Any]]) -> None:
        """
        Создает карточки по конфигурации.
        
        Args:
            cards_config: Список словарей с конфигурацией карточек.
                Каждый словарь должен содержать ключи:
                - 'id': Идентификатор карточки
                - 'title': Заголовок карточки
                - 'format': Формат отображения значения (например '{:.2f}')
                - 'color': Цвет значения (в формате CSS/HTML, например '#1e88e5')
                - 'width': (опционально) Ширина карточки в колонках (1, 2, 3, ...)
        """
        # Очищаем текущие карточки
        self.clear()
        
        # Создаем новые карточки
        row, col = 0, 0
        
        for card_config in cards_config:
            # Проверяем наличие обязательных ключей
            if 'id' not in card_config or 'title' not in card_config:
                logger.warning(f"Пропуск карточки из-за отсутствия обязательных полей: {card_config}")
                continue
                
            # Получаем параметры карточки
            card_id = card_config['id']
            title = card_config['title']
            color = card_config.get('color', '#2c3e50')
            value_format = card_config.get('format', '{}')
            width = card_config.get('width', 1)
            
            # Создаем карточку
            card = StatsCard(title=title, value=0, value_color=color, value_format=value_format)
            
            # Добавляем карточку в словарь
            self.cards[card_id] = card
            
            # Добавляем карточку в сетку
            self.grid_layout.addWidget(card, row, col, 1, width)
            
            # Переходим к следующей позиции
            col += width
            if col >= self.columns:
                col = 0
                row += 1
    
    def update_values(self, data: Dict[str, Any]) -> None:
        """
        Обновляет значения карточек.
        
        Args:
            data: Словарь с данными {id_карточки: значение}.
        """
        for card_id, value in data.items():
            if card_id in self.cards:
                self.cards[card_id].set_value(value)
    
    def update_card(self, card_id: str, value: Any) -> None:
        """
        Обновляет значение отдельной карточки.
        
        Args:
            card_id: Идентификатор карточки.
            value: Новое значение.
        """
        if card_id in self.cards:
            self.cards[card_id].set_value(value)
    
    def get_card(self, card_id: str) -> Optional[StatsCard]:
        """
        Возвращает карточку по идентификатору.
        
        Args:
            card_id: Идентификатор карточки.
            
        Returns:
            Экземпляр StatsCard или None, если карточка не найдена.
        """
        return self.cards.get(card_id)
    
    def clear(self) -> None:
        """
        Очищает все карточки.
        """
        # Удаляем все виджеты из сетки
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        # Очищаем словарь карточек
        self.cards.clear()