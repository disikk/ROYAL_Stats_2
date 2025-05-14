#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модель для хранения информации о нокауте.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Knockout:
    """
    Класс для представления нокаута.
    
    Attributes:
        tournament_id: ID турнира, в котором произошел нокаут.
        knocked_out_player: Имя выбитого игрока.
        pot_size: Размер банка, выигранного в результате нокаута.
        session_id: ID сессии, к которой относится нокаут.
        
        id: Локальный ID записи в БД (автогенерируемый).
        hand_id: ID раздачи, в которой произошел нокаут.
        multi_knockout: Был ли это мульти-нокаут (деление банка).
        early_stage: Произошел ли нокаут на ранней стадии турнира (9-6 игроков).
        created_at: Время создания записи.
    """
    
    # Обязательные поля
    tournament_id: str
    knocked_out_player: str
    pot_size: int
    session_id: str
    
    # Опциональные поля
    id: Optional[int] = None
    hand_id: str = ""
    multi_knockout: bool = False
    early_stage: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует экземпляр класса в словарь для сохранения в БД.
        
        Returns:
            Словарь с атрибутами нокаута.
        """
        return {
            'tournament_id': self.tournament_id,
            'knocked_out_player': self.knocked_out_player,
            'pot_size': self.pot_size,
            'session_id': self.session_id,
            'id': self.id,
            'hand_id': self.hand_id,
            'multi_knockout': self.multi_knockout,
            'early_stage': self.early_stage,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Knockout':
        """
        Создает экземпляр класса из словаря.
        
        Args:
            data: Словарь с данными о нокауте.
            
        Returns:
            Экземпляр класса Knockout.
        """
        # Копируем словарь чтобы не изменять оригинал
        knockout_data = data.copy()
        
        # Преобразуем created_at из строки в datetime если это строка
        if 'created_at' in knockout_data and isinstance(knockout_data['created_at'], str):
            try:
                knockout_data['created_at'] = datetime.fromisoformat(knockout_data['created_at'])
            except ValueError:
                # Если не удалось преобразовать, используем текущее время
                knockout_data['created_at'] = datetime.now()
                
        # Сопоставляем ключи из словаря с параметрами конструктора
        required_params = {
            'tournament_id': knockout_data.get('tournament_id', ''),
            'knocked_out_player': knockout_data.get('knocked_out_player', 'Unknown'),
            'pot_size': knockout_data.get('pot_size', 0),
            'session_id': knockout_data.get('session_id', '')
        }
        
        # Опциональные параметры
        optional_params = {
            'id': knockout_data.get('id'),
            'hand_id': knockout_data.get('hand_id', ''),
            'multi_knockout': knockout_data.get('multi_knockout', False),
            'early_stage': knockout_data.get('early_stage', False),
            'created_at': knockout_data.get('created_at', datetime.now())
        }
        
        # Объединяем параметры и создаем экземпляр класса
        params = {**required_params, **optional_params}
        return cls(**params)