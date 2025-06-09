# -*- coding: utf-8 -*-

"""
Базовый класс парсера для Royal Stats.
Все дочерние парсеры должны реализовывать только работу с Hero.
"""
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic
from services.app_config import app_config

# Тип для результата парсера
T = TypeVar('T')

class BaseParser(ABC, Generic[T]):
    """
    Базовый класс для всех парсеров проекта.
    Реализует базовую структуру и общие проверки.
    Теперь типизирован для возврата конкретных моделей.
    """

    def __init__(self, hero_name: str = app_config.hero_name):
        # Имя Hero берется из конфигурации
        self.hero_name = hero_name

    @abstractmethod
    def parse(self, file_content: str, filename: str = "") -> T:
        """
        Парсит содержимое файла и возвращает типизированные данные.

        Args:
            file_content: Содержимое файла в виде строки.
            filename: Имя файла (может быть полезно для определения турнира ID).

        Returns:
            Типизированный результат парсинга (зависит от конкретного парсера).
        """
        raise NotImplementedError("Метод parse должен быть реализован в дочернем классе.")

    def is_hero(self, name: str) -> bool:
        """
        Проверка: является ли игрок Hero.
        """
        # Для надёжности сравниваем с учётом регистра и лишних пробелов
        return name.strip() == self.hero_name