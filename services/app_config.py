# -*- coding: utf-8 -*-

"""
Централизованная конфигурация приложения Royal Stats.
"""

import os
from dataclasses import dataclass, field
from typing import Dict
import configparser


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
    base_dir: str = field(
        default_factory=lambda: os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
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
    ko_coeff: Dict[int, float] = field(
        default_factory=lambda: {
            8: 0.40,
            7: 0.50,
            6: 0.60,
            5: 0.60,
            4: 0.65,
            3: 0.70,
            2: 0.70,
        }
    )

    # Соответствие байинов и среднего размера нокаута
    buyin_avg_ko_map: Dict[float, float] = field(
        default_factory=lambda: {
            0.25: 0.23,
            1.0: 0.93,
            3.0: 2.79,
            10.0: 9.28,
            25.0: 23.18,
        }
    )

    # Настройки интерфейса
    theme: str = "dark"  # dark / light
    lang: str = "ru"  # ru / en
    ui_scale: float = 1.0
    chart_type: str = "bar"  # bar / pie / line

    # Прочее
    debug: bool = False

    # Пути к реализациям основных сервисов
    services: Dict[str, str] = field(
        default_factory=lambda: {
            "event_bus": "services.event_bus.EventBus",
            "import_service": "services.import_service.ImportService",
            "statistics_service": "services.statistics_service.StatisticsService",
            "app_facade": "services.app_facade.AppFacade",
        }
    )

    def __post_init__(self):
        """Инициализация зависимых полей после создания объекта."""
        # Устанавливаем производные пути
        self.db_dir = os.path.join(self.base_dir, "databases")
        self.default_db_path = os.path.join(self.db_dir, self.default_db_name)
        self.last_db_file = os.path.join(self.db_dir, "last_db_path.txt")
        self.stats_cache_file = os.path.abspath(
            os.path.join(self.db_dir, "stats_cache.json")
        )

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
    def from_ini(cls, ini_path: str | None = None) -> "AppConfig":
        """Создает конфигурацию из INI-файла."""
        parser = configparser.ConfigParser()
        if ini_path and os.path.exists(ini_path):
            parser.read(ini_path, encoding="utf-8")
        base = cls()

        hero_name = parser.get("game", "hero_name", fallback=base.hero_name)
        final_table_size = parser.getint(
            "game", "final_table_size", fallback=base.final_table_size
        )
        early_ft_min_players = parser.getint(
            "game", "early_ft_min_players", fallback=base.early_ft_min_players
        )
        min_ko_blind_level_bb = parser.getint(
            "game", "min_ko_blind_level_bb", fallback=base.min_ko_blind_level_bb
        )

        ko_coeff = base.ko_coeff.copy()
        if parser.has_section("ko_coeff"):
            ko_coeff = {
                int(k): parser.getfloat("ko_coeff", k) for k in parser["ko_coeff"]
            }

        buyin_avg_ko_map = base.buyin_avg_ko_map.copy()
        if parser.has_section("buyin_avg_ko_map"):
            buyin_avg_ko_map = {
                float(k): parser.getfloat("buyin_avg_ko_map", k)
                for k in parser["buyin_avg_ko_map"]
            }

        service_classes = base.services.copy()
        if parser.has_section("services"):
            service_classes.update(parser["services"])

        return cls(
            hero_name=hero_name,
            final_table_size=final_table_size,
            early_ft_min_players=early_ft_min_players,
            min_ko_blind_level_bb=min_ko_blind_level_bb,
            ko_coeff=ko_coeff,
            buyin_avg_ko_map=buyin_avg_ko_map,
            services=service_classes,
        )


# Путь к конфигурационному файлу по умолчанию
CONFIG_INI_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini"
)

# Глобальный объект конфигурации
app_config = AppConfig.from_ini(CONFIG_INI_PATH)
