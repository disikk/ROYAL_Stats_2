# -*- coding: utf-8 -*-

"""
ViewModel для карточек статистики.
Содержит готовые для отображения данные.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StatCardViewModel:
    """ViewModel для отдельной карточки статистики."""
    
    title: str
    value: str
    subtitle: Optional[str] = None
    value_color: Optional[str] = None
    tooltip: Optional[str] = None
    
    @staticmethod
    def format_money(value: float) -> str:
        """Форматирует денежное значение."""
        if value == 0:
            return "$0.00"
        return f"${value:+,.2f}"
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 1) -> str:
        """Форматирует процентное значение."""
        return f"{value:+.{decimals}f}%"
    
    @staticmethod
    def format_number(value: float, decimals: int = 1) -> str:
        """Форматирует числовое значение."""
        if decimals == 0:
            return f"{value:,.0f}"
        return f"{value:,.{decimals}f}"
    
    @staticmethod
    def get_value_color(value: float) -> Optional[str]:
        """Возвращает цвет для значения на основе положительности/отрицательности."""
        if value > 0:
            return "#10B981"  # Зеленый
        elif value < 0:
            return "#EF4444"  # Красный
        return None  # Нейтральный
    
    @classmethod
    def create_roi_card(cls, roi_value: float) -> 'StatCardViewModel':
        """Создает карточку ROI."""
        return cls(
            title="ROI",
            value=cls.format_percentage(roi_value),
            value_color=cls.get_value_color(roi_value),
            tooltip="Return On Investment - средний возврат на вложенный бай-ин"
        )
    
    @classmethod
    def create_ko_luck_card(cls, ko_luck: float) -> 'StatCardViewModel':
        """Создает карточку KO Luck."""
        return cls(
            title="KO Luck",
            value=cls.format_money(ko_luck),
            value_color=cls.get_value_color(ko_luck),
            tooltip="Отклонение полученных денег от нокаутов относительно среднего"
        )
    
    @classmethod
    def create_ko_contribution_card(cls, contribution: float, contribution_adj: float) -> 'StatCardViewModel':
        """Создает карточку KO Contribution."""
        return cls(
            title="KO Contribution",
            value=f"{contribution:.1f}%",
            subtitle=f"С поправкой на удачу в КО (adj) {contribution_adj:.1f}%",
            tooltip="Доля выигрышей, полученная за счет нокаутов"
        )
    
    @classmethod
    def create_avg_stack_card(cls, chips: float, bb: float) -> 'StatCardViewModel':
        """Создает карточку среднего стека на финалке."""
        return cls(
            title="Avg FT Stack",
            value=cls.format_number(chips, decimals=0),
            subtitle=f"{cls.format_number(chips, decimals=0)} фишек / {bb:.1f} BB",
            tooltip="Средний стек Hero на старте финального стола"
        )
    
    @classmethod
    def create_early_ko_card(cls, count: float, per_tournament: float) -> 'StatCardViewModel':
        """Создает карточку Early FT KO."""
        return cls(
            title="Early FT KO",
            value=cls.format_number(count),
            subtitle=f"{per_tournament:.2f} за турнир с FT",
            tooltip="Количество нокаутов в ранней стадии финалки (9-6 игроков)"
        )
    
    @classmethod
    def create_stack_conversion_card(cls, conversion: float, attempts: float) -> 'StatCardViewModel':
        """Создает карточку FT Stack Conversion."""
        return cls(
            title="FT Stack Conv%",
            value=f"{conversion:.2f}",
            subtitle=f"{attempts:.2f} попыток за турнир с FT",
            tooltip="Процент конвертации попыток нокаута на финальном столе"
        )