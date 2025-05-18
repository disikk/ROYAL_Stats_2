"""
Парсер итогового Tournament Summary для Hero.
Бай-ин берём из первой строки (названия турнира), а не из строки Buy-in!
"""

import re

class TournamentSummaryParser:
    """
    Парсер summary-файла турнира только для Hero.
    """

    def __init__(self, hero_name="Hero"):
        self.hero_name = hero_name
        # Регулярки для поиска места и выплат по Hero
        self.re_place = re.compile(r"You finished the tournament in (\d+)[a-z]{2} place")
        self.re_payout = re.compile(r"You received a total of \$?([\d\.]+)")
        self.re_buyin_from_title = re.compile(r"[$€]([\d]+(?:\.\d+)?)")  # ищет $25, $10, €1 и т.д.

    def parse(self, file_content):
        """
        Возвращает: {"place": place, "payout": payout, "buyin": buyin}
        """
        lines = file_content.splitlines()
        place, payout, buyin = None, None, None

        # Бай-ин парсим из первой строки (Tournament Name)
        if lines:
            m = self.re_buyin_from_title.search(lines[0])
            if m:
                buyin = float(m.group(1))

        # Ищем строку места Hero
        m = self.re_place.search(file_content)
        if m:
            place = int(m.group(1))

        # Итоговая выплата Hero
        m = self.re_payout.search(file_content)
        if m:
            payout = float(m.group(1))

        return {
            "place": place,
            "payout": payout,
            "buyin": buyin
        }
