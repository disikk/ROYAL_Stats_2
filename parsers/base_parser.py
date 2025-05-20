# -*- coding: utf-8 -*-

"""
Базовый класс парсера для Royal Stats.
Все дочерние парсеры должны реализовывать только работу с Hero.
"""
import config # Для имени Hero

class BaseParser:
    """
    Базовый класс для всех парсеров проекта.
    Реализует базовую структуру и общие проверки.
    """

    def __init__(self, hero_name: str = config.HERO_NAME):
        # Имя Hero берется из конфигурации
        self.hero_name = hero_name

    def parse(self, file_content: str, filename: str = ""):
        """
        Метод-заглушка: должен быть переопределён в наследниках.
        Парсит содержимое файла и возвращает структурированные данные.

        Args:
            file_content: Содержимое файла в виде строки.
            filename: Имя файла (может быть полезно для определения турнира ID).

        Returns:
            Словарь или объект модели с извлеченными данными.
        """
        raise NotImplementedError("Метод parse должен быть реализован в дочернем классе.")

    def is_hero(self, name: str) -> bool:
        """
        Проверка: является ли игрок Hero.
        """
        # Для надёжности сравниваем с учётом регистра и лишних пробелов
        return name.strip() == self.hero_name