"""
Базовый класс парсера для Royal Stats.
Все дочерние парсеры должны реализовывать только работу с Hero.
"""

class BaseParser:
    """
    Базовый класс для всех парсеров проекта.
    Реализует базовую структуру и общие проверки.
    """

    def __init__(self, hero_name="Hero"):
        # Имя Hero фиксировано для всех задач (можно переопределить в дочернем классе)
        self.hero_name = hero_name

    def parse(self, file_content):
        """
        Метод-заглушка: должен быть переопределён в наследниках.
        """
        raise NotImplementedError("Метод parse должен быть реализован в дочернем классе.")

    def is_hero(self, name: str) -> bool:
        """
        Проверка: является ли игрок Hero.
        """
        # Для надёжности сравниваем с учётом регистра и лишних пробелов
        return name.strip() == self.hero_name

    def filter_hero_only(self, data: list, key: str) -> list:
        """
        Фильтрует список данных, оставляя только записи по Hero.
        Удобно использовать для post-processing результатов парсинга.
        """
        return [row for row in data if row.get(key, "").strip() == self.hero_name]
