# -*- coding: utf-8 -*-

import os

# Абсолютный путь до директории проекта, где расположен этот файл
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
"""Application configuration for ROYAL Stats."""


# ==== Базовые параметры приложения ====
HERO_NAME = "Hero"
APP_VERSION = "0.1.0" # Начальная версия для новой разработки

# Текущий путь к БД (по умолчанию, можно менять в интерфейсе)
# Все базы храним в подпапке `databases` для удобства.
DEFAULT_DB_DIR = os.path.join(BASE_DIR, "databases")
# Создаём каталог, если его ещё нет
os.makedirs(DEFAULT_DB_DIR, exist_ok=True)

# Устанавливаем путь по умолчанию внутри каталога
DEFAULT_DB_NAME = "royal_stats.db"
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, DEFAULT_DB_NAME)

# Файл для хранения последней выбранной БД
LAST_DB_FILE = os.path.join(DEFAULT_DB_DIR, "last_db_path.txt")
# Файл для хранения кеша статистики по базам данных
STATS_CACHE_FILE = os.path.abspath(
    os.path.join(DEFAULT_DB_DIR, "stats_cache.json")
)

# Последняя открытая БД
if os.path.exists(LAST_DB_FILE):
    try:
        with open(LAST_DB_FILE, "r", encoding="utf-8") as f:
            LAST_DB_PATH = f.read().strip() or DEFAULT_DB_PATH
    except Exception:
        LAST_DB_PATH = DEFAULT_DB_PATH
else:
    LAST_DB_PATH = DEFAULT_DB_PATH

# Начальный путь к активной базе данных
DB_PATH = LAST_DB_PATH

# ==== Настройки игры ====
# Параметры для определения финального стола и "зоны KO" в HH
# Финальный стол определяется по размеру стола 9-max
FINAL_TABLE_SIZE = 9
# Количество игроков, до которого длится "ранняя" стадия финалки
EARLY_FT_MIN_PLAYERS = 6
# Зона KO начинается с первой раздачи на 9-max столе
MIN_KO_BLIND_LEVEL_BB = 0

# Коэффициенты вероятности получения KO в последней 5-max раздаче перед стартом
# финального стола, если финальный стол начинается с неполным составом.
# Ключ — количество участников в первой раздаче финалки, значение — множитель.
KO_COEFF = {
    8: 0.40,
    7: 0.50,
    6: 0.60,
    5: 0.60,
    4: 0.65,
    3: 0.70,
    2: 0.70,
}

# Соответствие байинов и среднего размера нокаута
# Формат: байин (в долларах) -> средний размер нокаута (в долларах)
BUYIN_AVG_KO_MAP = {
    0.25: 0.23,
    1.0: 0.93,
    3.0: 2.79,
    10.0: 9.28,
    25.0: 23.18,
}

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

