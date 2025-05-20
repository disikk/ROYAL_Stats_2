# -*- coding: utf-8 -*-

"""
Пакет стат-плагинов Royal Stats.
Автоматически импортирует все плагины, унаследованные от BaseStat.
"""

import pkgutil
import importlib
import os # ИМПОРТИРУЕМ OS
import logging # Импортируем logging для использования в обработке ошибок импорта плагинов

from .base import BaseStat
# Импортируем базовый класс явно

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Уровень логирования для инициализации плагинов

# Автоматический импорт всех модулей в папке stats, кроме base и __init__
__all__ = []
# Указываем путь к текущему пакету для iter_modules
package_dir = os.path.dirname(__file__)
if package_dir == '': # Handle case where __file__ might not be a full path
    package_dir = '.'

logger.debug(f"Сканирование директории плагинов: {package_dir}")

for loader, module_name, is_pkg in pkgutil.iter_modules([package_dir]):
    if module_name not in ("base", "__init__"):
        try:
            # Импортируем модуль
            full_module_name = f".{module_name}"
            logger.debug(f"Попытка импорта модуля плагина: {full_module_name}")
            mod = importlib.import_module(full_module_name, package=__name__)
            logger.debug(f"Модуль {full_module_name} успешно импортирован.")

            # Ищем в модуле классы, которые являются подклассами BaseStat (кроме самого BaseStat)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseStat) and attr is not BaseStat:
                    # Добавляем имя класса в __all__
                    logger.debug(f"Найден стат-плагин: {attr_name} в модуле {module_name}")
                    __all__.append(attr_name)
                    # Можно также сохранить ссылку на класс в глобальном пространстве пакета,
                    # чтобы их можно было импортировать напрямую, например, from stats import BigKOStat
                    globals()[attr_name] = attr

        except Exception as e:
            # Логируем ошибку импорта плагина, но не прерываем работу
            logger.error(f"Ошибка при импорте стат-плагина '{module_name}': {e}")

logger.debug(f"Завершен поиск плагинов. Обнаружены плагины: {__all__}")

