# -*- coding: utf-8 -*-

"""
Централизованная конфигурация приложения Royal Stats.
"""

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class AppConfig:
    """
    Класс конфигурации приложения.
    Содержит все настройки, необходимые для работы приложения.
    """
    
    # Базовые параметры приложения
    hero_name: str = "Hero"
    app_version: str = "0.1.0"
    app_title: str = "MBR Stats by disikk"
    
    # Пути и директории
    base_dir: str = field(default_factory=lambda: os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_dir: str = field(init=False)
    default_db_name: str = "royal_stats.db"
    default_db_path: str = field(init=False)
    last_db_file: str = field(init=False)
    stats_cache_file: str = field(init=False)
    current_db_path: str = field(init=False)
    
    # Настройки игры
    final_table_size: int = 9
    early_ft_min_players: int = 6
    min_ko_blind_level_bb: int = 0
    
    # Коэффициенты вероятности KO
    ko_coeff: Dict[int, float] = field(default_factory=lambda: {
        8: 0.40,
        7: 0.50,
        6: 0.60,
        5: 0.60,
        4: 0.65,
        3: 0.70,
        2: 0.70,
    })
    
    # Соответствие байинов и среднего размера нокаута
    buyin_avg_ko_map: Dict[float, float] = field(default_factory=lambda: {
        0.25: 0.23,
        1.0: 0.93,
        3.0: 2.79,
        10.0: 9.28,
        25.0: 23.18,
    })
    
    # Настройки интерфейса
    theme: str = "dark"  # dark / light
    lang: str = "ru"  # ru / en
    ui_scale: float = 1.0
    chart_type: str = "bar"  # bar / pie / line
    
    # Прочее
    debug: bool = False
    
    def __post_init__(self):
        """Инициализация зависимых полей после создания объекта."""
        # Устанавливаем производные пути
        self.db_dir = os.path.join(self.base_dir, "databases")
        self.default_db_path = os.path.join(self.db_dir, self.default_db_name)
        self.last_db_file = os.path.join(self.db_dir, "last_db_path.txt")
        self.stats_cache_file = os.path.abspath(os.path.join(self.db_dir, "stats_cache.json"))
        
        # Создаём каталог для БД, если его нет
        os.makedirs(self.db_dir, exist_ok=True)
        
        # Загружаем последнюю использованную БД
        self.current_db_path = self._load_last_db_path()
    
    def _load_last_db_path(self) -> str:
        """Загружает путь к последней использованной БД."""
        if os.path.exists(self.last_db_file):
            try:
                with open(self.last_db_file, "r", encoding="utf-8") as f:
                    path = f.read().strip()
                    return path or self.default_db_path
            except Exception:
                return self.default_db_path
        return self.default_db_path
    
    def set_current_db_path(self, path: str) -> None:
        """
        Устанавливает текущий путь к БД и сохраняет его.
        
        Args:
            path: Новый путь к базе данных
        """
        self.current_db_path = path
        try:
            with open(self.last_db_file, "w", encoding="utf-8") as f:
                f.write(path)
        except Exception:
            pass
    
    def get_db_connection_string(self) -> str:
        """Возвращает строку подключения к текущей БД."""
        return f"sqlite:///{self.current_db_path}"
    
    @classmethod
    def from_legacy_config(cls) -> 'AppConfig':
        """
        Создает AppConfig из существующего config.py.
        Используется для миграции со старой системы конфигурации.
        """
        # Импортируем старый config для получения значений
        import config as legacy_config
        
        return cls(
            hero_name=legacy_config.HERO_NAME,
            app_version=legacy_config.APP_VERSION,
            app_title=legacy_config.APP_TITLE,
            base_dir=legacy_config.BASE_DIR,
            default_db_name=legacy_config.DEFAULT_DB_NAME,
            final_table_size=legacy_config.FINAL_TABLE_SIZE,
            early_ft_min_players=legacy_config.EARLY_FT_MIN_PLAYERS,
            min_ko_blind_level_bb=legacy_config.MIN_KO_BLIND_LEVEL_BB,
            ko_coeff=legacy_config.KO_COEFF.copy(),
            buyin_avg_ko_map=legacy_config.BUYIN_AVG_KO_MAP.copy(),
            theme=legacy_config.THEME,
            lang=legacy_config.LANG,
            ui_scale=legacy_config.UI_SCALE,
            chart_type=legacy_config.CHART_TYPE,
            debug=legacy_config.DEBUG,
        )