#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль визуализации прибыли и ROI в покерных турнирах.
Предоставляет класс ProfitChart для отображения статистики прибыли и ROI.
"""

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from datetime import datetime

from .base_chart import BaseChart

class ProfitChart(BaseChart):
    """
    Класс для визуализации прибыли и ROI в турнирах.
    """
    
    def __init__(self, parent=None):
        """
        Инициализирует виджет визуализации прибыли.
        
        Args:
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.title = "Прибыль по месяцам"
        self.title_label.setText(self.title)
        
        # Создаем фигуру и холст matplotlib
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        
        # Удаляем placeholder и добавляем холст
        self.layout.removeWidget(self.chart_placeholder)
        self.chart_placeholder.setParent(None)
        self.layout.addWidget(self.canvas)
        
        # Настройки графиков
        self.x_label = "Месяц"
        self.y_label = "Прибыль"
        self.chart_type = 'line'
        
        # Настройки серий
        self.series = [
            {
                'name': 'Прибыль',
                'value_key': 'profit',
                'color': '#198754'
            },
            {
                'name': 'ROI',
                'value_key': 'roi',
                'color': '#0d6efd',
                'y_axis_id': 'secondary'
            }
        ]
        
        # Форматирование валюты
        self.currency_format = '$'
        
        # Настройки отображения
        self.settings = {
            'show_monthly_breakdown': True
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
        Обновляет график прибыли на основе текущих данных.
        """
        if not self.data or 'months_data' not in self.data:
            # Если данных нет, показываем пустой график
            self._setup_figure()
            return
            
        # Получаем данные для графика
        chart_type = self.config.get('type', self.chart_type)
        months_data = self.data.get('months_data', [])
        
        if not months_data:
            self._setup_figure()
            self.ax.text(0.5, 0.5, 'Нет данных о прибыли по месяцам', 
                        ha='center', va='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return
            
        # Очищаем текущую фигуру
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        
        # Создаем вторую ось Y для ROI
        self.ax2 = self.ax.twinx()
        
        # Выбираем тип графика и отрисовываем
        if chart_type == 'line':
            self._draw_line_chart(months_data)
        elif chart_type == 'bar':
            self._draw_bar_chart(months_data)
        else:
            # По умолчанию линейный график
            self._draw_line_chart(months_data)
        
        # Применяем тесную компоновку
        self.figure.tight_layout()
        
        # Обновляем холст
        self.canvas.draw()
    
    def _draw_line_chart(self, months_data: List[Dict[str, Any]]):
        """
        Рисует линейный график прибыли и ROI по месяцам.
        
        Args:
            months_data: Список словарей с данными по месяцам
        """
        # Извлекаем данные для построения графика
        months = [item['month'] for item in months_data]
        profit_values = [item['profit'] for item in months_data]
        roi_values = [item['roi'] for item in months_data]
        
        # Преобразуем месяцы в более читаемый формат
        readable_months = [self._format_month(month) for month in months]
        
        # Строим линию прибыли
        profit_line, = self.ax.plot(
            readable_months, 
            profit_values, 
            marker='o', 
            linestyle='-', 
            color=self.series[0]['color'],
            label=self.series[0]['name']
        )
        
        # Добавляем линию с накопительной прибылью
        cumulative_profit = np.cumsum(profit_values)
        cumulative_line, = self.ax.plot(
            readable_months, 
            cumulative_profit, 
            marker='s', 
            linestyle='--', 
            color='#6f42c1',
            label='Накопительная прибыль'
        )
        
        # Строим линию ROI на второй оси
        roi_line, = self.ax2.plot(
            readable_months, 
            roi_values, 
            marker='^', 
            linestyle='-.', 
            color=self.series[1]['color'],
            label=self.series[1]['name']
        )
        
        # Настраиваем оси
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(f"{self.y_label} ({self.currency_format})")
        self.ax2.set_ylabel("ROI (%)")
        
        # Добавляем сетку
        self.ax.grid(True, linestyle='--', alpha=0.7)
        
        # Добавляем горизонтальную линию на нуле для прибыли
        self.ax.axhline(y=0, color='#dc3545', linestyle='-', alpha=0.3)
        
        # Наклоняем метки оси X для лучшей читаемости
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')
        
        # Добавляем легенду
        lines = [profit_line, cumulative_line, roi_line]
        labels = [line.get_label() for line in lines]
        self.ax.legend(lines, labels, loc='upper left')
        
        # Устанавливаем заголовок если нужно
        if self.config.get('show_title', True):
            title = self.config.get('chart_title', self.title)
            self.ax.set_title(title)
            
        # Добавляем аннотацию с общей прибылью и ROI
        total_profit = self.data.get('profit', 0)
        total_roi = self.data.get('roi', 0)
        
        annotation_text = f"Общая прибыль: {self.currency_format}{total_profit:.2f}\nОбщий ROI: {total_roi:.2f}%"
        if total_profit > 0:
            bbox_color = '#d7f9e0'  # Зеленоватый для положительной прибыли
        else:
            bbox_color = '#f9d7da'  # Красноватый для отрицательной прибыли
            
        self.ax.annotate(
            annotation_text,
            xy=(0.02, 0.02),
            xycoords='axes fraction',
            ha='left',
            va='bottom',
            bbox=dict(boxstyle="round,pad=0.3", fc=bbox_color, ec='#dee2e6', alpha=0.8)
        )
    
    def _draw_bar_chart(self, months_data: List[Dict[str, Any]]):
        """
        Рисует столбчатую диаграмму прибыли и ROI по месяцам.
        
        Args:
            months_data: Список словарей с данными по месяцам
        """
        # Извлекаем данные для построения графика
        months = [item['month'] for item in months_data]
        profit_values = [item['profit'] for item in months_data]
        buyin_values = [item['total_buyin'] for item in months_data]
        prize_values = [item['total_prize'] for item in months_data]
        
        # Преобразуем месяцы в более читаемый формат
        readable_months = [self._format_month(month) for month in months]
        
        # Определяем ширину столбцов
        width = 0.35
        
        # Позиции столбцов
        x = np.arange(len(readable_months))
        
        # Столбцы для бай-инов (затрат)
        buyin_bars = self.ax.bar(
            x - width/2, 
            buyin_values, 
            width, 
            label='Бай-ины', 
            color='#dc3545'
        )
        
        # Столбцы для призов (доходов)
        prize_bars = self.ax.bar(
            x + width/2, 
            prize_values, 
            width, 
            label='Призы', 
            color='#198754'
        )
        
        # Строим линию ROI на второй оси
        roi_values = [item['roi'] for item in months_data]
        roi_line, = self.ax2.plot(
            x, 
            roi_values, 
            marker='^', 
            linestyle='-', 
            color='#0d6efd',
            label='ROI'
        )
        
        # Настраиваем оси
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(f"Сумма ({self.currency_format})")
        self.ax2.set_ylabel("ROI (%)")
        
        # Устанавливаем метки оси X
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(readable_months)
        
        # Наклоняем метки оси X для лучшей читаемости
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')
        
        # Добавляем сетку
        self.ax.grid(True, linestyle='--', alpha=0.7, axis='y')
        
        # Добавляем легенду
        handles = [buyin_bars, prize_bars, roi_line]
        labels = ['Бай-ины', 'Призы', 'ROI']
        self.ax.legend(handles, labels, loc='upper left')
        
        # Устанавливаем заголовок если нужно
        if self.config.get('show_title', True):
            title = self.config.get('chart_title', "Доходы и расходы по месяцам")
            self.ax.set_title(title)
            
        # Добавляем аннотацию с общей прибылью и ROI
        total_profit = self.data.get('profit', 0)
        total_roi = self.data.get('roi', 0)
        total_buyin = self.data.get('total_buyin', 0)
        total_prize = self.data.get('total_prize', 0)
        
        annotation_text = (
            f"Бай-ины: {self.currency_format}{total_buyin:.2f}\n"
            f"Призы: {self.currency_format}{total_prize:.2f}\n"
            f"Прибыль: {self.currency_format}{total_profit:.2f}\n"
            f"ROI: {total_roi:.2f}%"
        )
        
        if total_profit > 0:
            bbox_color = '#d7f9e0'  # Зеленоватый для положительной прибыли
        else:
            bbox_color = '#f9d7da'  # Красноватый для отрицательной прибыли
            
        self.ax.annotate(
            annotation_text,
            xy=(0.02, 0.02),
            xycoords='axes fraction',
            ha='left',
            va='bottom',
            bbox=dict(boxstyle="round,pad=0.3", fc=bbox_color, ec='#dee2e6', alpha=0.8)
        )
    
    def _format_month(self, month_str: str) -> str:
        """
        Преобразует строку месяца в более читаемый формат.
        
        Args:
            month_str: Строка месяца в формате 'YYYY-MM'
            
        Returns:
            Отформатированная строка месяца
        """
        try:
            date = datetime.strptime(month_str, '%Y-%m')
            return date.strftime('%b %Y')  # Например, 'Jan 2023'
        except ValueError:
            return month_str
    
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
        if 'series' in config:
            self.series = config['series']
        
        # Обновляем график с новыми настройками
        self._update_chart()
    
    def set_settings(self, settings: Dict[str, Any]):
        """
        Устанавливает настройки отображения графика прибыли.
        
        Args:
            settings: Словарь с настройками отображения
        """
        self.settings.update(settings)
        
        # Обновляем формат валюты, если он указан
        if 'currency_format' in settings:
            self.currency_format = settings['currency_format']
            
        self._update_chart()