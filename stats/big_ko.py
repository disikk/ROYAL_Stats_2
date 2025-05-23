# -*- coding: utf-8 -*-

"""
Плагин для подсчёта крупных нокаутов Hero (x1.5, x2, x10, x100, x1000, x10000).
Жадное разложение суммы KO для каждого турнира.
Обновлен для работы с новой архитектурой и моделями.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament, OverallStats # Импортируем модели

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
                tournaments: List[Tournament],
                final_table_hands: List[Any],
                sessions: List[Any],
                overall_stats: Any,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает Big KO на основе турниров.
        """
        result = {}
        for m in self.MULTIPLIERS:
            key = f"x{int(m)}" if m == int(m) else f"x{m}"
            result[key] = 0

        import logging
        logger = logging.getLogger('ROYAL_Stats.BigKOStat')

        if overall_stats:
            for m in self.MULTIPLIERS:
                key = f"x{int(m)}" if m == int(m) else f"x{m}"
                result[key] = getattr(overall_stats, f"big_ko_{key.replace('.', '_')}", 0)
        else:
            logger.warning("Расчет Big KO выполняется в плагине (fallback).")
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
                for m in self.MULTIPLIERS:
                    value = m * buyin_val
                    if value <= 0:
                        continue
                    count = int(remains // value)
                    if count > 0:
                        key = f"x{int(m)}" if m == int(m) else f"x{m}"
                        if key in result:
                            result[key] += count
                        remains -= count * value
                        if m >= 10:
                            logger.info(f"Турнир {getattr(t, 'tournament_id', '?')}: {count} x {key} KO (ko_sum={ko_sum}, buyin={buyin_val})")
            logger.info(f"Big KO расчет: обработано {tournaments_processed} турниров, {tournaments_with_ko} с KO суммой")
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