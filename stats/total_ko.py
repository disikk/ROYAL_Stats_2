"""
Плагин для подсчёта общего количества нокаутов, совершённых Hero.
"""

from .base import BaseStat

class TotalKOStat(BaseStat):
    name = "Total KO"
    description = "Общее количество сделанных Hero нокаутов"

    def compute(self, tournaments, knockouts, sessions):
        total_ko = 0
        if tournaments:
            # Check if the first tournament (if any) has 'ko_count' key
            if tournaments[0] and isinstance(tournaments[0], dict) and 'ko_count' in tournaments[0]:
                total_ko = sum(t.get('ko_count', 0) or 0 for t in tournaments)
            # Fallback to knockouts list if ko_count not in tournament dicts
            elif knockouts:
                total_ko = len(knockouts)
        elif knockouts: # if tournaments is empty but knockouts is not
            total_ko = len(knockouts)
        
        return {"total_ko": total_ko}
