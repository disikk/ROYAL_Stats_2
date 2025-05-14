#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль статистики прибыли в покерных турнирах.
"""

import logging
from typing import Dict, List, Any, Optional

from stats.base_stat import BaseStat

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.ProfitStat')


class ProfitStat(BaseStat):
    """
    Модуль для анализа и визуализации прибыли в покерных турнирах.
    
    Предоставляет функции для анализа призовых выплат, ROI и прибыльности.
    """
    
    @property
    def name(self) -> str:
        """
        Уникальный идентификатор модуля.
        
        Returns:
            Строка с уникальным идентификатором модуля.
        """
        return "profit"
    
    @property
    def display_name(self) -> str:
        """
        Отображаемое имя для UI.
        
        Returns:
            Строка с человекочитаемым названием модуля.
        """
        return "Прибыль и ROI"
    
    def get_description(self) -> str:
        """
        Возвращает описание модуля для отображения в UI.
        
        Returns:
            Строка с описанием модуля.
        """
        return "Анализ прибыли, ROI и финансовых показателей в покерных турнирах"
    
    def get_sort_order(self) -> int:
        """
        Возвращает порядок сортировки модуля для отображения в UI.
        
        Returns:
            Целое число, определяющее порядок модуля.
        """
        # Прибыль - важный модуль, отображается четвертым
        return 40
    
    def calculate(self, db_repository, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Вычисляет статистику прибыли и ROI и возвращает данные.
        
        Args:
            db_repository: Репозиторий для доступа к данным.
            session_id: ID сессии для фильтрации данных (опционально).
            
        Returns:
            Словарь с рассчитанными статистическими данными:
            - total_prize: Общая сумма призовых
            - total_buy_in: Общая сумма бай-инов
            - profit: Прибыль (total_prize - total_buy_in)
            - roi: ROI в процентах (profit / total_buy_in * 100)
            - avg_prize: Средний выигрыш на турнир
            - avg_buy_in: Средний бай-ин
            - highest_prize: Наибольший выигрыш
            - prize_per_place: Словарь {место: средний_выигрыш}
            - total_tournaments: Общее количество турниров
        """
        try:
            # Получаем все турниры из репозитория
            tournaments = db_repository.get_tournaments(session_id)
            total_tournaments = len(tournaments)
            
            if not tournaments:
                logger.warning("Нет данных о турнирах для расчета статистики прибыли")
                return {
                    'total_prize': 0.0,
                    'total_buy_in': 0.0,
                    'profit': 0.0,
                    'roi': 0.0,
                    'avg_prize': 0.0,
                    'avg_buy_in': 0.0,
                    'highest_prize': 0.0,
                    'prize_per_place': {i: 0.0 for i in range(1, 10)},
                    'total_tournaments': 0
                }
            
            # Общие суммы призовых и бай-инов
            total_prize = sum(t.prize_total for t in tournaments)
            total_buy_in = sum(t.total_buy_in for t in tournaments)
            
            # Прибыль и ROI
            profit = total_prize - total_buy_in
            roi = (profit / total_buy_in * 100) if total_buy_in > 0 else 0.0
            
            # Средние значения
            avg_prize = total_prize / total_tournaments if total_tournaments > 0 else 0.0
            avg_buy_in = total_buy_in / total_tournaments if total_tournaments > 0 else 0.0
            
            # Наибольший выигрыш
            highest_prize = max((t.prize_total for t in tournaments), default=0.0)
            
            # Средний выигрыш по местам
            prize_per_place = {i: 0.0 for i in range(1, 10)}
            place_counts = {i: 0 for i in range(1, 10)}
            
            for t in tournaments:
                # Нормализуем место к диапазону 1-9
                place = t.normalized_finish_place
                if 1 <= place <= 9:
                    prize_per_place[place] = prize_per_place[place] + t.prize_total
                    place_counts[place] = place_counts[place] + 1
            
            # Рассчитываем средний выигрыш для каждого места
            for place in prize_per_place:
                if place_counts[place] > 0:
                    prize_per_place[place] = prize_per_place[place] / place_counts[place]
            
            # Формируем результат
            result = {
                'total_prize': total_prize,
                'total_buy_in': total_buy_in,
                'profit': profit,
                'roi': roi,
                'avg_prize': avg_prize,
                'avg_buy_in': avg_buy_in,
                'highest_prize': highest_prize,
                'prize_per_place': prize_per_place,
                'total_tournaments': total_tournaments
            }
            
            return result
        except Exception as e:
            logger.error(f"Ошибка при расчете статистики прибыли: {e}", exc_info=True)
            # Возвращаем пустые данные в случае ошибки
            return {
                'total_prize': 0.0,
                'total_buy_in': 0.0,
                'profit': 0.0,
                'roi': 0.0,
                'avg_prize': 0.0,
                'avg_buy_in': 0.0,
                'highest_prize': 0.0,
                'prize_per_place': {i: 0.0 for i in range(1, 10)},
                'total_tournaments': 0
            }
    
    def get_cards_config(self) -> List[Dict[str, Any]]:
        """
        Возвращает конфигурацию карточек для отображения в UI.
        
        Returns:
            Список словарей с конфигурацией карточек для статистики прибыли.
        """
        return [
            {
                'id': 'total_prize',
                'title': 'Общий выигрыш',
                'format': '${:.2f}',
                'color': '#198754',
                'width': 1
            },
            {
                'id': 'total_buy_in',
                'title': 'Общий бай-ин',
                'format': '${:.2f}',
                'color': '#dc3545',
                'width': 1
            },
            {
                'id': 'profit',
                'title': 'Прибыль',
                'format': '${:.2f}',
                'color': '#0d6efd',
                'width': 1
            },
            {
                'id': 'roi',
                'title': 'ROI',
                'format': '{:.2f}%',
                'color': '#6610f2',
                'width': 1
            },
            {
                'id': 'avg_prize',
                'title': 'Средний выигрыш',
                'format': '${:.2f}',
                'color': '#20c997',
                'width': 1
            },
            {
                'id': 'highest_prize',
                'title': 'Наибольший выигрыш',
                'format': '${:.2f}',
                'color': '#fd7e14',
                'width': 1
            }
        ]
    
    def get_chart_config(self) -> Dict[str, Any]:
        """
        Возвращает конфигурацию графика для отображения в UI.
        
        Returns:
            Словарь с конфигурацией графика зависимости выигрыша от места.
        """
        return {
            'type': 'bar',
            'title': 'Средний выигрыш по местам',
            'x_label': 'Место',
            'y_label': 'Средний выигрыш ($)',
            'data_key': 'prize_per_place',
            'x_key': 'place',
            'y_key': 'prize',
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
            'value_format': '${:.2f}'
        }
    
    def get_settings_config(self) -> List[Dict[str, Any]]:
        """
        Возвращает конфигурацию настроек модуля для отображения в UI.
        
        Returns:
            Список словарей с конфигурацией настроек.
        """
        return [
            {
                'id': 'show_negative_profit',
                'name': 'Показывать отрицательную прибыль',
                'type': 'boolean',
                'value': True,
                'description': 'Если выключено, отрицательная прибыль будет отображаться как 0'
            },
            {
                'id': 'currency',
                'name': 'Валюта',
                'type': 'select',
                'value': 'USD',
                'options': [
                    {'value': 'USD', 'label': 'USD ($)'},
                    {'value': 'EUR', 'label': 'EUR (€)'},
                    {'value': 'RUB', 'label': 'RUB (₽)'}
                ],
                'description': 'Валюта для отображения денежных значений'
            }
        ]