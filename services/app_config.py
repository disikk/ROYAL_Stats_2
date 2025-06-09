# -*- coding: utf-8 -*-

"""
Централизованная конфигурация приложения Royal Stats.
"""

import os
import configparser
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
    def from_ini(cls, path: str) -> 'AppConfig':
        """Создает AppConfig из INI-файла."""
        parser = configparser.ConfigParser()
        parser.read(path, encoding="utf-8")
        base_dir = os.path.dirname(os.path.abspath(path))

        ko_coeff = {int(k): float(v) for k, v in parser.items("ko_coeff")} if parser.has_section("ko_coeff") else None
        buyin_avg = {float(k): float(v) for k, v in parser.items("buyin_avg_ko_map")} if parser.has_section("buyin_avg_ko_map") else None

        return cls(
            hero_name=parser.get("app", "hero_name", fallback="Hero"),
            app_version=parser.get("app", "app_version", fallback="0.1.0"),
            app_title=parser.get("app", "app_title", fallback="MBR Stats by disikk"),
            base_dir=base_dir,
            default_db_name=parser.get("paths", "default_db_name", fallback="royal_stats.db"),
            final_table_size=parser.getint("game", "final_table_size", fallback=9),
            early_ft_min_players=parser.getint("game", "early_ft_min_players", fallback=6),
            min_ko_blind_level_bb=parser.getint("game", "min_ko_blind_level_bb", fallback=0),
            ko_coeff=ko_coeff if ko_coeff is not None else {
                8: 0.40,
                7: 0.50,
                6: 0.60,
                5: 0.60,
                4: 0.65,
                3: 0.70,
                2: 0.70,
            },
            buyin_avg_ko_map=buyin_avg if buyin_avg is not None else {
                0.25: 0.23,
                1.0: 0.93,
                3.0: 2.79,
                10.0: 9.28,
                25.0: 23.18,
            },
            theme=parser.get("interface", "theme", fallback="dark"),
            lang=parser.get("interface", "lang", fallback="ru"),
            ui_scale=parser.getfloat("interface", "ui_scale", fallback=1.0),
            chart_type=parser.get("interface", "chart_type", fallback="bar"),
            debug=parser.getboolean("app", "debug", fallback=False),
        )

    def save_to_ini(self, path: str) -> None:
        """Сохраняет публичную часть конфигурации в INI-файл."""
        parser = configparser.ConfigParser()

        parser["game"] = {
            "final_table_size": str(self.final_table_size),
            "early_ft_min_players": str(self.early_ft_min_players),
            "min_ko_blind_level_bb": str(self.min_ko_blind_level_bb),
        }

        parser["ko_coeff"] = {str(k): str(v) for k, v in self.ko_coeff.items()}
        parser["buyin_avg_ko_map"] = {str(k): str(v) for k, v in self.buyin_avg_ko_map.items()}

        with open(path, "w", encoding="utf-8") as f:
            parser.write(f)


# --- Глобальный экземпляр конфигурации ---

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini")

try:
    app_config = AppConfig.from_ini(CONFIG_PATH)
except Exception:
    app_config = AppConfig()
    try:
        app_config.save_to_ini(CONFIG_PATH)
    except Exception:
        pass


