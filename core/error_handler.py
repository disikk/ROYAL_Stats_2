#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для централизованной обработки ошибок в ROYAL_Stats.
"""

import logging
import functools
import traceback
from typing import Callable, Any, Dict, Optional, TypeVar, cast

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.ErrorHandler')

# Тип для декоратора
F = TypeVar('F', bound=Callable[..., Any])

class AppError(Exception):
    """
    Базовый класс для всех ошибок приложения.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Инициализирует объект ошибки.
        
        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали об ошибке (опционально)
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        
class DatabaseError(AppError):
    """Ошибка при работе с базой данных."""
    pass

class ParserError(AppError):
    """Ошибка при парсинге файлов."""
    pass

class ImportError(AppError):
    """Ошибка при импорте файлов."""
    pass

class StatisticsError(AppError):
    """Ошибка при расчете статистики."""
    pass

def log_error(func: F) -> F:
    """
    Декоратор для логирования ошибок.
    
    Args:
        func: Декорируемая функция
        
    Returns:
        Обернутая функция
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppError as e:
            # Логируем ошибку приложения с дополнительными деталями
            logger.error(f"{type(e).__name__}: {e.message}", 
                        extra=e.details, 
                        exc_info=True)
            raise
        except AttributeError as e:
            # Атрибуты могут отсутствовать из-за ошибок в структуре кода
            # Логируем ошибку, но пытаемся продолжить работу
            logger.error(f"Ошибка доступа к атрибуту в {func.__name__}: {str(e)}", 
                       exc_info=True)
            
            # Получаем имя класса, если функция является методом
            class_name = args[0].__class__.__name__ if args else "Unknown"
            details = {
                'function': func.__name__,
                'class': class_name,
                'args': str(args[1:]) if args else "",
                'kwargs': str(kwargs),
                'attribute': str(e),
                'traceback': traceback.format_exc()
            }
            
            # Формируем результат для некоторых известных паттернов
            if "db_manager" in str(e):
                # Возвращаем пустой результат для методов базы данных
                if func.__name__.startswith('get_'):
                    return []
                elif "tournament" in func.__name__ or "knockout" in func.__name__:
                    # Для операций с турнирами или нокаутами
                    return {'error': 'Database access error', 'details': str(e)}
                else:
                    # Для общих случаев
                    raise AppError(f"Ошибка доступа к базе данных: {str(e)}", details)
            else:
                # Для всех других ошибок атрибутов
                raise AppError(f"Ошибка в структуре приложения: {str(e)}", details)
        except Exception as e:
            # Логируем неожиданную ошибку и преобразуем ее в AppError
            logger.error(f"Неожиданная ошибка в {func.__name__}: {str(e)}", 
                        exc_info=True)
            # Получаем имя класса, если функция является методом
            class_name = args[0].__class__.__name__ if args else "Unknown"
            details = {
                'function': func.__name__,
                'class': class_name,
                'args': str(args[1:]) if args else "",
                'kwargs': str(kwargs),
                'traceback': traceback.format_exc()
            }
            raise AppError(f"Неожиданная ошибка: {str(e)}", details)
    return cast(F, wrapper)

def handle_error(default_value: Any = None):
    """
    Декоратор для обработки ошибок с возвратом значения по умолчанию.
    
    Args:
        default_value: Значение по умолчанию, возвращаемое в случае ошибки
        
    Returns:
        Декоратор
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppError as e:
                logger.error(f"{type(e).__name__}: {e.message}", 
                            extra=e.details, 
                            exc_info=True)
                return default_value
            except Exception as e:
                logger.error(f"Неожиданная ошибка в {func.__name__}: {str(e)}", 
                            exc_info=True)
                return default_value
        return cast(F, wrapper)
    return decorator

def transaction(db_arg_name: str = 'db_manager'):
    """
    Декоратор для обертывания функции в транзакцию базы данных.
    
    Args:
        db_arg_name: Имя аргумента, содержащего объект DatabaseManager
        
    Returns:
        Декоратор
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Получаем объект db_manager
            db_manager = None
            if args and hasattr(args[0], db_arg_name):
                # Если первый аргумент - объект с атрибутом db_manager
                db_manager = getattr(args[0], db_arg_name)
            elif db_arg_name in kwargs:
                # Если db_manager передан в kwargs
                db_manager = kwargs[db_arg_name]
                
            if not db_manager:
                # Если не нашли db_manager, вызываем функцию без транзакции
                return func(*args, **kwargs)
                
            # Начинаем транзакцию
            try:
                db_manager.begin_transaction()
                result = func(*args, **kwargs)
                db_manager.commit()
                return result
            except Exception as e:
                # Откатываем транзакцию при ошибке
                db_manager.rollback()
                logger.error(f"Ошибка в транзакции функции {func.__name__}: {str(e)}", 
                            exc_info=True)
                raise
        return cast(F, wrapper)
    return decorator
        
def report_error(e: Exception, context: str = "") -> str:
    """
    Логирует ошибку и возвращает описание для пользователя.
    
    Args:
        e: Исключение
        context: Контекст ошибки (опционально)
        
    Returns:
        Сообщение об ошибке для пользователя
    """
    if isinstance(e, AppError):
        logger.error(f"{context}: {type(e).__name__}: {e.message}", 
                    extra=e.details, 
                    exc_info=True)
        return f"{context}: {e.message}"
    else:
        logger.error(f"{context}: Неожиданная ошибка: {str(e)}", 
                    exc_info=True)
        return f"{context}: {str(e)}"

def get_error_details(e: Exception) -> Dict[str, Any]:
    """
    Возвращает детальную информацию об ошибке.
    
    Args:
        e: Исключение
        
    Returns:
        Словарь с деталями ошибки
    """
    if isinstance(e, AppError):
        details = e.details.copy()
        details['message'] = e.message
        details['type'] = type(e).__name__
        return details
    else:
        return {
            'message': str(e),
            'type': type(e).__name__,
            'traceback': traceback.format_exc()
        }