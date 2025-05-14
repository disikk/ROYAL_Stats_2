#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль статистики нокаутов в покерных турнирах.
"""

import logging
from typing import Dict, List, Any, Optional

from stats.base_stat import BaseStat

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.KnockoutsStat')


class KnockoutsStat(BaseStat):
    """
    Модуль для анализа и визуализации нокаутов в покерных турнирах.
    
    Предоставляет функции для анализа обычных нокаутов, включая общее количество,
    нокауты на ранней стадии турнира, мульти-нокауты.
    """
    
    @property
    def name(self) -> str:
        """
        Уникальный идентификатор модуля.
        
        Returns:
            Строка с уникальным идентификатором модуля.
        """
        return "knockouts"
    
    @property
    def display_name(self) -> str:
        """
        Отображаемое имя для UI.
        
        Returns:
            Строка с человекочитаемым названием модуля.
        """
        return "Нокауты"
    
    def get_description(self) -> str:
        """
        Возвращает описание модуля для отображения в UI.
        
        Returns:
            Строка с описанием модуля.
        """
        return "Анализ нокаутов (когда Hero выбил другого игрока), включая мульти-нокауты и ранние нокауты"
    
    def get_sort_order(self) -> int:
        """
        Возвращает порядок сортировки модуля для отображения в UI.
        
        Returns:
            Целое число, определяющее порядок модуля.
        """
        # Нокауты - один из основных модулей, отображается вторым
        return 20
    
    def calculate(self, db_repository, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Вычисляет статистику нокаутов и возвращает данные.
        
        Args:
            db_repository: Репозиторий для доступа к данным.
            session_id: ID сессии для фильтрации данных (опционально).
            
        Returns:
            Словарь с рассчитанными статистическими данными:
            - total_knockouts: Общее количество нокаутов
            - early_stage_knockouts: Количество нокаутов на ранней стадии (9-6 игроков)
            - multi_knockouts: Количество мульти-нокаутов (дележка банка)
            - single_knockouts: Количество обычных нокаутов
            - knockouts_per_tournament: Среднее количество нокаутов на турнир
            - total_tournaments: Общее количество турниров
        """
        try:
            # Получаем все нокауты из репозитория
            knockouts = db_repository.get_knockouts(session_id)
            
            # Общее количество турниров
            tournaments = db_repository.get_tournaments(session_id)
            total_tournaments = len(tournaments)
            
            if not knockouts:
                logger.warning("Нет данных о нокаутах для расчета статистики")
                return {
                    'total_knockouts': 0,
                    'early_stage_knockouts': 0,
                    'multi_knockouts': 0,
                    'single_knockouts': 0,
                    'knockouts_per_tournament': 0.0,
                    'total_tournaments': total_tournaments
                }
            
            # Общее количество нокаутов
            total_knockouts = len(knockouts)
            
            # Количество нокаутов на ранней стадии (9-6 игроков)
            early_stage_knockouts = sum(1 for ko in knockouts if ko.early_stage)
            
            # Количество мульти-нокаутов и обычных нокаутов
            multi_knockouts = sum(1 for ko in knockouts if ko.multi_knockout)
            single_knockouts = total_knockouts - multi_knockouts
            
            # Среднее количество нокаутов на турнир
            knockouts_per_tournament = total_knockouts / total_tournaments if total_tournaments > 0 else 0.0
            
            # Формируем результат
            result = {
                'total_knockouts': total_knockouts,
                'early_stage_knockouts': early_stage_knockouts,
                'multi_knockouts': multi_knockouts,
                'single_knockouts': single_knockouts,
                'knockouts_per_tournament': knockouts_per_tournament,
                'total_tournaments': total_tournaments
            }
            
            return result
        except Exception as e:
            logger.error(f"Ошибка при расчете статистики нокаутов: {e}", exc_info=True)
            # Возвращаем пустые данные в случае ошибки
            return {
                'total_knockouts': 0,
                'early_stage_knockouts': 0,
                'multi_knockouts': 0,
                'single_knockouts': 0,
                'knockouts_per_tournament': 0.0,
                'total_tournaments': 0
            }
    
    def get_cards_config(self) -> List[Dict[str, Any]]:
        """
        Возвращает конфигурацию карточек для отображения в UI.
        
        Returns:
            Список словарей с конфигурацией карточек для статистики нокаутов.
        """
        return [
            {
                'id': 'total_knockouts',
                'title': 'Всего нокаутов',
                'format': '{}',
                'color': '#0d6efd',
                'width': 1
            },
            {
                'id': 'early_stage_knockouts',
                'title': 'Ранние нокауты',
                'format': '{}',
                'color': '#6610f2',
                'width': 1
            },
            {
                'id': 'knockouts_per_tournament',
                'title': 'Нокаутов на турнир',
                'format': '{:.2f}',
                'color': '#20c997',
                'width': 1
            },
            {
                'id': 'single_knockouts',
                'title': 'Обычные нокауты',
                'format': '{}',
                'color': '#198754',
                'width': 1
            },
            {
                'id': 'multi_knockouts',
                'title': 'Мульти-нокауты',
                'format': '{}',
                'color': '#0dcaf0',
                'width': 1
            }
        ]
    
    def get_chart_config(self) -> Dict[str, Any]:
        """
        Возвращает конфигурацию графика для отображения в UI.
        
        Returns:
            Словарь с конфигурацией графика распределения типов нокаутов.
        """
        return {
            'type': 'pie',
            'title': 'Распределение нокаутов',
            'data': [
                {
                    'id': 'single_knockouts',
                    'label': 'Обычные нокауты',
                    'color': '#198754'
                },
                {
                    'id': 'multi_knockouts',
                    'label': 'Мульти-нокауты',
                    'color': '#0dcaf0'
                },
                {
                    'id': 'early_stage_knockouts',
                    'label': 'Ранние нокауты',
                    'color': '#6610f2'
                }
            ],
            'show_values': True,
            'show_percent': True,
            'show_legend': True
        }
    
    def get_settings_config(self) -> List[Dict[str, Any]]:
        """
        Возвращает конфигурацию настроек модуля для отображения в UI.
        
        Returns:
            Список словарей с конфигурацией настроек.
        """
        return [
            {
                'id': 'early_stage_threshold',
                'name': 'Порог ранней стадии',
                'type': 'select',
                'value': 6,
                'options': [
                    {'value': 4, 'label': '9-7 игроков'},
                    {'value': 5, 'label': '9-5 игроков'},
                    {'value': 6, 'label': '9-4 игроков'},
                    {'value': 7, 'label': '9-3 игроков'},
                    {'value': 8, 'label': '9-2 игроков'}
                ],
                'description': 'Определяет, какой диапазон считать ранней стадией турнира'
            }
        ]