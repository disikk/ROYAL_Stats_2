#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Базовый класс для графиков в покерном трекере ROYAL_Stats.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QFrame
from PyQt6.QtCore import Qt

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.BaseChart')


class BaseChart(QWidget):
    """
    Базовый класс для всех графиков в ROYAL_Stats.
    
    Предоставляет общий интерфейс и функциональность для всех типов графиков.
    """
    
    def __init__(self, parent=None, title: str = "", figsize: Tuple[float, float] = (7, 3.5)):
        """
        Инициализирует базовый график.
        
        Args:
            parent: Родительский виджет (опционально).
            title: Заголовок графика (опционально).
            figsize: Размер графика в дюймах (ширина, высота) (опционально).
        """
        super().__init__(parent)
        
        # Создаем layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаем фрейм для графика
        self.chart_frame = QFrame()
        self.chart_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.chart_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.chart_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }
        """)
        self.chart_layout = QVBoxLayout(self.chart_frame)
        self.chart_layout.setContentsMargins(5, 5, 5, 5)
        
        # Создаем фигуру matplotlib
        self.figure = Figure(figsize=figsize, dpi=90)
        self.figure.patch.set_facecolor('white')
        self.canvas = FigureCanvas(self.figure)
        self.chart_layout.addWidget(self.canvas)
        
        # Добавляем фрейм с графиком в основной layout
        self.layout.addWidget(self.chart_frame)
        
        # Задаем заголовок графика
        self.title = title
        
        # Стиль графика
        self.style = {
            'title_size': 12,
            'title_weight': 'bold',
            'axis_label_size': 10,
            'axis_label_weight': 'bold',
            'tick_label_size': 9,
            'grid_alpha': 0.3,
            'grid_style': '--',
            'background_color': '#f8f9fa',
            'text_color': '#343a40',
            'colormap': 'Blues'  # Цветовая схема для графиков
        }
        
        # Данные для графика
        self.data = {}
    
    def update_data(self, data: Dict[str, Any]) -> None:
        """
        Обновляет данные графика.
        
        Args:
            data: Словарь с данными для отображения на графике.
        """
        self.data = data
        self.redraw()
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настраивает график по конфигурации.
        
        Args:
            config: Словарь с настройками графика.
        """
        # Обновляем заголовок
        if 'title' in config:
            self.title = config['title']
            
        # Обновляем стиль
        for key in ['title_size', 'title_weight', 'axis_label_size', 'axis_label_weight',
                     'tick_label_size', 'grid_alpha', 'grid_style', 'background_color',
                     'text_color', 'colormap']:
            if key in config:
                self.style[key] = config[key]
    
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
        
        # Применяем базовые настройки стиля
        ax.set_title(
            self.title, 
            fontsize=self.style['title_size'], 
            fontweight=self.style['title_weight'],
            color=self.style['text_color'],
            pad=10
        )
        
        # Скрываем верхнюю и правую границы
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Настраиваем левую и нижнюю границы
        ax.spines['left'].set_linewidth(0.5)
        ax.spines['bottom'].set_linewidth(0.5)
        
        # Включаем сетку
        ax.grid(
            True, 
            linestyle=self.style['grid_style'], 
            alpha=self.style['grid_alpha'], 
            axis='y'
        )
        
        # Добавляем немного места сверху графика для текста
        ax.set_ylim(0, 5)  # Это будет переопределено в дочерних классах
        
        # Тесное расположение элементов
        self.figure.tight_layout(pad=2.0)
        
        # Отрисовываем график
        self.canvas.draw()
    
    def save_to_file(self, file_path: str) -> bool:
        """
        Сохраняет график в файл.
        
        Args:
            file_path: Путь для сохранения графика.
            
        Returns:
            True, если сохранение успешно, иначе False.
        """
        try:
            self.figure.savefig(file_path)
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении графика в файл {file_path}: {e}", exc_info=True)
            return False