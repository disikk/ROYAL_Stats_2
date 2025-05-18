"""
ITM-плагин для Hero (In The Money — попадание в топ-3).
"""

from .base import BaseStat

class ITMStat(BaseStat):
    name = "ITM"
    description = "ITM% — процент попадания Hero в топ-3 (призовые места)"

    def compute(self, tournaments, knockouts, sessions):
        total = len(tournaments)
        if total == 0:
            return {"itm_percent": 0.0, "itm_count": 0, "total": 0}
        itm_count = sum(1 for t in tournaments if t.place in (1, 2, 3))
        itm_percent = itm_count / total * 100.0
        return {"itm_percent": round(itm_percent, 2), "itm_count": itm_count, "total": total}
