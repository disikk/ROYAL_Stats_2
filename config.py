# -*- coding: utf-8 -*-

import os
import json

# ==== Базовые параметры приложения ====
HERO_NAME = "Hero"
APP_VERSION = "0.1.0" # Начальная версия для новой разработки

# Текущий путь к БД (по умолчанию, можно менять в интерфейсе)
# Все базы храним в подпапке `databases` для удобства.
DEFAULT_DB_DIR = "databases"
# Создаём каталог, если его ещё нет
os.makedirs(DEFAULT_DB_DIR, exist_ok=True)

# Файл для хранения конфигурации (например, путь к последней БД)
CONFIG_FILE = "config.json"

# Устанавливаем путь по умолчанию внутри каталога
DEFAULT_DB_NAME = "royal_stats.db"
DB_PATH = os.path.join(DEFAULT_DB_DIR, DEFAULT_DB_NAME)

# Последняя открытая БД
LAST_DB_PATH = DB_PATH # Значение по умолчанию

# ==== Настройки игры ====
# Параметры для определения финального стола и "зоны KO" в HH
# Финальный стол определяется по размеру стола 9-max
FINAL_TABLE_SIZE = 9
# Зона KO начинается с первой раздачи на 9-max столе с блайндами >= 50/100
MIN_KO_BLIND_LEVEL_BB = 100 # BB >= 100

# ==== Интерфейс / GUI ====
APP_TITLE = "Royal Stats — Hero-only"
THEME = "dark"         # dark / light
LANG = "ru"            # ru / en
UI_SCALE = 1.0         # Масштаб интерфейса
CHART_TYPE = "bar"     # bar / pie / line (по желанию)

# ==== Прочее ====
DEBUG = True # В режиме отладки может выводиться больше логов

# ==== Функции для работы с конфигом ====

def load_config():
    """Загружает настройки из файла."""
    global LAST_DB_PATH
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                LAST_DB_PATH = config_data.get("last_db_path", DB_PATH)
                # Убедимся, что папка для БД существует, если путь загружен
                db_dir = os.path.dirname(LAST_DB_PATH)
                if not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
    except Exception as e:
        print(f"Ошибка при загрузке конфига: {e}")

def save_config():
    """Сохраняет настройки в файл."""
    try:
        config_data = {
            "last_db_path": LAST_DB_PATH
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Ошибка при сохранении конфига: {e}")

def set_db_path(path: str):
    """Устанавливает текущий путь к БД и сохраняет его."""
    global DB_PATH
    global LAST_DB_PATH
    DB_PATH = path
    LAST_DB_PATH = path
    save_config()

# Загружаем конфиг при старте модуля
load_config()

# Присваиваем начальное значение DB_PATH из загруженного конфига
DB_PATH = LAST_DB_PATH