#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль визуализации статистики крупных нокаутов в покерных турнирах.
Предоставляет класс LargeKnockoutChart для отображения распределения крупных нокаутов.
"""

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy

from .base_chart import BaseChart

class LargeKnockoutChart(BaseChart):
    """
    Класс для визуализации статистики крупных нокаутов в турнирах.
    """
    
    def __init__(self, parent=None):
        """
        Инициализирует виджет визуализации крупных нокаутов.
        
        Args:
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.title = "Распределение крупных нокаутов"
        self.title_label.setText(self.title)
        
        # Создаем фигуру и холст matplotlib
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        
        # Удаляем placeholder и добавляем холст
        self.layout.removeWidget(self.chart_placeholder)
        self.chart_placeholder.setParent(None)
        self.layout.addWidget(self.canvas)
        
        # Цветовая схема по умолчанию
        self.colors = {
            'x2': '#20c997',
            'x10': '#0d6efd',
            'x100': '#fd7e14',
            'x1000': '#dc3545',
            'x10000': '#6f42c1'
        }
        
        # Метки для типов нокаутов
        self.labels = {
            'x2': 'x2',
            'x10': 'x10',
            'x100': 'x100',
            'x1000': 'x1000',
            'x10000': 'x10000'
        }
        
        # Метки осей по умолчанию
        self.x_label = "Тип нокаута"
        self.y_label = "Количество"
        
        # Тип графика по умолчанию
        self.chart_type = 'bar'
        
        # Настройки
        self.settings = {
            'show_x2_knockouts': True,
            'include_x2_in_totals': True
        }
        
        # Создаем пустую фигуру по умолчанию
        self._setup_figure()
    
    def _setup_figure(self):
        """
        Настраивает фигуру matplotlib.
        """
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.grid(True, linestyle='--', alpha=0.7)
        
        # Обновляем холст
        self.canvas.draw()
    
    def _update_chart(self):
        """
        Обновляет график крупных нокаутов на основе текущих данных.
        """
        if not self.data or 'large_knockouts' not in self.data:
            # Если данных нет, показываем пустой график
            self._setup_figure()
            return
            
        # Получаем данные для графика
        large_knockouts = self.data.get('large_knockouts', {})
        if not large_knockouts or sum(large_knockouts.values()) == 0:
            self._setup_figure()
            self.ax.text(0.5, 0.5, 'Нет данных о крупных нокаутах', 
                        ha='center', va='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return
            
        # Очищаем текущую фигуру
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        
        # Подготавливаем данные для диаграммы
        chart_type = self.config.get('type', self.chart_type)
        
        if chart_type == 'bar':
            self._draw_bar_chart(large_knockouts)
        elif chart_type == 'pie':
            self._draw_pie_chart(large_knockouts)
        else:
            # По умолчанию столбчатая диаграмма
            self._draw_bar_chart(large_knockouts)
        
        # Применяем тесную компоновку
        self.figure.tight_layout()
        
        # Обновляем холст
        self.canvas.draw()
    
    def _draw_bar_chart(self, large_knockouts: Dict[str, int]):
        """
        Рисует столбчатую диаграмму распределения крупных нокаутов.
        
        Args:
            large_knockouts: Словарь с данными о крупных нокаутах
        """
        # Фильтруем данные в соответствии с настройками
        filtered_knockouts = {}
        for key, value in large_knockouts.items():
            if key == 'x2' and not self.settings.get('show_x2_knockouts', True):
                continue
            if value > 0:  # Показываем только ненулевые значения
                filtered_knockouts[key] = value
        
        if not filtered_knockouts:
            self.ax.text(0.5, 0.5, 'Нет данных о крупных нокаутах', 
                        ha='center', va='center', transform=self.ax.transAxes)
            return
            
        # Подготавливаем данные для отображения
        categories = list(filtered_knockouts.keys())
        values = [filtered_knockouts[key] for key in categories]
        
        # Создаем цвета для каждого столбца
        bar_colors = [self.colors.get(cat, '#6c757d') for cat in categories]
        
        # Названия для каждой категории
        tick_labels = [self.labels.get(cat, cat) for cat in categories]
        
        # Строим столбчатую диаграмму
        bars = self.ax.bar(categories, values, color=bar_colors)
        
        # Добавляем числовые значения над столбцами
        for bar in bars:
            height = bar.get_height()
            self.ax.text(
                bar.get_x() + bar.get_width()/2.,
                height + 0.1,
                str(int(height)),
                ha='center', va='bottom',
                fontsize=9
            )
        
        # Настраиваем оси
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.set_xticks(range(len(categories)))
        self.ax.set_xticklabels(tick_labels)
        
        # Добавляем сетку
        self.ax.grid(True, linestyle='--', alpha=0.7, axis='y')
        
        # Устанавливаем заголовок если нужно
        if self.config.get('show_title', True):
            title = self.config.get('chart_title', self.title)
            self.ax.set_title(title)
            
        # Добавляем аннотацию с общим количеством крупных нокаутов
        total_knockouts = self.data.get('total_large_knockouts', 0)
        large_ko_per_tournament = self.data.get('large_ko_per_tournament', 0)
        
        self.ax.annotate(
            f'Всего крупных нокаутов: {total_knockouts}\nКрупных КО/турнир: {large_ko_per_tournament:.2f}',
            xy=(0.95, 0.95),
            xycoords='axes fraction',
            ha='right',
            va='top',
            bbox=dict(boxstyle="round,pad=0.3", fc='#f8f9fa', ec='#dee2e6', alpha=0.8)
        )
    
    def _draw_pie_chart(self, large_knockouts: Dict[str, int]):
        """
        Рисует круговую диаграмму распределения крупных нокаутов.
        
        Args:
            large_knockouts: Словарь с данными о крупных нокаутах
        """
        # Фильтруем данные в соответствии с настройками
        filtered_knockouts = {}
        for key, value in large_knockouts.items():
            if key == 'x2' and not self.settings.get('show_x2_knockouts', True):
                continue
            if value > 0:  # Показываем только ненулевые значения
                filtered_knockouts[key] = value
        
        if not filtered_knockouts:
            self.ax.text(0.5, 0.5, 'Нет данных о крупных нокаутах', 
                        ha='center', va='center', transform=self.ax.transAxes)
            return
            
        # Подготавливаем данные для круговой диаграммы
        labels = [f"{self.labels.get(key, key)} ({value})" for key, value in filtered_knockouts.items()]
        values = list(filtered_knockouts.values())
        colors = [self.colors.get(key, '#6c757d') for key in filtered_knockouts.keys()]
        
        # Рисуем круговую диаграмму
        wedges, texts, autotexts = self.ax.pie(
            values, 
            labels=labels, 
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            shadow=False,
            textprops={'fontsize': 9}
        )
        
        # Устанавливаем равные пропорции для круга
        self.ax.axis('equal')
        
        # Устанавливаем заголовок если нужно
        if self.config.get('show_title', True):
            title = self.config.get('chart_title', self.title)
            self.ax.set_title(title)
        
        # Добавляем аннотацию с общим количеством крупных нокаутов
        total_knockouts = self.data.get('total_large_knockouts', 0)
        
        self.ax.annotate(
            f'Всего крупных нокаутов: {total_knockouts}',
            xy=(0.95, 0.05),
            xycoords='axes fraction',
            ha='right',
            va='bottom',
            bbox=dict(boxstyle="round,pad=0.3", fc='#f8f9fa', ec='#dee2e6', alpha=0.8)
        )
    
    def set_config(self, config: Dict[str, Any]):
        """
        Устанавливает конфигурацию графика.
        
        Args:
            config: Словарь с настройками графика
        """
        super().set_config(config)
        
        # Обновляем специфичные настройки
        if 'type' in config:
            self.chart_type = config['type']
        if 'x_label' in config:
            self.x_label = config['x_label']
        if 'y_label' in config:
            self.y_label = config['y_label']
        if 'colors' in config:
            self.colors.update(config['colors'])
        if 'labels' in config:
            self.labels.update(config['labels'])
        
        # Обновляем график с новыми настройками
        self._update_chart()
    
    def set_settings(self, settings: Dict[str, Any]):
        """
        Устанавливает настройки отображения крупных нокаутов.
        
        Args:
            settings: Словарь с настройками отображения
        """
        self.settings.update(settings)
        self._update_chart()