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
        self.re_tournament_id_content = re.compile(r"Tournament #(\d+)") # For content fallback
        self.re_tournament_id_filename = re.compile(r"Tournament #(\d+)") # For filename
        self.re_start_date = re.compile(r"Tournament started (\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")

    def parse(self, file_content, filename=""):
        """
        Возвращает: {"place": place, "payout": payout, "buyin": buyin, "tournament_id": tid, "date": date_str}
        """
        lines = file_content.splitlines()
        place, payout, buyin, tournament_id, date_str = None, None, None, None, None

        # 1. Try to get Tournament ID from filename
        if filename:
            m_tid_fn = self.re_tournament_id_filename.search(filename)
            if m_tid_fn:
                tournament_id = m_tid_fn.group(1)
        
        # 2. If not in filename, try from content (e.g. first line or specific line)
        if not tournament_id and lines:
            # Check first few lines for tournament ID
            for line in lines[:5]: 
                m_tid_content = self.re_tournament_id_content.search(line)
                if m_tid_content:
                    tournament_id = m_tid_content.group(1)
                    break

        # Стартовая дата турнира (если есть)
        m_dt = self.re_start_date.search(file_content)
        if m_dt:
            date_str = m_dt.group(1)

        # Бай-ин парсим из первой строки (Tournament Name)
        if lines:
            m = self.re_buyin_from_title.search(lines[0])
            if m:
                buyin_str = m.group(1)
                if buyin_str:
                    buyin = float(buyin_str.rstrip('.'))

        # Ищем строку места Hero
        m = self.re_place.search(file_content)
        if m:
            place = int(m.group(1))

        # Итоговая выплата Hero
        m = self.re_payout.search(file_content)
        if m:
            payout_str = m.group(1)
            if payout_str:
                payout = float(payout_str.rstrip('.'))

        return {
            "tournament_id": tournament_id,
            "place": place,
            "payout": payout,
            "buyin": buyin,
            "tournament_id": tournament_id,
            "date": date_str,
        }
