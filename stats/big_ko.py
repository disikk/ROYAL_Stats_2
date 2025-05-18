"""
Плагин для подсчёта крупных нокаутов Hero (x1.5, x2, x10, x100, x1000, x10000).
Жадное разложение суммы KO для каждого турнира.
"""

from .base import BaseStat

class BigKOStat(BaseStat):
    name = "Big KO"
    description = (
        "Жадная декомпозиция KO Hero: сколько раз получал KO суммой x1.5, x2, x10, x100, x1000, x10000 бай-ина"
    )

    # Кратные бай-ина (от большего к меньшему, float!)
    # По текущему ТЗ нужны только x1.5, x2, x10 и x100
    MULTIPLIERS = [100.0, 10.0, 2.0, 1.5]

    def compute(self, tournaments, knockouts, sessions):
        # Ensure keys are correctly formatted, e.g. "x1.5" not "x1.50000"
        result = {}
        for m in self.MULTIPLIERS:
            if m == int(m): # Check if float is whole number
                 result[f"x{int(m)}"] = 0
            else:
                 result[f"x{m}"] = 0

        for t in tournaments:
            # Определяем сумму KO (остаток после вычета регулярных выплат)
            ko_sum = self._ko_sum(t) # t will be a dict
            buyin_val = t.get('buyin', 0.0) # Use .get for safety
            if buyin_val <= 0: # Cannot calculate multipliers if buy-in is 0 or missing
                continue
            
            if ko_sum <= 0:
                continue

            # Декомпозиция суммы KO по крупным множителям (жадный алгоритм)
            bi = buyin_val
            remains = ko_sum
            for m in self.MULTIPLIERS:
                value = m * bi
                if value == 0: continue # Avoid division by zero if bi or m is zero

                count = int(remains // value)
                if count > 0:
                    # key = f"x{int(m) if m.is_integer() else m}" # Old way
                    key = f"x{int(m)}" if m == int(m) else f"x{m}" # Corrected key formatting
                    if key in result: # Make sure key exists from init
                        result[key] += count
                    remains -= count * value
            if remains < 0: remains = 0 # just in case of float precision issues

        return result

    @staticmethod
    def _ko_sum(t_dict):
        # Для топ‑3 вычитаем стандартную выплату; для остальных — всё KO
        place = t_dict.get('place')
        payout = t_dict.get('payout', 0.0)
        buyin = t_dict.get('buyin', 0.0)

        if place == 1:
            return max(0, payout - 4 * buyin)
        elif place == 2:
            return max(0, payout - 3 * buyin)
        elif place == 3:
            return max(0, payout - 2 * buyin)
        else:
            return payout
