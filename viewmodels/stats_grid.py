# -*- coding: utf-8 -*-

"""
ViewModel для StatsGrid.
Содержит всю логику подготовки данных для отображения.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from .stat_card import StatCardViewModel
from models import Tournament, FinalTableHand, OverallStats

# Импортируем стат-плагины для расчетов
from stats import (
    TotalKOStat, ITMStat, ROIStat, BigKOStat,
    AvgKOPerTournamentStat, FinalTableReachStat,
    AvgFTInitialStackStat, EarlyFTKOStat, EarlyFTBustStat,
    FTStackConversionStat, FTStackConversionAttemptsStat,
    PreFTKOStat, KOLuckStat, ROIAdjustedStat, KOContributionStat,
    KOStage23Stat, KOStage45Stat, KOStage69Stat,
    WinningsFromITMStat, WinningsFromKOStat, DeepFTStat
)


@dataclass
class BigKOCardViewModel:
    """ViewModel для карточки Big KO."""
    
    tier: str  # "x1.5", "x2", etc.
    count: int
    subtitle: Optional[str] = None
    value_color: Optional[str] = None
    emoji: Optional[str] = None

    @staticmethod
    def get_big_ko_color(tier: str, total_knockouts: float, count: int) -> Optional[str]:
        """Определяет цвет для Big KO карточки."""
        if tier == "x10":
            if count <= 0 or total_knockouts <= 0:
                return None
            ratio = total_knockouts / count
            if ratio <= 25:
                return "#00FF00"  # Ярко-зеленый
            elif ratio <= 29:
                return "#10B981"  # Зеленый
            elif ratio <= 33:
                return "#F59E0B"  # Оранжевый
            else:
                return "#EF4444"  # Красный
        elif tier in ["x100", "x1000", "x10000"]:
            if count > 0:
                return "#10B981"  # Зеленый
        return None

    @staticmethod
    def get_big_ko_emoji(tier: str, total_knockouts: float, count: int) -> Optional[str]:
        """Возвращает emoji для Big KO карточки."""
        if tier == "x10":
            if count <= 0 or total_knockouts <= 0:
                return None
            ratio = total_knockouts / count
            if ratio <= 25:
                return "\U0001F525"  # Огонек
            elif ratio >= 34:
                return "\U0001F622"  # :sad:
            return None
        elif tier in ["x100", "x1000", "x10000"]:
            if count > 0:
                return "\U0001F525"  # Огонек
        return None
    
    @classmethod
    def create_from_stats(cls, tier: str, count: int, total_knockouts: float,
                         total_tournaments: int = 0) -> 'BigKOCardViewModel':
        """Создает ViewModel для Big KO карточки."""
        subtitle = None
        if tier in ["x1.5", "x2", "x10"] and count > 0 and total_knockouts > 0:
            per = total_knockouts / count
            subtitle = f"1 на {per:.0f} нокаутов"

        value_color = cls.get_big_ko_color(tier, total_knockouts, count)
        emoji = cls.get_big_ko_emoji(tier, total_knockouts, count)

        return cls(
            tier=tier,
            count=count,
            subtitle=subtitle,
            value_color=value_color,
            emoji=emoji
        )


@dataclass
class PlaceDistributionViewModel:
    """ViewModel для распределения мест."""
    
    place_distribution: Dict[int, int]
    chart_type: str  # "ft", "pre_ft", "all"
    total_count: int = 0


@dataclass
class StatsGridViewModel:
    """Основной ViewModel для сетки статистики."""
    
    # Основные карточки статистики
    stat_cards: Dict[str, StatCardViewModel]
    
    # Карточки Big KO
    big_ko_cards: Dict[str, BigKOCardViewModel]
    
    # Распределения для графиков
    place_distributions: Dict[str, PlaceDistributionViewModel]
    
    # Дополнительные данные
    overall_stats: OverallStats
    total_tournaments: int
    
    @classmethod
    def create_from_data(cls, 
                        tournaments: List[Tournament],
                        final_table_hands: List[FinalTableHand],
                        overall_stats: OverallStats,
                        precomputed_stats: Optional[Dict[str, Any]] = None) -> 'StatsGridViewModel':
        """Создает ViewModel из сырых данных."""
        
        # Подготовка предварительно рассчитанных значений
        if precomputed_stats is None:
            precomputed_stats = {
                'total_tournaments': overall_stats.total_tournaments,
                'total_buy_in': overall_stats.total_buy_in,
                'total_prize': overall_stats.total_prize,
                'total_knockouts': overall_stats.total_knockouts,
                'total_final_tables': overall_stats.total_final_tables,
            }
        
        # Расчет всех статистик через плагины
        roi_value = ROIStat().compute(tournaments, final_table_hands, precomputed_stats=precomputed_stats).get('roi', 0.0)
        itm_value = ITMStat().compute(tournaments, final_table_hands).get('itm_percent', 0.0)
        ft_reach = FinalTableReachStat().compute(tournaments, final_table_hands, precomputed_stats=precomputed_stats).get('final_table_reach_percent', 0.0)
        
        avg_stack_res = AvgFTInitialStackStat().compute(tournaments, final_table_hands)
        avg_chips = avg_stack_res.get('avg_ft_initial_stack_chips', 0.0)
        avg_bb = avg_stack_res.get('avg_ft_initial_stack_bb', 0.0)
        
        early_res = EarlyFTKOStat().compute(tournaments, final_table_hands)
        early_ko = early_res.get('early_ft_ko_count', 0)
        early_ko_per = early_res.get('early_ft_ko_per_tournament', 0.0)
        
        conv_res = FTStackConversionStat().compute(tournaments, final_table_hands)
        ft_stack_conv = conv_res.get('ft_stack_conversion', 0.0)
        
        attempts_res = FTStackConversionAttemptsStat().compute(tournaments, final_table_hands)
        avg_attempts = attempts_res.get('avg_ko_attempts_per_ft', 0.0)
        
        pre_ft_ko_res = PreFTKOStat().compute(tournaments, final_table_hands)
        pre_ft_ko_count = pre_ft_ko_res.get('pre_ft_ko_count', 0.0)
        
        ko_luck_value = KOLuckStat().compute(tournaments, final_table_hands).get('ko_luck', 0.0)
        roi_adj_value = ROIAdjustedStat().compute(tournaments, final_table_hands).get('roi_adj', 0.0)
        
        ko_contrib_res = KOContributionStat().compute(tournaments, final_table_hands)
        ko_contrib = ko_contrib_res.get('ko_contribution', 0.0)
        ko_contrib_adj = ko_contrib_res.get('ko_contribution_adj', 0.0)
        
        early_bust_res = EarlyFTBustStat().compute(tournaments, final_table_hands)
        early_bust_count = early_bust_res.get('early_ft_bust_count', 0)
        early_bust_per = early_bust_res.get('early_ft_bust_per_tournament', 0.0)
        
        # Новые статистики
        winnings_from_ko_res = WinningsFromKOStat().compute(tournaments, final_table_hands, precomputed_stats=precomputed_stats)
        winnings_from_ko = winnings_from_ko_res.get('winnings_from_ko', 0.0)
        
        ko_stage_2_3_res = KOStage23Stat().compute(tournaments, final_table_hands)
        ko_stage_2_3 = ko_stage_2_3_res.get('ko_stage_2_3', 0)
        attempts_stage_2_3 = ko_stage_2_3_res.get('ko_stage_2_3_attempts_per_tournament', 0.0)

        ko_stage_4_5_res = KOStage45Stat().compute(tournaments, final_table_hands)
        ko_stage_4_5 = ko_stage_4_5_res.get('ko_stage_4_5', 0)
        attempts_stage_4_5 = ko_stage_4_5_res.get('ko_stage_4_5_attempts_per_tournament', 0.0)
        
        ko_stage_6_9_res = KOStage69Stat().compute(tournaments, final_table_hands)
        ko_stage_6_9 = ko_stage_6_9_res.get('ko_stage_6_9', 0)

        winnings_from_itm_res = WinningsFromITMStat().compute(tournaments, final_table_hands, precomputed_stats=precomputed_stats)
        winnings_from_itm = winnings_from_itm_res.get('winnings_from_itm', 0.0)

        deep_ft_res = DeepFTStat().compute(tournaments, final_table_hands, overall_stats=overall_stats)
        deep_ft_reach = deep_ft_res.get('deep_ft_reach_percent', 0.0)
        deep_ft_stack_chips = deep_ft_res.get('deep_ft_avg_stack_chips', 0.0)
        deep_ft_stack_bb = deep_ft_res.get('deep_ft_avg_stack_bb', 0.0)
        deep_ft_roi = deep_ft_res.get('deep_ft_roi', 0.0)
        
        # Расчет средних мест
        all_places = [t.finish_place for t in tournaments if t.finish_place is not None]
        avg_all = sum(all_places) / len(all_places) if all_places else 0.0
        
        ft_places = [t.finish_place for t in tournaments 
                    if t.reached_final_table and t.finish_place is not None and 1 <= t.finish_place <= 9]
        avg_ft = sum(ft_places) / len(ft_places) if ft_places else 0.0
        
        no_ft_places = [t.finish_place for t in tournaments 
                       if not t.reached_final_table and t.finish_place is not None]
        avg_no_ft = sum(no_ft_places) / len(no_ft_places) if no_ft_places else 0.0
        
        # Создание карточек статистики
        stat_cards = {
            'tournaments': StatCardViewModel(
                title="Tournaments",
                value=str(overall_stats.total_tournaments)
            ),
            'knockouts': StatCardViewModel(
                title="Knockouts",
                value=f"{overall_stats.total_knockouts:.1f}"
            ),
            'avg_ko': StatCardViewModel(
                title="Avg KO/Tour",
                value=f"{overall_stats.avg_ko_per_tournament:.2f}"
            ),
            'roi': StatCardViewModel.create_roi_card(roi_value),
            'ko_contribution': StatCardViewModel.create_ko_contribution_card(ko_contrib, ko_contrib_adj),
            'itm': StatCardViewModel(
                title="ITM%",
                value=f"{itm_value:.1f}%"
            ),
            'ft_reach': StatCardViewModel(
                title="% Reach FT",
                value=f"{ft_reach:.1f}%"
            ),
            'avg_ft_stack': StatCardViewModel.create_avg_stack_card(avg_chips, avg_bb),
            'early_ft_ko': StatCardViewModel.create_early_ko_card(early_ko, early_ko_per),
            'ft_stack_conv': StatCardViewModel.create_stack_conversion_card(ft_stack_conv, avg_attempts),
            'early_ft_bust': StatCardViewModel(
                title="Early FT Bust",
                value=str(early_bust_count),
                subtitle=f"{early_bust_per:.2f} за турнир с FT"
            ),
            'avg_place_all': StatCardViewModel(
                title="Avg Place (All)",
                value=f"{avg_all:.2f}"
            ),
            'avg_place_ft': StatCardViewModel(
                title="Avg Place (FT)",
                value=f"{avg_ft:.2f}"
            ),
            'avg_place_no_ft': StatCardViewModel(
                title="Avg Place (No FT)",
                value=f"{avg_no_ft:.2f}"
            ),
            'pre_ft_ko': StatCardViewModel(
                title="Pre-FT KO",
                value=f"{pre_ft_ko_count:.1f}"
            ),
            'ko_luck': StatCardViewModel.create_ko_luck_card(ko_luck_value),
            'roi_adj': StatCardViewModel(
                title="ROI adj",
                value=StatCardViewModel.format_percentage(roi_adj_value),
                value_color=StatCardViewModel.get_value_color(roi_adj_value),
                tooltip="ROI с поправкой на удачу в нокаутах"
            ),
            'winnings_from_ko': StatCardViewModel(
                title="Выигрыш от KO",
                value=f"${winnings_from_ko:.0f}",
            ),
            'ko_stage_2_3': StatCardViewModel(
                title="KO 2-3 игрока",
                value=str(ko_stage_2_3),
                subtitle=f"{attempts_stage_2_3:.2f} попыток за турнир с FT",
                tooltip="Количество нокаутов в стадии 2-3 человека"
            ),
            'ko_stage_4_5': StatCardViewModel(
                title="KO 4-5 игроков",
                value=str(ko_stage_4_5),
                subtitle=f"{attempts_stage_4_5:.2f} попыток за турнир с FT",
                tooltip="Количество нокаутов в стадии 4-5 человек"
            ),
            'ko_stage_6_9': StatCardViewModel(
                title="KO 6-9 игроков",
                value=str(ko_stage_6_9),
                tooltip="Количество нокаутов в стадии 6-9 человек"
            ),
            'winnings_from_itm': StatCardViewModel(
                title="Выигрыш от ITM",
                value=f"${winnings_from_itm:.0f}",
                tooltip="Сумма, полученная от попадания в призы (места 1-3)"
            ),
            'deep_ft_reach': StatCardViewModel(
                title="% Reach \u22645",
                value=f"{deep_ft_reach:.1f}%",
                tooltip="Процент финалок, где Hero дошел до 5 игроков и меньше"
            ),
            'deep_ft_stack': StatCardViewModel(
                title="Stack \u22645",
                value=StatCardViewModel.format_number(deep_ft_stack_chips, decimals=0),
                subtitle=f"{StatCardViewModel.format_number(deep_ft_stack_chips, decimals=0)} фишек / {deep_ft_stack_bb:.1f} BB",
                tooltip="Средний стек при \u22645 игроках на финальном столе"
            ),
            'deep_ft_roi': StatCardViewModel(
                title="ROI \u22645",
                value=StatCardViewModel.format_percentage(deep_ft_roi),
                value_color=StatCardViewModel.get_value_color(deep_ft_roi),
                tooltip="ROI в турнирах, где Hero дошел до стадии \u22645 игроков"
            ),
        }
        
        # Создание карточек Big KO
        big_ko_cards = {}
        for tier, count_attr in [
            ("x1.5", overall_stats.big_ko_x1_5),
            ("x2", overall_stats.big_ko_x2),
            ("x10", overall_stats.big_ko_x10),
            ("x100", overall_stats.big_ko_x100),
            ("x1000", overall_stats.big_ko_x1000),
            ("x10000", overall_stats.big_ko_x10000),
        ]:
            big_ko_cards[tier] = BigKOCardViewModel.create_from_stats(
                tier, count_attr, overall_stats.total_knockouts, overall_stats.total_tournaments
            )
        
        # Расчет распределений мест
        place_dist_ft = {i: 0 for i in range(1, 10)}
        place_dist_pre_ft = {i: 0 for i in range(10, 19)}
        place_dist_all = {i: 0 for i in range(1, 19)}
        
        for t in tournaments:
            if t.finish_place is None:
                continue
            if 1 <= t.finish_place <= 9:
                place_dist_ft[t.finish_place] += 1
            if 10 <= t.finish_place <= 18:
                place_dist_pre_ft[t.finish_place] += 1
            if 1 <= t.finish_place <= 18:
                place_dist_all[t.finish_place] += 1
        
        place_distributions = {
            'ft': PlaceDistributionViewModel(place_dist_ft, 'ft'),
            'pre_ft': PlaceDistributionViewModel(place_dist_pre_ft, 'pre_ft'),
            'all': PlaceDistributionViewModel(place_dist_all, 'all'),
        }
        
        return cls(
            stat_cards=stat_cards,
            big_ko_cards=big_ko_cards,
            place_distributions=place_distributions,
            overall_stats=overall_stats,
            total_tournaments=overall_stats.total_tournaments
        )