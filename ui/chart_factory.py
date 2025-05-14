#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Вспомогательный класс для создания графиков из модулей статистики.
"""

import logging
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.ChartFactory')

class ChartFactory:
    """Класс для создания графиков на основе конфигурации модулей статистики"""
    
    @staticmethod
    def create_chart_widget(module_name: str, chart_config: Dict[str, Any], data: Dict[str, Any]) -> QWidget:
        """
        Создает виджет с графиком на основе конфигурации модуля.
        
        Args:
            module_name: Имя модуля статистики
            chart_config: Конфигурация графика
            data: Данные для отображения
            
        Returns:
            Виджет с графиком
        """
        try:
            # Базовый контейнер для графика
            chart_widget = QWidget()
            layout = QVBoxLayout(chart_widget)
            
            # Создаем заголовок
            title = chart_config.get('title', f'График {module_name}')
            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(title_label)
            
            # Временный заглушка с типом графика
            chart_type = chart_config.get('type', 'unknown')
            chart_placeholder = QLabel(f"[График типа: {chart_type}]")
            chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            chart_placeholder.setStyleSheet("background-color: #f0f0f0; border: 1px solid #cccccc; padding: 20px;")
            layout.addWidget(chart_placeholder)
            
            return chart_widget
        except Exception as e:
            logger.error(f"Ошибка при создании графика для модуля {module_name}: {e}", exc_info=True)
            # Возвращаем пустой виджет с сообщением об ошибке
            error_widget = QWidget()
            error_layout = QVBoxLayout(error_widget)
            error_label = QLabel(f"Ошибка при создании графика: {str(e)}")
            error_label.setStyleSheet("color: red;")
            error_layout.addWidget(error_label)
            return error_widget
    
    @classmethod
    def extend_stats_module(cls, module_class):
        """
        Расширяет класс модуля статистики методом create_chart_widget
        
        Args:
            module_class: Класс модуля статистики
        """
        def create_chart_widget(self, data):
            """Создает виджет с графиком на основе конфигурации модуля"""
            chart_config = self.get_chart_config()
            return cls.create_chart_widget(self.name, chart_config, data)
        
        # Добавляем метод в класс модуля
        module_class.create_chart_widget = create_chart_widget
        
    @classmethod
    def extend_all_stats_modules(cls):
        """Расширяет все существующие классы модулей статистики"""
        try:
            from stats.base_stat import BaseStat
            import stats
            
            # Получаем все классы модулей
            if hasattr(stats, 'AVAILABLE_STATS'):
                for module_class in stats.AVAILABLE_STATS:
                    cls.extend_stats_module(module_class)
            
            logger.info("Модули статистики успешно расширены методом create_chart_widget")
        except Exception as e:
            logger.error(f"Ошибка при расширении модулей статистики: {e}", exc_info=True)