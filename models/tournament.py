"""
Модель турнира для Hero в Royal Stats.
Описывает только то, что реально важно для Hero: ID турнира, место, выплата, бай-ин (целиком), KO.
"""

from dataclasses import dataclass

@dataclass
class HeroTournament:
    """
    Турнир с данными только по Hero.
    """
    tournament_id: str
    place: int           # Место, занятое Hero
    payout: float        # Итоговая выплата Hero (в долларах)
    buyin: float         # Фактическая стоимость входа в турнир (в долларах, целиком)
    ko_count: int        # Сколько KO совершил Hero в этом турнире

    def as_dict(self):
        return {
            "tournament_id": self.tournament_id,
            "place": self.place,
            "payout": self.payout,
            "buyin": self.buyin,
            "ko_count": self.ko_count,
        }
