#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Адаптер класса SessionTree для работы с главным окном приложения.
"""

import logging
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.SessionTreeAdapter')

class SessionTreeAdapter:
    """
    Класс-адаптер для расширения функциональности SessionTree.
    """
    
    @classmethod
    def extend_session_tree(cls, session_tree_class):
        """
        Расширяет класс SessionTree необходимыми методами.
        
        Args:
            session_tree_class: Класс SessionTree для расширения
        """
        def select_all_sessions(self):
            """Выбирает опцию 'Все сессии' в дереве сессий"""
            try:
                # Предположительная реализация - пытаемся найти первый элемент верхнего уровня
                # и установить его как текущий выбранный
                item_count = self.topLevelItemCount()
                if item_count > 0:
                    # Выбираем первый элемент (предположительно 'Все сессии')
                    self.setCurrentItem(self.topLevelItem(0))
                    # Эмитируем сигнал о смене элемента, если такой сигнал есть
                    if hasattr(self, 'itemClicked'):
                        self.itemClicked.emit(self.topLevelItem(0), 0)
                    logger.debug("Выбран элемент 'Все сессии' в дереве сессий")
                else:
                    logger.warning("Дерево сессий пусто, невозможно выбрать 'Все сессии'")
            except Exception as e:
                logger.error(f"Ошибка при выборе 'Все сессии' в дереве сессий: {e}", exc_info=True)
        
        # Добавляем метод в класс
        session_tree_class.select_all_sessions = select_all_sessions
        
        logger.info("Класс SessionTree успешно расширен методом select_all_sessions")
        
    @classmethod
    def create_empty_tree_widget(cls) -> QWidget:
        """
        Создает пустой виджет дерева сессий для замены в случае ошибки.
        
        Returns:
            Виджет-заглушка дерева сессий
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel("Сессии не загружены")
        layout.addWidget(label)
        return widget