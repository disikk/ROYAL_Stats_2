#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модель для хранения информации о сессии.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Session:
    """
    Класс для представления сессии загрузки файлов.
    
    Attributes:
        session_id: Уникальный ID сессии.
        session_name: Название сессии, задаваемое пользователем.
        
        id: Локальный ID записи в БД (автогенерируемый).
        tournaments_count: Количество турниров в сессии.
        knockouts_count: Количество нокаутов в сессии.
        avg_finish_place: Среднее место в турнирах сессии.
        total_prize: Общий выигрыш в турнирах сессии.
        avg_initial_stack: Средний начальный стек в турнирах сессии.
        total_buy_in: Общая сумма бай-инов в турнирах сессии.
        created_at: Время создания сессии.
    """
    
    # Обязательные поля
    session_id: str
    session_name: str
    
    # Опциональные поля
    id: Optional[int] = None
    tournaments_count: int = 0
    knockouts_count: int = 0
    avg_finish_place: float = 0.0
    total_prize: float = 0.0
    avg_initial_stack: float = 0.0
    total_buy_in: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def profit(self) -> float:
        """
        Рассчитывает профит (выигрыш - затраты).
        
        Returns:
            Профит сессии.
        """
        return self.total_prize - self.total_buy_in
    
    @property
    def roi(self) -> float:
        """
        Рассчитывает ROI (Return On Investment).
        
        Returns:
            ROI в процентах. 0, если total_buy_in равен 0.
        """
        if self.total_buy_in <= 0:
            return 0.0
        return (self.profit / self.total_buy_in) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует экземпляр класса в словарь для сохранения в БД.
        
        Returns:
            Словарь с атрибутами сессии.
        """
        return {
            'session_id': self.session_id,
            'session_name': self.session_name,
            'id': self.id,
            'tournaments_count': self.tournaments_count,
            'knockouts_count': self.knockouts_count,
            'avg_finish_place': self.avg_finish_place,
            'total_prize': self.total_prize,
            'avg_initial_stack': self.avg_initial_stack,
            'total_buy_in': self.total_buy_in,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """
        Создает экземпляр класса из словаря.
        
        Args:
            data: Словарь с данными о сессии.
            
        Returns:
            Экземпляр класса Session.
        """
        # Копируем словарь чтобы не изменять оригинал
        session_data = data.copy()
        
        # Преобразуем created_at из строки в datetime если это строка
        if 'created_at' in session_data and isinstance(session_data['created_at'], str):
            try:
                session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
            except ValueError:
                # Если не удалось преобразовать, используем текущее время
                session_data['created_at'] = datetime.now()
                
        # Сопоставляем ключи из словаря с параметрами конструктора
        required_params = {
            'session_id': session_data.get('session_id', ''),
            'session_name': session_data.get('session_name', '')
        }
        
        # Опциональные параметры
        optional_params = {
            'id': session_data.get('id'),
            'tournaments_count': session_data.get('tournaments_count', 0),
            'knockouts_count': session_data.get('knockouts_count', 0),
            'avg_finish_place': session_data.get('avg_finish_place', 0.0),
            'total_prize': session_data.get('total_prize', 0.0),
            'avg_initial_stack': session_data.get('avg_initial_stack', 0.0),
            'total_buy_in': session_data.get('total_buy_in', 0.0),
            'created_at': session_data.get('created_at', datetime.now())
        }
        
        # Объединяем параметры и создаем экземпляр класса
        params = {**required_params, **optional_params}
        return cls(**params)