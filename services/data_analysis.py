#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис для анализа данных в покерном трекере ROYAL_Stats.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Callable

from core.plugin_manager import PluginManager
from stats.base_stat import BaseStat

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.DataAnalysisService')


class DataAnalysisService:
    """
    Сервис для анализа статистических данных.
    
    Использует модули статистики для анализа данных и предоставляет интерфейс
    для получения различных статистических показателей.
    """
    
    def __init__(self, db_repository, plugin_manager=None):
        """
        Инициализирует сервис анализа данных.
        
        Args:
            db_repository: Репозиторий для доступа к данным.
            plugin_manager: Менеджер модулей статистики (опционально).
        """
        self.db_repository = db_repository
        self.plugin_manager = plugin_manager
    
    def calculate_statistics(self, session_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Вычисляет статистику для всех активных модулей.
        
        Args:
            session_id: ID сессии для фильтрации данных (опционально).
            
        Returns:
            Словарь {имя_модуля: результаты_расчета} для всех активных модулей.
        """
        if self.plugin_manager is None:
            logger.warning("plugin_manager не задан, расчет статистики невозможен")
            return {}
            
        return self.plugin_manager.calculate_statistics(self.db_repository, session_id)
    
    def calculate_module_statistics(self, module_name: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Вычисляет статистику для конкретного модуля.
        
        Args:
            module_name: Имя модуля статистики.
            session_id: ID сессии для фильтрации данных (опционально).
            
        Returns:
            Словарь с результатами расчета статистики модуля.
            Пустой словарь, если модуль не найден или не активен.
        """
        if self.plugin_manager is None:
            logger.warning("plugin_manager не задан, расчет статистики невозможен")
            return {}
            
        module = self.plugin_manager.get_module(module_name)
        if not module or module_name not in self.plugin_manager.active_modules:
            logger.warning(f"Модуль '{module_name}' не найден или не активен")
            return {}
            
        try:
            return module.calculate(self.db_repository, session_id)
        except Exception as e:
            logger.error(f"Ошибка при расчете статистики модуля '{module_name}': {e}", exc_info=True)
            return {}
    
    def get_module_cards_config(self, module_name: str) -> List[Dict[str, Any]]:
        """
        Возвращает конфигурацию карточек для модуля.
        
        Args:
            module_name: Имя модуля статистики.
            
        Returns:
            Список словарей с конфигурацией карточек для статистики модуля.
            Пустой список, если модуль не найден.
        """
        if self.plugin_manager is None:
            logger.warning("plugin_manager не задан, получение конфигурации карточек невозможно")
            return []
            
        module = self.plugin_manager.get_module(module_name)
        if not module:
            logger.warning(f"Модуль '{module_name}' не найден")
            return []
            
        try:
            return module.get_cards_config()
        except Exception as e:
            logger.error(f"Ошибка при получении конфигурации карточек модуля '{module_name}': {e}", exc_info=True)
            return []
    
    def get_module_chart_config(self, module_name: str) -> Dict[str, Any]:
        """
        Возвращает конфигурацию графика для модуля.
        
        Args:
            module_name: Имя модуля статистики.
            
        Returns:
            Словарь с конфигурацией графика для статистики модуля.
            Пустой словарь, если модуль не найден.
        """
        if self.plugin_manager is None:
            logger.warning("plugin_manager не задан, получение конфигурации графика невозможно")
            return {}
            
        module = self.plugin_manager.get_module(module_name)
        if not module:
            logger.warning(f"Модуль '{module_name}' не найден")
            return {}
            
        try:
            return module.get_chart_config()
        except Exception as e:
            logger.error(f"Ошибка при получении конфигурации графика модуля '{module_name}': {e}", exc_info=True)
            return {}
    
    def get_sessions(self) -> List[Dict]:
        """
        Получает список всех сессий.
        
        Returns:
            Список словарей с информацией о сессиях.
            Пустой список, если возникла ошибка или нет доступа к репозиторию.
        """
        try:
            if hasattr(self.db_repository, 'session_repository') and hasattr(self.db_repository.session_repository, 'get_all_sessions'):
                return self.db_repository.session_repository.get_all_sessions()
            elif hasattr(self.db_repository, 'get_all_sessions'):
                return self.db_repository.get_all_sessions()
            else:
                logger.warning("У db_repository нет метода get_all_sessions")
                return []
        except Exception as e:
            logger.error(f"Ошибка при получении списка сессий: {e}", exc_info=True)
            return []
    
    def get_session_tournaments(self, session_id: Optional[str] = None) -> List[Dict]:
        """
        Получает список турниров для определенной сессии.
        
        Args:
            session_id: ID сессии для фильтрации данных (опционально).
            
        Returns:
            Список словарей с информацией о турнирах.
        """
        try:
            if hasattr(self.db_repository, 'tournament_repository') and hasattr(self.db_repository.tournament_repository, 'get_tournaments'):
                return self.db_repository.tournament_repository.get_tournaments(session_id)
            elif hasattr(self.db_repository, 'get_tournaments'):
                return self.db_repository.get_tournaments(session_id)
            else:
                logger.warning("У db_repository нет метода get_tournaments")
                return []
        except Exception as e:
            logger.error(f"Ошибка при получении турниров сессии {session_id}: {e}", exc_info=True)
            return []
    
    def update_statistics(self, session_id: Optional[str] = None) -> bool:
        """
        Обновляет статистику в базе данных.
        
        Args:
            session_id: ID сессии для обновления статистики конкретной сессии (опционально).
                        Если не указан, обновляется общая статистика.
            
        Returns:
            True в случае успеха, False в случае ошибки.
        """
        try:
            # Проверяем наличие необходимых методов в репозитории
            if session_id:
                # Обновляем статистику для конкретной сессии
                if hasattr(self.db_repository, 'update_session_stats'):
                    return self.db_repository.update_session_stats(session_id)
                else:
                    logger.warning("У db_repository нет метода update_session_stats")
                    return False
            else:
                # Обновляем общую статистику
                if hasattr(self.db_repository, 'update_overall_statistics'):
                    return self.db_repository.update_overall_statistics()
                else:
                    logger.warning("У db_repository нет метода update_overall_statistics")
                    return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики: {e}", exc_info=True)
            return False
    
    def generate_report(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Генерирует полный отчет по статистике.
        
        Args:
            session_id: ID сессии для фильтрации данных (опционально).
            
        Returns:
            Словарь с полным отчетом, включая данные всех активных модулей.
        """
        # Получаем базовую информацию о сессии или общую статистику
        if session_id:
            session_info = self.db_repository.get_session(session_id)
            if not session_info:
                logger.warning(f"Сессия с ID '{session_id}' не найдена")
                return {'error': 'Session not found'}
                
            report_base = {
                'session_id': session_id,
                'session_name': session_info.session_name,
                'total_tournaments': session_info.tournaments_count,
                'total_knockouts': session_info.knockouts_count
            }
        else:
            # Общая статистика
            tournaments_count = self.db_repository.get_total_tournaments_count()
            knockouts_count = self.db_repository.get_total_knockouts_count()
            
            report_base = {
                'session_id': None,
                'session_name': 'All Sessions',
                'total_tournaments': tournaments_count,
                'total_knockouts': knockouts_count
            }
        
        # Рассчитываем статистику для всех активных модулей
        modules_stats = self.calculate_statistics(session_id)
        
        # Объединяем данные в один отчет
        report = {
            **report_base,
            'modules': modules_stats
        }
        
        return report