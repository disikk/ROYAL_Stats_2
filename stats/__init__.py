"""
Пакет стат-плагинов Royal Stats.
Автоматически импортирует все плагины, унаследованные от BaseStat.
"""

import pkgutil
import importlib
from .base import BaseStat

# Автоматический импорт всех модулей в папке stats, кроме base и __init__
__all__ = []
for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
    if module_name not in ("base", "__init__"):
        mod = importlib.import_module(f"{__name__}.{module_name}")
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, type) and issubclass(obj, BaseStat) and obj is not BaseStat:
                __all__.append(obj.__name__)

# После этого во внешнем коде: from stats import MyStatPlugin (если MyStatPlugin наследник BaseStat)
