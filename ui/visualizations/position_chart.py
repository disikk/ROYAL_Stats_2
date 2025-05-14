#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
График распределения позиций в покерном трекере ROYAL_Stats.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ui.visualizations.base_chart import BaseChart

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.PositionChart')


class PositionChart(BaseChart):
    """
    График для отображения распределения позиций (мест) в турнирах.
    """
    
    def __init__(self, parent=None):
        """
        Инициализирует график распределения позиций.
        
        Args:
            parent: Родительский виджет (опционально).
        """
        super().__init__(parent, title="Распределение мест")
        
        # Данные для диаграммы
        self.places = list(range(1, 10))
        self.counts = [0] * 9
        
        # Цвета для мест
        self.place_colors = {
            1: '#28a745',  # Зеленый для 1-го места
            2: '#17a2b8',  # Сине-зеленый для 2-го места
            3: '#6f42c1',  # Фиолетовый для 3-го места
            4: '#fd7e14',  # Оранжевый для 4-го места
            5: '#fd7e14',  # Оранжевый для 5-го места
            6: '#fd7e14',  # Оранжевый для 6-го места
            7: '#dc3545',  # Красный для 7-го места
            8: '#dc3545',  # Красный для 8-го места
            9: '#dc3545'   # Красный для 9-го места
        }
        
        # Дополнительные настройки
        self.show_values = True
        self.show_percent = True
    
    def update_data(self, data: Dict[str, Any]) -> None:
        """
        Обновляет данные графика.
        
        Args:
            data: Словарь с данными для отображения на графике.
                 Ожидается ключ 'places_distribution' с вложенным словарем {место: количество}.
        """
        # Проверяем наличие ключа 'places_distribution'
        if 'places_distribution' in data:
            distribution = data['places_distribution']
            
            # Обновляем данные для диаграммы
            self.places = list(range(1, 10))
            self.counts = [distribution.get(p, 0) for p in self.places]
            
            # Перерисовываем график
            self.redraw()
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настраивает график по конфигурации.
        
        Args:
            config: Словарь с настройками графика.
        """
        super().configure(config)
        
        # Дополнительные настройки для PositionChart
        if 'x_label' in config:
            self.x_label = config['x_label']
        else:
            self.x_label = 'Место'
            
        if 'y_label' in config:
            self.y_label = config['y_label']
        else:
            self.y_label = 'Количество турниров'
            
        if 'show_values' in config:
            self.show_values = config['show_values']
            
        if 'show_percent' in config:
            self.show_percent = config['show_percent']
            
        if 'colors' in config:
            # Обновляем только указанные цвета
            for place, color in config['colors'].items():
                if 1 <= place <= 9:
                    self.place_colors[place] = color
    
    def redraw(self) -> None:
        """
        Перерисовывает график с текущими данными и настройками.
        """
        # Очищаем фигуру
        self.figure.clear()
        
        # Создаем подграфик
        ax = self.figure.add_subplot(111)
        
        # Устанавливаем стиль
        ax.set_facecolor(self.style['background_color'])
        
        # Рассчитываем проценты
        total_tournaments = sum(self.counts)
        percents = [count / total_tournaments * 100 if total_tournaments > 0 else 0 for count in self.counts]
        
        # Получаем цвета для каждого места
        colors = [self.place_colors[place] for place in self.places]
        
        # Создаем столбчатую диаграмму
        bars = ax.bar(
            self.places,
            self.counts,
            color=colors,
            edgecolor='#343a40',
            linewidth=0.5,
            alpha=0.8,
            width=0.7
        )
        
        # Добавляем значения на столбцы
        if self.show_values:
            for i, bar in enumerate(bars):
                height = bar.get_height()
                if height > 0:
                    # Текст с количеством и процентом
                    if self.show_percent:
                        text = f'{int(height)}\n({percents[i]:.1f}%)'
                    else:
                        text = f'{int(height)}'
                        
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.,
                        height + 0.05 * max(self.counts if any(self.counts) else [1]),
                        text,
                        ha='center',
                        va='bottom',
                        fontweight='bold',
                        fontsize=self.style['tick_label_size']
                    )
        
        # Настраиваем оси
        ax.set_xlabel(
            self.x_label,
            fontsize=self.style['axis_label_size'],
            fontweight=self.style['axis_label_weight'],
            labelpad=8
        )
        ax.set_ylabel(
            self.y_label,
            fontsize=self.style['axis_label_size'],
            fontweight=self.style['axis_label_weight'],
            labelpad=8
        )
        
        # Настраиваем диапазон осей
        ax.set_xlim(0.5, len(self.places) + 0.5)
        
        if max(self.counts) == 0:
            ax.set_ylim(0, 5)
        else:
            ax.set_ylim(0, max(self.counts) * 1.25)  # Немного больше места сверху
        
        # Настраиваем метки осей
        ax.set_xticks(self.places)
        ax.set_xticklabels(self.places, fontsize=self.style['tick_label_size'])
        ax.set_yticklabels([f"{int(y)}" for y in ax.get_yticks()], fontsize=self.style['tick_label_size'])
        
        # Скрываем верхнюю и правую границы
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(0.5)
        ax.spines['bottom'].set_linewidth(0.5)
        
        # Включаем сетку
        ax.grid(
            True,
            linestyle=self.style['grid_style'],
            alpha=self.style['grid_alpha'],
            axis='y'
        )
        
        # Обновляем заголовок с учетом общего количества турниров
        ax.set_title(
            f'{self.title} (всего: {total_tournaments})',
            fontsize=self.style['title_size'],
            fontweight=self.style['title_weight'],
            pad=10
        )
        
        # Тесное расположение элементов
        self.figure.tight_layout(pad=2.0)
        
        # Отрисовываем график
        self.canvas.draw()