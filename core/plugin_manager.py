#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Менеджер модулей статистики для покерного трекера ROYAL_Stats.
"""

import logging
import importlib
import pkgutil
import inspect
from typing import Dict, List, Any, Optional, Type, Union

from stats.base_stat import BaseStat
import stats

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.PluginManager')


class PluginManager:
    """
    Менеджер для управления модулями статистики.
    
    Отвечает за обнаружение, загрузку, регистрацию и выполнение модулей статистики.
    """
    
    def __init__(self):
        """
        Инициализация менеджера модулей.
        """
        self.modules: Dict[str, BaseStat] = {}
        self.active_modules: Dict[str, BaseStat] = {}
        self.discover_modules()
    
    def discover_modules(self) -> List[Type[BaseStat]]:
        """
        Обнаруживает все доступные модули статистики.
        
        Returns:
            Список классов модулей статистики.
        """
        try:
            # Получаем все модули из пакета stats
            module_classes: List[Type[BaseStat]] = []
            
            # Подход 1: Из списка в __init__.py (предпочтительно)
            if hasattr(stats, 'AVAILABLE_STATS'):
                module_classes = stats.AVAILABLE_STATS
                logger.info(f"Обнаружено {len(module_classes)} модулей из списка AVAILABLE_STATS")
            else:
                # Подход 2: Через сканирование пакета (запасной вариант)
                logger.warning("Список AVAILABLE_STATS не найден, выполняем сканирование пакета")
                for _, module_name, _ in pkgutil.iter_modules(stats.__path__):
                    if module_name == 'base_stat':
                        continue  # Пропускаем базовый класс
                        
                    # Импортируем модуль
                    module = importlib.import_module(f'stats.{module_name}')
                    
                    # Ищем в модуле классы, наследующиеся от BaseStat
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseStat) and obj != BaseStat:
                            module_classes.append(obj)
                            
                logger.info(f"Обнаружено {len(module_classes)} модулей через сканирование пакета")
            
            # Инициализируем и регистрируем все найденные модули
            for module_class in module_classes:
                try:
                    module_instance = module_class()
                    self.register_module(module_instance)
                except Exception as e:
                    logger.error(f"Ошибка при инициализации модуля {module_class.__name__}: {e}", exc_info=True)
            
            return module_classes
        except Exception as e:
            logger.error(f"Ошибка при обнаружении модулей: {e}", exc_info=True)
            return []
    
    def register_module(self, module: BaseStat) -> bool:
        """
        Регистрирует модуль статистики.
        
        Args:
            module: Экземпляр модуля статистики.
            
        Returns:
            True, если регистрация успешна, иначе False.
        """
        try:
            module_name = module.name
            if module_name in self.modules:
                logger.warning(f"Модуль с именем '{module_name}' уже зарегистрирован")
                return False
                
            self.modules[module_name] = module
            
            # Если модуль должен быть включен по умолчанию, активируем его
            if module.is_enabled_by_default():
                self.active_modules[module_name] = module
                
            logger.info(f"Зарегистрирован модуль: {module.display_name} ({module_name})")
            return True
        except Exception as e:
            logger.error(f"Ошибка при регистрации модуля: {e}", exc_info=True)
            return False
    
    def load_module(self, module_name: str) -> Optional[BaseStat]:
        """
        Загружает модуль статистики по имени.
        
        Args:
            module_name: Имя модуля.
            
        Returns:
            Экземпляр модуля статистики или None, если модуль не найден.
        """
        try:
            # Попробуем найти модуль среди уже загруженных
            if module_name in self.modules:
                return self.modules[module_name]
                
            # Если модуль не загружен, попробуем загрузить его динамически
            module_path = f'stats.{module_name}_stat'
            module = importlib.import_module(module_path)
            
            # Ищем класс модуля
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseStat) and obj != BaseStat:
                    # Создаем экземпляр модуля
                    module_instance = obj()
                    
                    # Регистрируем модуль
                    self.register_module(module_instance)
                    
                    return module_instance
            
            logger.warning(f"Модуль '{module_name}' не найден в {module_path}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при загрузке модуля '{module_name}': {e}", exc_info=True)
            return None
    
    def activate_module(self, module_name: str) -> bool:
        """
        Активирует модуль статистики.
        
        Args:
            module_name: Имя модуля.
            
        Returns:
            True, если активация успешна, иначе False.
        """
        if module_name not in self.modules:
            logger.warning(f"Модуль '{module_name}' не зарегистрирован")
            return False
            
        self.active_modules[module_name] = self.modules[module_name]
        logger.info(f"Активирован модуль: {self.modules[module_name].display_name} ({module_name})")
        return True
    
    def deactivate_module(self, module_name: str) -> bool:
        """
        Деактивирует модуль статистики.
        
        Args:
            module_name: Имя модуля.
            
        Returns:
            True, если деактивация успешна, иначе False.
        """
        if module_name not in self.active_modules:
            logger.warning(f"Модуль '{module_name}' не активен")
            return False
            
        del self.active_modules[module_name]
        logger.info(f"Деактивирован модуль: {self.modules[module_name].display_name} ({module_name})")
        return True
    
    def get_all_modules(self) -> List[BaseStat]:
        """
        Возвращает список всех зарегистрированных модулей.
        
        Returns:
            Список экземпляров модулей статистики.
        """
        return list(self.modules.values())
    
    def get_active_modules(self) -> List[BaseStat]:
        """
        Возвращает список активных модулей.
        
        Returns:
            Список экземпляров активных модулей статистики.
        """
        return list(self.active_modules.values())
    
    def get_module(self, module_name: str) -> Optional[BaseStat]:
        """
        Возвращает модуль по имени.
        
        Args:
            module_name: Имя модуля.
            
        Returns:
            Экземпляр модуля статистики или None, если модуль не найден.
        """
        return self.modules.get(module_name)
    
    def calculate_statistics(self, db_repository, session_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Вычисляет статистику для всех активных модулей.
        
        Args:
            db_repository: Репозиторий для доступа к данным.
            session_id: ID сессии для фильтрации данных (опционально).
            
        Returns:
            Словарь {имя_модуля: результаты_расчета} для всех активных модулей.
        """
        results = {}
        
        for module_name, module in self.active_modules.items():
            try:
                logger.debug(f"Расчет статистики модуля '{module_name}'")
                results[module_name] = module.calculate(db_repository, session_id)
            except Exception as e:
                logger.error(f"Ошибка при расчете статистики модуля '{module_name}': {e}", exc_info=True)
                results[module_name] = {}  # Пустой результат в случае ошибки
                
        return results