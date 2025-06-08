# -*- coding: utf-8 -*-

"""
Плагин для подсчёта крупных нокаутов Hero (x1.5, x2, x10, x100, x1000, x10000).
Жадное разложение суммы KO для каждого турнира.
Автономный плагин для работы с сырыми данными.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session
import logging

logger = logging.getLogger('ROYAL_Stats.BigKOStat')

class BigKOStat(BaseStat):
    name = "Big KO"
    description = (
        "Жадная декомпозиция KO Hero: сколько раз получал KO суммой x1.5, x2, x10, x100, x1000, x10000 бай-ина"
    )

    # Кратные бай-ина (от большего к меньшему, float!)
    # По текущему ТЗ нужны только x1.5, x2, x10 и x100, x1000, x10000
    # Важно использовать float для сравнения
    MULTIPLIERS = [10000.0, 1000.0, 100.0, 10.0, 2.0, 1.5]

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает Big KO на основе турниров.
        
        Args:
            tournaments: Список турниров для анализа
            final_table_hands: Список рук финального стола (не используется)
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры:
                - precomputed_stats: Dict с предварительно рассчитанными big_ko_x* значениями
                
        Returns:
            Словарь с ключами 'x1.5', 'x2', 'x10', 'x100', 'x1000', 'x10000'
        """
        # Обработка None значений
        tournaments = tournaments or []
        
        # Инициализируем результат
        result = {}
        for m in self.MULTIPLIERS:
            key = f"x{int(m)}" if m == int(m) else f"x{m}"
            result[key] = 0

        # Проверяем наличие предварительно рассчитанных значений
        precomputed_stats = kwargs.get('precomputed_stats', {})
        
        # Пытаемся использовать предварительно рассчитанные значения
        all_precomputed = True
        for m in self.MULTIPLIERS:
            key = f"x{int(m)}" if m == int(m) else f"x{m}"
            big_ko_key = f"big_ko_{key.replace('.', '_')}"
            if big_ko_key in precomputed_stats:
                result[key] = precomputed_stats[big_ko_key]
            else:
                all_precomputed = False
                break
        
        # Если не все значения предварительно рассчитаны, считаем из сырых данных
        if not all_precomputed:
            tournaments_processed = 0
            tournaments_with_ko = 0
            
            for t in tournaments:
                tournaments_processed += 1
                ko_sum = self._ko_sum(t)
                buyin_val = t.buyin if t.buyin is not None else 0.0
                
                if buyin_val <= 0 or ko_sum <= 0:
                    continue
                    
                tournaments_with_ko += 1
                remains = ko_sum
                
                # Жадное разложение суммы KO
                for m in self.MULTIPLIERS:
                    value = m * buyin_val
                    if value <= 0:
                        continue
                        
                    count = int(remains // value)
                    if count > 0:
                        key = f"x{int(m)}" if m == int(m) else f"x{m}"
                        result[key] += count
                        remains -= count * value
            
            logger.debug(f"Big KO расчет: обработано {tournaments_processed} турниров, {tournaments_with_ko} с KO суммой")
        
        return result

    @staticmethod
    def _ko_sum(tournament: Tournament) -> float:
        """
        Оценивает сумму KO, полученную Hero в турнире, вычитая регулярные призовые.
        """
        place = tournament.finish_place
        payout = tournament.payout if tournament.payout is not None else 0.0
        buyin = tournament.buyin if tournament.buyin is not None else 0.0
        if buyin <= 0:
            return 0.0
        if place == 1:
            return max(0.0, payout - 4 * buyin)
        elif place == 2:
            return max(0.0, payout - 3 * buyin)
        elif place == 3:
            return max(0.0, payout - 2 * buyin)
        elif place is not None and place > 3:
            return payout
        else:
            return 0.0