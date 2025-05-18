"""
Модель одного нокаута для Hero в Royal Stats.
Только для хранения факта KO (без лишней инфы).
"""

from dataclasses import dataclass

@dataclass
class Knockout:
    """
    Представляет факт нокаута, совершённого Hero.
    """
    tournament_id: str   # ID турнира
    hand_idx: int        # Индекс раздачи
    split: bool = False  # True, если KO делился с другим игроком (split-pot)

    def as_dict(self):
        return {
            "tournament_id": self.tournament_id,
            "hand_idx": self.hand_idx,
            "split": self.split,
        }
