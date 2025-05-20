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
                final_table_hands: List[Any], # Не используется напрямую этим плагином
                sessions: List[Any], # Не используется напрямую этим плагином
                overall_stats: Any, # Используем overall_stats для извлечения посчитанных значений
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Получает посчитанные значения Big KO из OverallStats.
        Если OverallStats недоступен (fallback), рассчитывает сам.

        Args:
            tournaments: Список объектов Tournament (используется только в fallback).
            overall_stats: Объект OverallStats с уже посчитанными агрегатами.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с количеством KO для каждого множителя.
        """
        # По нашей архитектуре, расчет Big KO происходит в ApplicationService
        # и результат хранится в OverallStats. Плагин просто извлекает его.
        # Это делает плагин легковесным и позволяет переиспользовать логику расчета
        # в ApplicationService при обновлении OverallStats.

        result = {}
        # Инициализируем словарь результата
        for m in self.MULTIPLIERS:
            key = f"x{int(m)}" if m == int(m) else f"x{m}"
            result[key] = 0

        if overall_stats:
             # Если OverallStats доступен, берем значения оттуда
             for m in self.MULTIPLIERS:
                 key = f"x{int(m)}" if m == int(m) else f"x{m}"
                 # Получаем значение из объекта OverallStats, используя getattr на случай, если поле еще не добавлено
                 result[key] = getattr(overall_stats, f"big_ko_{key.replace('.', '_')}", 0)
        else:
             # Fallback расчет (только если OverallStats не передан)
             # Эта логика должна быть в ApplicationService, но сохраним ее здесь
             # как запасной вариант или для отдельного использования плагина.
             logger.warning("Расчет Big KO выполняется в плагине (fallback). Рекомендуется использовать OverallStats.")
             for t in tournaments:
                 ko_sum = self._ko_sum(t)
                 buyin_val = t.buyin if t.buyin is not None else 0.0
                 if buyin_val <= 0 or ko_sum <= 0:
                     continue

                 remains = ko_sum
                 for m in self.MULTIPLIERS:
                     value = m * buyin_val
                     if value <= 0: continue # Избегаем деления на ноль и некорректных множителей

                     count = int(remains // value)
                     if count > 0:
                         key = f"x{int(m)}" if m == int(m) else f"x{m}"
                         if key in result: # Убедимся, что ключ существует из инициализации
                             result[key] += count
                         remains -= count * value
                 # remains здесь может быть небольшим из-за особенностей Bounty Structure или округлений

        return result

    @staticmethod
    def _ko_sum(tournament: Tournament) -> float:
        """
        Оценивает сумму KO, полученную Hero в турнире, вычитая регулярные призовые.
        Используется только в fallback расчете в плагине.
        """
        place = tournament.finish_place
        payout = tournament.payout if tournament.payout is not None else 0.0
        buyin = tournament.buyin if tournament.buyin is not None else 0.0

        # Стандартные выплаты в 18-max SNG (4-3-2 бай-ина)
        if place == 1:
            # Победитель забирает только KO за соперника в хедзапе
            # Общая выплата = Регулярный приз (4 BI) + KO.
            # Если считать, что в хедзапе победитель не забирает свой собственный bounty,
            # то вся выплата > 4 * buyin - это KO.
            # По условию "в хедзапе победитель забирает только нокаут за соперника"
            # и "всегда 3 призовых места (выплаты 4-3-2 баййина)".
            # Это может быть интерпретировано так:
            # 1 место: получает 4 BI из регулярного призового фонда + свой KO + KO за выбитых.
            # НО, если "победитель забирает только нокаут за соперника (за себя самого не получает)",
            # то выплата может быть только KO частью.
            # Давайте примем, что payout из TS включает и призовые и KO.
            # Тогда, для оценки КО части, вычитаем регулярные призовые.
            # 1 место: payout - 4 * buyin (остаток это KO)
            # 2 место: payout - 3 * buyin
            # 3 место: payout - 2 * buyin
            # Остальные места: вся выплата (payout) это KO (так как нет регулярных призовых)

            # Учитываем, что payout может быть меньше регулярного приза, если KO часть была маленькой.
            # В этом случае, ko_sum = 0 или положительная часть.
            return max(0.0, payout - 4 * buyin)
        elif place == 2:
            return max(0.0, payout - 3 * buyin)
        elif place == 3:
            return max(0.0, payout - 2 * buyin)
        elif place is not None and place > 3:
            # Места вне призов, вся выплата - это KO
            return payout
        else:
            # Для турниров, где место неизвестно или Hero не попал в призы (но место > 3)
            # Если place is None, но есть payout > 0, это, вероятно, KO.
            return payout