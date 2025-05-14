#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль статистики крупных нокаутов в покерных турнирах.
"""

import logging
from typing import Dict, List, Any, Optional

from stats.base_stat import BaseStat

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.LargeKOStat')


class LargeKOStat(BaseStat):
    """
    Модуль для анализа и визуализации крупных нокаутов в покерных турнирах.
    
    Предоставляет функции для анализа крупных нокаутов (x2, x10, x100, x1000, x10000).
    """
    
    @property
    def name(self) -> str:
        """
        Уникальный идентификатор модуля.
        
        Returns:
            Строка с уникальным идентификатором модуля.
        """
        return "large_knockouts"
    
    @property
    def display_name(self) -> str:
        """
        Отображаемое имя для UI.
        
        Returns:
            Строка с человекочитаемым названием модуля.
        """
        return "Крупные нокауты"
    
    def get_description(self) -> str:
        """
        Возвращает описание модуля для отображения в UI.
        
        Returns:
            Строка с описанием модуля.
        """
        return "Анализ крупных нокаутов (x2, x10, x100, x1000, x10000) в покерных турнирах"
    
    def get_sort_order(self) -> int:
        """
        Возвращает порядок сортировки модуля для отображения в UI.
        
        Returns:
            Целое число, определяющее порядок модуля.
        """
        # Крупные нокауты - важный модуль, отображается третьим
        return 30
    
    def calculate(self, db_repository, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Вычисляет статистику крупных нокаутов и возвращает данные.
        
        Args:
            db_repository: Репозиторий для доступа к данным.
            session_id: ID сессии для фильтрации данных (опционально).
            
        Returns:
            Словарь с рассчитанными статистическими данными:
            - knockouts_x2: Количество x2 нокаутов
            - knockouts_x10: Количество x10 нокаутов
            - knockouts_x100: Количество x100 нокаутов
            - knockouts_x1000: Количество x1000 нокаутов
            - knockouts_x10000: Количество x10000 нокаутов
            - total_large_knockouts: Общее количество крупных нокаутов
            - large_knockouts_per_tournament: Среднее количество крупных нокаутов на турнир
            - total_tournaments: Общее количество турниров
        """
        try:
            # Получаем все турниры из репозитория
            tournaments = db_repository.get_tournaments(session_id)
            total_tournaments = len(tournaments)
            
            if not tournaments:
                logger.warning("Нет данных о турнирах для расчета статистики крупных нокаутов")
                return {
                    'knockouts_x2': 0,
                    'knockouts_x10': 0,
                    'knockouts_x100': 0,
                    'knockouts_x1000': 0,
                    'knockouts_x10000': 0,
                    'total_large_knockouts': 0,
                    'large_knockouts_per_tournament': 0.0,
                    'total_tournaments': 0
                }
            
            # Суммируем крупные нокауты по всем турнирам
            knockouts_x2 = sum(t.knockouts_x2 for t in tournaments)
            knockouts_x10 = sum(t.knockouts_x10 for t in tournaments)
            knockouts_x100 = sum(t.knockouts_x100 for t in tournaments)
            knockouts_x1000 = sum(t.knockouts_x1000 for t in tournaments)
            knockouts_x10000 = sum(t.knockouts_x10000 for t in tournaments)
            
            # Общее количество крупных нокаутов
            total_large_knockouts = (
                knockouts_x2 + 
                knockouts_x10 + 
                knockouts_x100 + 
                knockouts_x1000 + 
                knockouts_x10000
            )
            
            # Среднее количество крупных нокаутов на турнир
            large_knockouts_per_tournament = total_large_knockouts / total_tournaments if total_tournaments > 0 else 0.0
            
            # Формируем результат
            result = {
                'knockouts_x2': knockouts_x2,
                'knockouts_x10': knockouts_x10,
                'knockouts_x100': knockouts_x100,
                'knockouts_x1000': knockouts_x1000,
                'knockouts_x10000': knockouts_x10000,
                'total_large_knockouts': total_large_knockouts,
                'large_knockouts_per_tournament': large_knockouts_per_tournament,
                'total_tournaments': total_tournaments
            }
            
            return result
        except Exception as e:
            logger.error(f"Ошибка при расчете статистики крупных нокаутов: {e}", exc_info=True)
            # Возвращаем пустые данные в случае ошибки
            return {
                'knockouts_x2': 0,
                'knockouts_x10': 0,
                'knockouts_x100': 0,
                'knockouts_x1000': 0,
                'knockouts_x10000': 0,
                'total_large_knockouts': 0,
                'large_knockouts_per_tournament': 0.0,
                'total_tournaments': 0
            }
    
    def get_cards_config(self) -> List[Dict[str, Any]]:
        """
        Возвращает конфигурацию карточек для отображения в UI.
        
        Returns:
            Список словарей с конфигурацией карточек для статистики крупных нокаутов.
        """
        return [
            {
                'id': 'total_large_knockouts',
                'title': 'Всего крупных KO',
                'format': '{}',
                'color': '#0d6efd',
                'width': 1
            },
            {
                'id': 'large_knockouts_per_tournament',
                'title': 'Крупных KO на турнир',
                'format': '{:.2f}',
                'color': '#20c997',
                'width': 1
            },
            {
                'id': 'knockouts_x2',
                'title': 'x2 нокаутов',
                'format': '{}',
                'color': '#6610f2',
                'width': 1
            },
            {
                'id': 'knockouts_x10',
                'title': 'x10 нокаутов',
                'format': '{}',
                'color': '#6f42c1',
                'width': 1
            },
            {
                'id': 'knockouts_x100',
                'title': 'x100 нокаутов',
                'format': '{}',
                'color': '#d63384',
                'width': 1
            },
            {
                'id': 'knockouts_x1000',
                'title': 'x1000 нокаутов',
                'format': '{}',
                'color': '#dc3545',
                'width': 1
            },
            {
                'id': 'knockouts_x10000',
                'title': 'x10000 нокаутов',
                'format': '{}',
                'color': '#fd7e14',
                'width': 1
            }
        ]
    
    def get_chart_config(self) -> Dict[str, Any]:
        """
        Возвращает конфигурацию графика для отображения в UI.
        
        Returns:
            Словарь с конфигурацией графика распределения крупных нокаутов.
        """
        return {
            'type': 'bar',
            'title': 'Распределение крупных нокаутов',
            'x_label': 'Тип нокаута',
            'y_label': 'Количество',
            'data': [
                {
                    'id': 'knockouts_x2',
                    'label': 'x2',
                    'color': '#6610f2'
                },
                {
                    'id': 'knockouts_x10',
                    'label': 'x10',
                    'color': '#6f42c1'
                },
                {
                    'id': 'knockouts_x100',
                    'label': 'x100',
                    'color': '#d63384'
                },
                {
                    'id': 'knockouts_x1000',
                    'label': 'x1000',
                    'color': '#dc3545'
                },
                {
                    'id': 'knockouts_x10000',
                    'label': 'x10000',
                    'color': '#fd7e14'
                }
            ],
            'show_values': True
        }