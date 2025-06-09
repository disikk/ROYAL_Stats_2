# -*- coding: utf-8 -*-

"""
Пакет стат-плагинов Royal Stats.
Автоматически импортирует все плагины, унаследованные от BaseStat.
"""

import pkgutil
import importlib
import os  # ИМПОРТИРУЕМ OS
import logging  # Импортируем logging для использования в обработке ошибок импорта плагинов
from typing import List, Type

from importlib import metadata

from .base import BaseStat
# Импортируем базовый класс явно

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Уровень логирования для инициализации плагинов

# Автоматический импорт всех модулей в папке stats, кроме base и __init__
__all__ = []
# Указываем путь к текущему пакету для iter_modules
package_dir = os.path.dirname(__file__)
if package_dir == '': # Handle case where __file__ might not be a full path
    package_dir = '.'


for loader, module_name, is_pkg in pkgutil.iter_modules([package_dir]):
    if module_name not in ("base", "__init__"):
        try:
            # Импортируем модуль
            full_module_name = f".{module_name}"
            mod = importlib.import_module(full_module_name, package=__name__)

            # Ищем в модуле классы, которые являются подклассами BaseStat (кроме самого BaseStat)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseStat) and attr is not BaseStat:
                    # Добавляем имя класса в __all__
                    __all__.append(attr_name)
                    # Можно также сохранить ссылку на класс в глобальном пространстве пакета,
                    # чтобы их можно было импортировать напрямую, например, from stats import BigKOStat
                    globals()[attr_name] = attr

        except Exception as e:
            # Логируем ошибку импорта плагина, но не прерываем работу
            logger.error(f"Ошибка при импорте стат-плагина '{module_name}': {e}")


def discover_plugins(entry_point_group: str = "royal_stats.plugins") -> List[Type[BaseStat]]:
    """Возвращает все классы стат-плагинов из пакета и entry points."""
    plugins: List[Type[BaseStat]] = []

    # Сначала добавляем плагины из пакета stats
    for name in __all__:
        attr = globals().get(name)
        if isinstance(attr, type) and issubclass(attr, BaseStat) and attr is not BaseStat:
            plugins.append(attr)

    # Затем пробуем загрузить плагины из entry points
    try:
        eps = metadata.entry_points()
        selected = eps.select(group=entry_point_group) if hasattr(eps, "select") else eps.get(entry_point_group, [])
        for ep in selected:
            try:
                plugin_class = ep.load()
                if isinstance(plugin_class, type) and issubclass(plugin_class, BaseStat):
                    plugins.append(plugin_class)
            except Exception as e:  # pragma: no cover - защитная логика
                logger.error(f"Ошибка загрузки плагина из entry point {ep.name}: {e}")
    except Exception as e:  # pragma: no cover - защитная логика
        logger.error(f"Ошибка при получении entry points: {e}")

    return plugins


