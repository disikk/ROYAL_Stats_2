import os

# ==== Базовые параметры приложения ====
HERO_NAME = "Hero"
APP_VERSION = "16.05.2025"

# Текущий путь к БД (по умолчанию, можно менять в интерфейсе)
# Все базы храним в подпапке `databases` для удобства.
DEFAULT_DB_DIR = "databases"
# Создаём каталог, если его ещё нет
os.makedirs(DEFAULT_DB_DIR, exist_ok=True)

# Устанавливаем путь по умолчанию внутри каталога
DB_PATH = os.path.join(DEFAULT_DB_DIR, "royal_stats.db")

# Список недавних баз (может использоваться для быстрого переключения в GUI)
RECENT_DATABASES = [
    DB_PATH,
    # Добавлять новые файлы через GUI или вручную
]

# Папки для файлов (hand history, summaries, tournaments и пр.)
TOURNAMENTS_DIR = "./tournaments"
HH_DIR = "./handhistories"
SUMMARY_DIR = "./summaries"

# ==== Настройки финального стола для парсера ====
MIN_FINAL_TABLE_PLAYERS = 6
MIN_FINAL_TABLE_BLIND = 50

# ==== Интерфейс / GUI ====
APP_TITLE = "Royal Stats — Hero-only"
THEME = "dark"         # dark / light
LANG = "ru"            # ru / en
UI_SCALE = 1.0         # Масштаб интерфейса
CHART_TYPE = "bar"     # bar / pie / line (по желанию)

# ==== Прочее ====
DEBUG = False

# ==== Функции для динамического обновления настроек ====
def set_db_path(path: str):
    global DB_PATH
    DB_PATH = path
    # Можно также дополнять RECENT_DATABASES, если файл новый
    if path not in RECENT_DATABASES:
        RECENT_DATABASES.insert(0, path)
        if len(RECENT_DATABASES) > 10:
            RECENT_DATABASES.pop()

def set_theme(theme: str):
    global THEME
    THEME = theme

def set_lang(lang: str):
    global LANG
    LANG = lang

def set_ui_scale(scale: float):
    global UI_SCALE
    UI_SCALE = scale

def set_chart_type(chart_type: str):
    global CHART_TYPE
    CHART_TYPE = chart_type

# Можно добавить сохранение этих настроек в файл, если понадобится "персистентность"
