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
    MULTIPLIERS = [10000, 1000, 100, 10, 2, 1.5]

    def compute(self, tournaments, knockouts, sessions):
        result = {f"x{int(m) if m.is_integer() else m}": 0 for m in self.MULTIPLIERS}

        for t in tournaments:
            # Определяем сумму KO (остаток после вычета регулярных выплат)
            ko_sum = self._ko_sum(t)
            if ko_sum <= 0:
                continue

            # Декомпозиция суммы KO по крупным множителям (жадный алгоритм)
            bi = t.buyin
            remains = ko_sum
            for m in self.MULTIPLIERS:
                value = m * bi
                count = int(remains // value)
                if count > 0:
                    key = f"x{int(m) if m.is_integer() else m}"
                    result[key] += count
                    remains -= count * value

        return result

    @staticmethod
    def _ko_sum(t):
        # Для топ‑3 вычитаем стандартную выплату; для остальных — всё KO
        if t.place == 1:
            return max(0, t.payout - 4 * t.buyin)
        elif t.place == 2:
            return max(0, t.payout - 3 * t.buyin)
        elif t.place == 3:
            return max(0, t.payout - 2 * t.buyin)
        else:
            return t.payout
