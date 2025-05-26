# -*- coding: utf-8 -*-

import os
"""Application configuration for ROYAL Stats."""


# ==== Базовые параметры приложения ====
HERO_NAME = "Hero"
APP_VERSION = "0.1.0" # Начальная версия для новой разработки

# Текущий путь к БД (по умолчанию, можно менять в интерфейсе)
# Все базы храним в подпапке `databases` для удобства.
DEFAULT_DB_DIR = "databases"
# Создаём каталог, если его ещё нет
os.makedirs(DEFAULT_DB_DIR, exist_ok=True)

# Устанавливаем путь по умолчанию внутри каталога
DEFAULT_DB_NAME = "royal_stats.db"
DB_PATH = os.path.join(DEFAULT_DB_DIR, DEFAULT_DB_NAME)

# Файл для хранения последней выбранной БД
LAST_DB_FILE = os.path.join(DEFAULT_DB_DIR, "last_db_path.txt")

# Последняя открытая БД
if os.path.exists(LAST_DB_FILE):
    try:
        with open(LAST_DB_FILE, "r", encoding="utf-8") as f:
            LAST_DB_PATH = f.read().strip() or DB_PATH
    except Exception:
        LAST_DB_PATH = DB_PATH
else:
    LAST_DB_PATH = DB_PATH

# ==== Настройки игры ====
# Параметры для определения финального стола и "зоны KO" в HH
# Финальный стол определяется по размеру стола 9-max
FINAL_TABLE_SIZE = 9
# Зона KO начинается с первой раздачи на 9-max столе с блайндами >= 50/100
MIN_KO_BLIND_LEVEL_BB = 100 # BB >= 100

# ==== Интерфейс / GUI ====
APP_TITLE = "MBR Stats by disikk"
THEME = "dark"         # dark / light
LANG = "ru"            # ru / en
UI_SCALE = 1.0         # Масштаб интерфейса
CHART_TYPE = "bar"     # bar / pie / line (по желанию)

# ==== Прочее ====
DEBUG = False # В режиме отладки может выводиться больше логов


def set_db_path(path: str) -> None:
    """Sets the current database path."""
    global DB_PATH, LAST_DB_PATH
    DB_PATH = path
    LAST_DB_PATH = path
    try:
        with open(LAST_DB_FILE, "w", encoding="utf-8") as f:
            f.write(path)
    except Exception:
        pass

