"""
ROI-плагин для Hero.
"""

from .base import BaseStat

class ROIStat(BaseStat):
    name = "ROI"
    description = "Return On Investment (ROI) — средний возврат на вложенный бай-ин для Hero"

    def compute(self, tournaments, knockouts, sessions):
        total_buyin = sum(t.buyin for t in tournaments)
        total_payout = sum(t.payout for t in tournaments)
        if total_buyin == 0:
            roi = 0.0
        else:
            roi = (total_payout - total_buyin) / total_buyin * 100.0
        return {"roi": round(roi, 2), "total_buyin": total_buyin, "total_payout": total_payout}
