# -*- coding: utf-8 -*-
"""Базовый класс плагина-парсера для Royal Stats."""

from typing import TypeVar, Generic

from .base_parser import BaseParser
from plugins.plugin_manager import Plugin

T = TypeVar('T')


class BaseParserPlugin(Plugin, BaseParser[T], Generic[T]):
    """Базовый класс плагинов-парсеров."""

    # Категория для plugin_manager
    category: str = "parsers"
    # Тип файла, который может обрабатывать парсер
    file_type: str = ""

    def can_handle(self, file_type: str) -> bool:
        """Возвращает True, если парсер может обработать файл указанного типа."""
        return file_type == self.file_type

