#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль статистики позиций (мест) в покерных турнирах.
"""

import logging
from typing import Dict, List, Any, Optional, Union

from stats.base_stat import BaseStat

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.PositionsStat')


class PositionsStat(BaseStat):
    """
    Модуль для анализа и визуализации позиций (мест) в покерных турнирах.
    
    Предоставляет функции для анализа распределения мест, расчета среднего места
    и других статистических метрик.
    """
    
    @property
    def name(self) -> str:
        """
        Уникальный идентификатор модуля.
        
        Returns:
            Строка с уникальным идентификатором модуля.
        """
        return "positions"
    
    @property
    def display_name(self) -> str:
        """
        Отображаемое имя для UI.
        
        Returns:
            Строка с человекочитаемым названием модуля.
        """
        return "Позиции"
    
    def get_description(self) -> str:
        """
        Возвращает описание модуля для отображения в UI.
        
        Returns:
            Строка с описанием модуля.
        """
        return "Анализ занятых мест в турнирах, включая среднее место и распределение мест"
    
    def get_sort_order(self) -> int:
        """
        Возвращает порядок сортировки модуля для отображения в UI.
        
        Returns:
            Целое число, определяющее порядок модуля.
        """
        # Позиции - один из основных модулей, поэтому отображается первым
        return 10
    
    def calculate(self, db_repository, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Вычисляет статистику позиций и возвращает данные.
        
        Args:
            db_repository: Репозиторий для доступа к данным.
            session_id: ID сессии для фильтрации данных (опционально).
            
        Returns:
            Словарь с рассчитанными статистическими данными:
            - places_distribution: Распределение мест в формате {место: количество}
            - avg_position: Среднее место (фактическое)
            - normalized_avg_position: Среднее нормализованное место (1-9)
            - first_places: Количество первых мест
            - second_places: Количество вторых мест
            - third_places: Количество третьих мест
            - total_tournaments: Общее количество турниров
            - itm_percent: Процент попадания в призы (топ-3)
        """
        # Получаем необходимые данные из репозитория
        try:
            # Распределение мест (нормализованное к 9-max)
            places_distribution = db_repository.get_places_distribution(session_id)
            
            # Общее количество турниров
            tournaments = db_repository.get_tournaments(session_id)
            total_tournaments = len(tournaments)
            
            if total_tournaments == 0:
                logger.warning("Нет данных о турнирах для расчета статистики позиций")
                return {
                    'places_distribution': {i: 0 for i in range(1, 10)},
                    'avg_position': 0.0,
                    'normalized_avg_position': 0.0,
                    'first_places': 0,
                    'second_places': 0,
                    'third_places': 0,
                    'total_tournaments': 0,
                    'itm_percent': 0.0
                }
            
            # Подсчет мест
            first_places = sum(1 for t in tournaments if t.finish_place == 1)
            second_places = sum(1 for t in tournaments if t.finish_place == 2)
            third_places = sum(1 for t in tournaments if t.finish_place == 3)
            
            # Среднее место (фактическое)
            finish_places = [t.finish_place for t in tournaments]
            avg_position = sum(finish_places) / len(finish_places) if finish_places else 0.0
            
            # Среднее нормализованное место
            normalized_places = [t.normalized_finish_place for t in tournaments]
            normalized_avg_position = sum(normalized_places) / len(normalized_places) if normalized_places else 0.0
            
            # Процент попадания в призы (топ-3)
            itm_count = first_places + second_places + third_places
            itm_percent = (itm_count / total_tournaments) * 100 if total_tournaments > 0 else 0.0
            
            # Формируем результат
            result = {
                'places_distribution': places_distribution,
                'avg_position': avg_position,
                'normalized_avg_position': normalized_avg_position,
                'first_places': first_places,
                'second_places': second_places,
                'third_places': third_places,
                'total_tournaments': total_tournaments,
                'itm_percent': itm_percent
            }
            
            return result
        except Exception as e:
            logger.error(f"Ошибка при расчете статистики позиций: {e}", exc_info=True)
            # Возвращаем пустые данные в случае ошибки
            return {
                'places_distribution': {i: 0 for i in range(1, 10)},
                'avg_position': 0.0,
                'normalized_avg_position': 0.0,
                'first_places': 0,
                'second_places': 0,
                'third_places': 0,
                'total_tournaments': 0,
                'itm_percent': 0.0
            }
    
    def get_cards_config(self) -> List[Dict[str, Any]]:
        """
        Возвращает конфигурацию карточек для отображения в UI.
        
        Returns:
            Список словарей с конфигурацией карточек для статистики позиций.
        """
        return [
            {
                'id': 'total_tournaments',
                'title': 'Всего турниров',
                'format': '{}',
                'color': '#0d6efd',
                'width': 1
            },
            {
                'id': 'normalized_avg_position',
                'title': 'Среднее место',
                'format': '{:.2f}',
                'color': '#fd7e14',
                'width': 1
            },
            {
                'id': 'itm_percent',
                'title': 'ITM (топ-3)',
                'format': '{:.2f}%',
                'color': '#20c997',
                'width': 1
            },
            {
                'id': 'first_places',
                'title': 'Первых мест',
                'format': '{}',
                'color': '#198754',
                'width': 1
            },
            {
                'id': 'second_places',
                'title': 'Вторых мест',
                'format': '{}',
                'color': '#0dcaf0',
                'width': 1
            },
            {
                'id': 'third_places',
                'title': 'Третьих мест',
                'format': '{}',
                'color': '#6f42c1',
                'width': 1
            }
        ]
    
    def get_chart_config(self) -> Dict[str, Any]:
        """
        Возвращает конфигурацию графика для отображения в UI.
        
        Returns:
            Словарь с конфигурацией графика распределения мест.
        """
        return {
            'type': 'bar',
            'title': 'Распределение мест',
            'x_label': 'Место',
            'y_label': 'Количество турниров',
            'data_key': 'places_distribution',
            'x_key': 'place',
            'y_key': 'count',
            'colors': {
                1: '#28a745',  # Зеленый для 1-го места
                2: '#17a2b8',  # Сине-зеленый для 2-го места
                3: '#6f42c1',  # Фиолетовый для 3-го места
                4: '#fd7e14',  # Оранжевый для 4-го места
                5: '#fd7e14',  # Оранжевый для 5-го места
                6: '#fd7e14',  # Оранжевый для 6-го места
                7: '#dc3545',  # Красный для 7-го места
                8: '#dc3545',  # Красный для 8-го места
                9: '#dc3545'   # Красный для 9-го места
            },
            'show_values': True,
            'show_percent': True
        }