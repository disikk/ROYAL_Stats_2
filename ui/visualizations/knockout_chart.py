#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
График нокаутов в покерном трекере ROYAL_Stats.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ui.visualizations.base_chart import BaseChart

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.KnockoutChart')


class KnockoutChart(BaseChart):
    """
    График для отображения статистики нокаутов в турнирах.
    """
    
    def __init__(self, parent=None):
        """
        Инициализирует график нокаутов.
        
        Args:
            parent: Родительский виджет (опционально).
        """
        super().__init__(parent, title="Распределение нокаутов")
        
        # Данные для диаграммы
        self.labels = ['x2', 'x10', 'x100', 'x1000', 'x10000']
        self.values = [0] * len(self.labels)
        
        # Цвета для категорий нокаутов
        self.knockout_colors = {
            'x2': '#6610f2',      # Фиолетовый для x2
            'x10': '#6f42c1',     # Фиолетовый для x10
            'x100': '#d63384',    # Розовый для x100
            'x1000': '#dc3545',   # Красный для x1000
            'x10000': '#fd7e14',  # Оранжевый для x10000
            'single': '#198754',  # Зеленый для обычных нокаутов
            'multi': '#0dcaf0',   # Голубой для мульти-нокаутов
            'early': '#6610f2'    # Фиолетовый для ранних нокаутов
        }
        
        # Тип графика
        self.chart_type = 'bar'  # 'bar' или 'pie'
        
        # Дополнительные настройки
        self.show_values = True
        self.value_format = '{}'
        self.show_percent = False
        self.show_legend = True
    
    def update_data(self, data: Dict[str, Any]) -> None:
        """
        Обновляет данные графика.
        
        Args:
            data: Словарь с данными для отображения на графике.
                 В зависимости от типа графика, ожидаются различные ключи.
        """
        # Обновляем данные в зависимости от типа графика
        if self.chart_type == 'bar':
            # Для столбчатой диаграммы проверяем наличие ключей с количеством нокаутов
            if all(f'knockouts_{label}' in data for label in ['x2', 'x10', 'x100', 'x1000', 'x10000']):
                self.values = [
                    data.get('knockouts_x2', 0),
                    data.get('knockouts_x10', 0),
                    data.get('knockouts_x100', 0),
                    data.get('knockouts_x1000', 0),
                    data.get('knockouts_x10000', 0)
                ]
            elif 'knockouts_distribution' in data:
                # Альтернативный формат данных
                distribution = data['knockouts_distribution']
                self.values = [
                    distribution.get('x2', 0),
                    distribution.get('x10', 0),
                    distribution.get('x100', 0),
                    distribution.get('x1000', 0),
                    distribution.get('x10000', 0)
                ]
        elif self.chart_type == 'pie':
            # Для круговой диаграммы ищем ключи с типами нокаутов
            self.labels = []
            self.values = []
            
            # Сбор данных для круговой диаграммы
            pie_data = {}
            
            # Проверяем наличие ключей с типами нокаутов
            if 'single_knockouts' in data and 'multi_knockouts' in data:
                pie_data['single'] = data['single_knockouts']
                pie_data['multi'] = data['multi_knockouts']
                
                # Добавляем ранние нокауты, если они есть
                if 'early_stage_knockouts' in data:
                    pie_data['early'] = data['early_stage_knockouts']
                
                # Формируем списки меток и значений
                self.labels = list(pie_data.keys())
                self.values = list(pie_data.values())
            elif 'knockout_types' in data:
                # Альтернативный формат данных
                knockout_types = data['knockout_types']
                
                # Формируем списки меток и значений
                self.labels = list(knockout_types.keys())
                self.values = list(knockout_types.values())
        
        # Перерисовываем график
        self.redraw()
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настраивает график по конфигурации.
        
        Args:
            config: Словарь с настройками графика.
        """
        super().configure(config)
        
        # Тип графика
        if 'type' in config:
            self.chart_type = config['type']
            
        # Дополнительные настройки для KnockoutChart
        if 'x_label' in config:
            self.x_label = config['x_label']
        else:
            self.x_label = 'Тип нокаута'
            
        if 'y_label' in config:
            self.y_label = config['y_label']
        else:
            self.y_label = 'Количество'
            
        if 'show_values' in config:
            self.show_values = config['show_values']
            
        if 'show_percent' in config:
            self.show_percent = config['show_percent']
            
        if 'show_legend' in config:
            self.show_legend = config['show_legend']
            
        if 'value_format' in config:
            self.value_format = config['value_format']
            
        if 'colors' in config:
            # Обновляем только указанные цвета
            for label, color in config['colors'].items():
                self.knockout_colors[label] = color
                
        # Если указаны данные для графика
        if 'data' in config:
            data_config = config['data']
            if isinstance(data_config, list):
                # Список элементов с id, label и color
                self.labels = [item['id'] for item in data_config]
                self.label_names = {item['id']: item.get('label', item['id']) for item in data_config}
                for item in data_config:
                    if 'color' in item:
                        self.knockout_colors[item['id']] = item['color']
    
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
        
        # Отрисовываем график в зависимости от типа
        if self.chart_type == 'bar':
            self._draw_bar_chart(ax)
        elif self.chart_type == 'pie':
            self._draw_pie_chart(ax)
        else:
            logger.warning(f"Неизвестный тип графика: {self.chart_type}")
            
        # Обновляем заголовок с учетом общего количества нокаутов
        total_knockouts = sum(self.values)
        ax.set_title(
            f'{self.title} (всего: {total_knockouts})',
            fontsize=self.style['title_size'],
            fontweight=self.style['title_weight'],
            pad=10
        )
        
        # Тесное расположение элементов
        self.figure.tight_layout(pad=2.0)
        
        # Отрисовываем график
        self.canvas.draw()
    
    def _draw_bar_chart(self, ax):
        """
        Отрисовывает столбчатую диаграмму.
        
        Args:
            ax: Ось для рисования.
        """
        # Получаем цвета для каждой категории
        colors = [self.knockout_colors.get(label, '#0d6efd') for label in self.labels]
        
        # Создаем столбчатую диаграмму
        bars = ax.bar(
            self.labels,
            self.values,
            color=colors,
            edgecolor='#343a40',
            linewidth=0.5,
            alpha=0.8,
            width=0.6
        )
        
        # Добавляем значения на столбцы
        if self.show_values:
            for i, bar in enumerate(bars):
                height = bar.get_height()
                if height > 0:
                    # Форматируем значение
                    text = self.value_format.format(height)
                        
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.,
                        height + 0.05 * max(self.values if any(self.values) else [1]),
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
        ax.set_xlim(-0.5, len(self.labels) - 0.5)
        
        if max(self.values) == 0:
            ax.set_ylim(0, 5)
        else:
            ax.set_ylim(0, max(self.values) * 1.25)  # Немного больше места сверху
        
        # Настраиваем метки осей
        ax.set_xticks(range(len(self.labels)))
        ax.set_xticklabels(self.labels, fontsize=self.style['tick_label_size'])
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
    
    def _draw_pie_chart(self, ax):
        """
        Отрисовывает круговую диаграмму.
        
        Args:
            ax: Ось для рисования.
        """
        # Получаем цвета для каждой категории
        colors = [self.knockout_colors.get(label, '#0d6efd') for label in self.labels]
        
        # Получаем метки для легенды
        if hasattr(self, 'label_names'):
            # Используем преобразование из настроек
            legend_labels = [self.label_names.get(label, label) for label in self.labels]
        else:
            # Или преобразуем метки напрямую
            legend_labels = [
                'Обычные нокауты' if label == 'single' else
                'Мульти-нокауты' if label == 'multi' else
                'Ранние нокауты' if label == 'early' else
                label
                for label in self.labels
            ]
        
        # Рассчитываем проценты
        total = sum(self.values)
        percents = [value / total * 100 if total > 0 else 0 for value in self.values]
        
        # Создаем круговую диаграмму
        wedges, texts, autotexts = ax.pie(
            self.values,
            labels=None,  # Не добавляем метки на диаграмму
            autopct='%1.1f%%' if self.show_percent else None,
            colors=colors,
            startangle=90,
            shadow=False,
            wedgeprops={'edgecolor': '#343a40', 'linewidth': 0.5, 'alpha': 0.8}
        )
        
        # Настраиваем автотексты (проценты)
        if self.show_percent:
            for autotext in autotexts:
                autotext.set_fontsize(self.style['tick_label_size'])
                autotext.set_fontweight('bold')
        
        # Добавляем легенду
        if self.show_legend:
            # Формируем метки для легенды с учетом значений
            if self.show_values:
                legend_labels = [f"{label} ({self.values[i]})" for i, label in enumerate(legend_labels)]
                
            ax.legend(
                wedges,
                legend_labels,
                loc='best',
                fontsize=self.style['tick_label_size']
            )
        
        # Устанавливаем равные оси для круговой диаграммы
        ax.set_aspect('equal')