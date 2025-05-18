"""
Плагин для подсчёта общего количества нокаутов, совершённых Hero.
"""

from .base import BaseStat

class TotalKOStat(BaseStat):
    name = "Total KO"
    description = "Общее количество сделанных Hero нокаутов"

    def compute(self, tournaments, knockouts, sessions):
        # В большинстве архитектур количество KO есть в турнире (t.ko_count)
        if tournaments and hasattr(tournaments[0], "ko_count"):
            total_ko = sum(t.ko_count for t in tournaments)
        elif knockouts:  # Если KO детализированы списком (по каждому выбитому)
            total_ko = len(knockouts)
        else:
            total_ko = 0
        return {"total_ko": total_ko}
