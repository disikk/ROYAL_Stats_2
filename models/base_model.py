# -*- coding: utf-8 -*-

"""
Базовый класс для всех моделей данных.
Предоставляет общий функционал для сериализации/десериализации.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, fields
from typing import Dict, Any, TypeVar, Type


T = TypeVar('T', bound='BaseModel')


@dataclass
class BaseModel(ABC):
    """
    Базовый класс для всех моделей данных.
    Предоставляет универсальную реализацию as_dict и from_dict.
    """
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Преобразует модель в словарь.
        Автоматически работает для всех dataclass наследников.
        
        Returns:
            Словарь с полями модели
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Создает экземпляр модели из словаря.
        Автоматически фильтрует только те поля, которые есть в dataclass.
        
        Args:
            data: Словарь с данными
            
        Returns:
            Экземпляр модели
        """
        # Получаем имена всех полей dataclass
        field_names = {f.name for f in fields(cls)}
        
        # Фильтруем только те ключи, которые есть в модели
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        
        return cls(**filtered_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Алиас для as_dict() для обратной совместимости.
        
        Returns:
            Словарь с полями модели
        """
        return self.as_dict()
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Обновляет поля модели из словаря.
        Обновляет только те поля, которые присутствуют в словаре.
        
        Args:
            data: Словарь с новыми значениями
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)