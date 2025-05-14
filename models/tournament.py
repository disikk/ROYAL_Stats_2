#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модель для хранения информации о турнире.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Tournament:
    """
    Класс для представления турнира.
    
    Attributes:
        tournament_id: Уникальный ID турнира.
        buy_in: Чистый бай-ин (без рейка и баунти).
        players_count: Количество игроков в турнире.
        hero_name: Имя основного игрока (обычно "Hero").
        finish_place: Место, на котором игрок закончил турнир.
        prize_total: Общий выигрыш (включая баунти).
        bounty_total: Общая сумма баунти.
        session_id: ID сессии, к которой относится турнир.
        
        id: Локальный ID записи в БД (автогенерируемый).
        tournament_name: Название турнира.
        game_type: Тип игры.
        fee: Рейк турнира.
        bounty: Баунти-часть бай-ина.
        total_buy_in: Полный бай-ин (buy_in + fee + bounty).
        prize_pool: Общий призовой фонд.
        start_time: Время начала турнира.
        average_initial_stack: Средний начальный стек.
        knockouts_x2: Количество x2 нокаутов.
        knockouts_x10: Количество x10 нокаутов.
        knockouts_x100: Количество x100 нокаутов.
        knockouts_x1000: Количество x1000 нокаутов.
        knockouts_x10000: Количество x10000 нокаутов.
        created_at: Время создания записи.
    """
    
    # Обязательные поля
    tournament_id: str
    buy_in: float
    players_count: int
    hero_name: str
    finish_place: int
    prize_total: float
    bounty_total: float
    session_id: str
    
    # Опциональные поля
    id: Optional[int] = None
    tournament_name: str = ""
    game_type: str = "No Limit Hold'em"
    fee: float = 0.0
    bounty: float = 0.0
    total_buy_in: float = field(init=False)
    prize_pool: float = 0.0
    start_time: Optional[datetime] = None
    average_initial_stack: float = 0.0
    knockouts_x2: int = 0
    knockouts_x10: int = 0
    knockouts_x100: int = 0
    knockouts_x1000: int = 0
    knockouts_x10000: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """
        Валидация и инициализация после создания экземпляра.
        """
        # Валидация
        if self.finish_place < 1:
            raise ValueError("finish_place должен быть >= 1")
        if self.players_count < 1:
            raise ValueError("players_count должен быть >= 1")
        if self.finish_place > self.players_count:
            raise ValueError(f"finish_place ({self.finish_place}) не может быть больше players_count ({self.players_count})")
            
        # Вычисления
        self.total_buy_in = self.buy_in + self.fee + self.bounty
        
    @property
    def normalized_finish_place(self) -> int:
        """
        Возвращает место без нормализации, так как
        в файлах tournament summary уже указано реальное место.
        
        Returns:
            Место, занятое игроком в турнире.
        """
        return self.finish_place
        
    @property
    def is_itm(self) -> bool:
        """
        Определяет, попал ли игрок в призы (ITM - In The Money).
        Считаем, что топ-3 места всегда в призах.
        """
        return self.finish_place <= 3
        
    @property
    def total_knockouts(self) -> int:
        """
        Возвращает общее количество крупных нокаутов всех типов.
        """
        return (self.knockouts_x2 + self.knockouts_x10 + 
                self.knockouts_x100 + self.knockouts_x1000 + 
                self.knockouts_x10000)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует экземпляр класса в словарь для сохранения в БД.
        
        Returns:
            Словарь с атрибутами турнира.
        """
        result = {
            'tournament_id': self.tournament_id,
            'tournament_name': self.tournament_name,
            'game_type': self.game_type,
            'buy_in': self.buy_in,
            'fee': self.fee,
            'bounty': self.bounty,
            'total_buy_in': self.total_buy_in,
            'players_count': self.players_count,
            'prize_pool': self.prize_pool,
            'finish_place': self.finish_place,
            'prize': self.prize_total,
            'knockouts_x2': self.knockouts_x2,
            'knockouts_x10': self.knockouts_x10,
            'knockouts_x100': self.knockouts_x100,
            'knockouts_x1000': self.knockouts_x1000,
            'knockouts_x10000': self.knockouts_x10000,
            'session_id': self.session_id,
            'average_initial_stack': self.average_initial_stack,
        }
        
        # Преобразуем datetime в строку, если он есть
        if self.start_time:
            result['start_time'] = self.start_time.isoformat()
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tournament':
        """
        Создает экземпляр класса из словаря.
        
        Args:
            data: Словарь с данными о турнире.
            
        Returns:
            Экземпляр класса Tournament.
        """
        # Копируем словарь чтобы не изменять оригинал
        tournament_data = data.copy()
        
        # Преобразуем start_time из строки в datetime если это строка
        if 'start_time' in tournament_data and isinstance(tournament_data['start_time'], str):
            try:
                tournament_data['start_time'] = datetime.fromisoformat(tournament_data['start_time'])
            except ValueError:
                # Если не удалось преобразовать, оставляем None
                tournament_data['start_time'] = None
                
        # Преобразуем created_at из строки в datetime если это строка
        if 'created_at' in tournament_data and isinstance(tournament_data['created_at'], str):
            try:
                tournament_data['created_at'] = datetime.fromisoformat(tournament_data['created_at'])
            except ValueError:
                # Если не удалось преобразовать, используем текущее время
                tournament_data['created_at'] = datetime.now()
                
        # Сопоставляем ключи из словаря с параметрами конструктора
        # Некоторые ключи могут иметь разные имена
        required_params = {
            'tournament_id': tournament_data.get('tournament_id'),
            'buy_in': tournament_data.get('buy_in', 0.0),
            'players_count': tournament_data.get('players_count', 9),
            'hero_name': tournament_data.get('hero_name', 'Hero'),
            'finish_place': tournament_data.get('finish_place', 0),
            'prize_total': tournament_data.get('prize', tournament_data.get('prize_total', 0.0)),
            'bounty_total': tournament_data.get('bounty_total', 0.0),
            'session_id': tournament_data.get('session_id', '')
        }
        
        # Опциональные параметры
        optional_params = {
            'id': tournament_data.get('id'),
            'tournament_name': tournament_data.get('tournament_name', ''),
            'game_type': tournament_data.get('game_type', 'No Limit Hold\'em'),
            'fee': tournament_data.get('fee', 0.0),
            'bounty': tournament_data.get('bounty', 0.0),
            'prize_pool': tournament_data.get('prize_pool', 0.0),
            'start_time': tournament_data.get('start_time'),
            'average_initial_stack': tournament_data.get('average_initial_stack', 0.0),
            'knockouts_x2': tournament_data.get('knockouts_x2', 0),
            'knockouts_x10': tournament_data.get('knockouts_x10', 0),
            'knockouts_x100': tournament_data.get('knockouts_x100', 0),
            'knockouts_x1000': tournament_data.get('knockouts_x1000', 0),
            'knockouts_x10000': tournament_data.get('knockouts_x10000', 0),
            'created_at': tournament_data.get('created_at', datetime.now()),
        }
        
        # Объединяем параметры и создаем экземпляр класса
        params = {**required_params, **optional_params}
        return cls(**params)