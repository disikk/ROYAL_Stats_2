# -*- coding: utf-8 -*-

"""
Модуль, содержащий схемы таблиц базы данных для ROYAL_Stats (Hero-only).
"""

# SQL-запросы для создания таблиц

# Таблица для хранения информации о сессиях импорта
CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    session_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tournaments_count INTEGER DEFAULT 0,
    knockouts_count INTEGER DEFAULT 0,
    avg_finish_place REAL DEFAULT 0,
    total_prize REAL DEFAULT 0,
    total_buy_in REAL DEFAULT 0
)
"""

# Таблица для хранения информации о турнирах Hero
CREATE_TOURNAMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id TEXT UNIQUE NOT NULL,
    tournament_name TEXT,
    start_time TEXT,
    buyin REAL,
    payout REAL,
    finish_place INTEGER,
    ko_count REAL DEFAULT 0,
    session_id TEXT,
    has_ts BOOLEAN DEFAULT 0,
    has_hh BOOLEAN DEFAULT 0,
    reached_final_table BOOLEAN DEFAULT 0,
    final_table_initial_stack_chips REAL,
    final_table_initial_stack_bb REAL,
    final_table_start_players INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
)
"""

# НОВАЯ Таблица для хранения информации о руках финального стола Hero
CREATE_HERO_FINAL_TABLE_HANDS_TABLE = """
CREATE TABLE IF NOT EXISTS hero_final_table_hands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id TEXT NOT NULL,
    hand_id TEXT NOT NULL, -- Уникальный ID раздачи
    hand_number INTEGER, -- Порядковый номер раздачи в турнире
    table_size INTEGER, -- Размер стола в этой раздаче
    bb REAL, -- Размер большого блайнда в этой раздаче
    hero_stack REAL, -- Стек Hero в начале этой раздачи
    players_count INTEGER, -- Фактическое число игроков за столом
    hero_ko_this_hand REAL DEFAULT 0, -- KO, сделанные Hero в этой раздаче
    pre_ft_ko REAL DEFAULT 0, -- KO, сделанные в последней 5-max раздаче
    hero_ko_attempts INTEGER DEFAULT 0, -- Количество попыток выбить соперников в этой раздаче
    session_id TEXT,
    is_early_final BOOLEAN DEFAULT 0, -- Флаг для стадии 9-6 игроков
    UNIQUE (tournament_id, hand_id), -- Раздача уникальна в рамках турнира
    FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
)
"""

# Таблица для хранения общей статистики Hero (одна строка)
CREATE_OVERALL_STATS_TABLE = """
CREATE TABLE IF NOT EXISTS overall_stats (
    id INTEGER PRIMARY KEY CHECK (id = 1), -- Гарантируем, что всегда одна строка с id=1
    total_tournaments INTEGER DEFAULT 0,
    total_final_tables INTEGER DEFAULT 0,
    total_knockouts REAL DEFAULT 0,
    avg_finish_place REAL DEFAULT 0, -- Среднее место по всем турнирам (включая не финалку)
    avg_finish_place_ft REAL DEFAULT 0, -- Среднее место только на финалке (1-9)
    avg_finish_place_no_ft REAL DEFAULT 0,
    total_prize REAL DEFAULT 0,
    total_buy_in REAL DEFAULT 0,
    avg_ko_per_tournament REAL DEFAULT 0,
    avg_ft_initial_stack_chips REAL DEFAULT 0,
    avg_ft_initial_stack_bb REAL DEFAULT 0,
    big_ko_x1_5 INTEGER DEFAULT 0,
    big_ko_x2 INTEGER DEFAULT 0,
    big_ko_x10 INTEGER DEFAULT 0,
    big_ko_x100 INTEGER DEFAULT 0,
    big_ko_x1000 INTEGER DEFAULT 0,
    big_ko_x10000 INTEGER DEFAULT 0,
    early_ft_ko_count REAL DEFAULT 0,
    early_ft_ko_per_tournament REAL DEFAULT 0,
    early_ft_bust_count INTEGER DEFAULT 0,
    early_ft_bust_per_tournament REAL DEFAULT 0,
    pre_ft_ko_count REAL DEFAULT 0,
    pre_ft_chipev REAL DEFAULT 0,
    incomplete_ft_count INTEGER DEFAULT 0,
    incomplete_ft_percent INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# Таблица для хранения распределения мест на финальном столе
CREATE_PLACES_DISTRIBUTION_TABLE = """
CREATE TABLE IF NOT EXISTS places_distribution (
    place INTEGER PRIMARY KEY, -- Место (1-9)
    count INTEGER DEFAULT 0 -- Количество финишей на этом месте
)
"""

# Таблицы для управления стат-модулями (если понадобится расширение)
CREATE_STAT_MODULES_TABLE = """
CREATE TABLE IF NOT EXISTS stat_modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    display_name TEXT,
    enabled BOOLEAN DEFAULT 1,
    position INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_MODULE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS module_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER,
    key TEXT,
    value TEXT,
    FOREIGN KEY (module_id) REFERENCES stat_modules(id),
    UNIQUE(module_id, key)
)
"""

# Индексы для оптимизации производительности
CREATE_INDEXES = [
    # Базовые индексы
    "CREATE INDEX IF NOT EXISTS idx_tournaments_session ON tournaments(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_tournaments_buyin ON tournaments(buyin)",
    "CREATE INDEX IF NOT EXISTS idx_tournaments_reached_ft ON tournaments(reached_final_table)",
    "CREATE INDEX IF NOT EXISTS idx_tournaments_finish_place ON tournaments(finish_place)",
    "CREATE INDEX IF NOT EXISTS idx_ft_hands_tournament ON hero_final_table_hands(tournament_id)",
    "CREATE INDEX IF NOT EXISTS idx_ft_hands_session ON hero_final_table_hands(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_ft_hands_is_early ON hero_final_table_hands(is_early_final)",
    "CREATE INDEX IF NOT EXISTS idx_ft_hands_ko ON hero_final_table_hands(hero_ko_this_hand)",
    
    # Составные индексы для оптимизации статистики
    "CREATE INDEX IF NOT EXISTS idx_tournaments_ft_place ON tournaments(reached_final_table, finish_place)",
    "CREATE INDEX IF NOT EXISTS idx_tournaments_ft_stacks ON tournaments(reached_final_table, final_table_initial_stack_chips, final_table_initial_stack_bb)",
    "CREATE INDEX IF NOT EXISTS idx_tournaments_session_place ON tournaments(session_id, finish_place)",
    "CREATE INDEX IF NOT EXISTS idx_tournaments_buyin_payout ON tournaments(buyin, payout)",
    "CREATE INDEX IF NOT EXISTS idx_ft_hands_early_ko ON hero_final_table_hands(is_early_final, hero_ko_this_hand)",
    "CREATE INDEX IF NOT EXISTS idx_tournaments_id_ko ON tournaments(tournament_id, ko_count)",
    
    # Индексы для ускорения агрегатных запросов
    "CREATE INDEX IF NOT EXISTS idx_tournaments_stats ON tournaments(reached_final_table, finish_place, buyin, payout) WHERE finish_place IS NOT NULL",
]

# Список всех SQL-запросов для создания таблиц
CREATE_TABLES_QUERIES = [
    CREATE_SESSIONS_TABLE,
    CREATE_TOURNAMENTS_TABLE,
    CREATE_HERO_FINAL_TABLE_HANDS_TABLE,
    CREATE_OVERALL_STATS_TABLE,
    CREATE_PLACES_DISTRIBUTION_TABLE,
    CREATE_STAT_MODULES_TABLE,
    CREATE_MODULE_SETTINGS_TABLE,
] + CREATE_INDEXES  # Добавляем индексы к списку создания

# Запрос для вставки/игнорирования начальной строки в overall_stats
INSERT_INITIAL_OVERALL_STATS = """
INSERT OR IGNORE INTO overall_stats (id) VALUES (1)
"""

# Запрос для вставки/игнорирования начальных записей в places_distribution
INSERT_INITIAL_PLACES_DISTRIBUTION = """
INSERT OR IGNORE INTO places_distribution (place, count) VALUES (?, 0)
"""

# Инициализационные запросы (выполняются при создании новой БД)
INITIALIZATION_QUERIES = [
    INSERT_INITIAL_OVERALL_STATS
] + [INSERT_INITIAL_PLACES_DISTRIBUTION.replace('?', str(i)) for i in range(1, 10)]

# SQL-запросы для получения данных (примеры, полный список будет в репозиториях)

# Получение общей статистики
GET_OVERALL_STATS = """
SELECT * FROM overall_stats WHERE id = 1
"""

# Получение распределения мест на финалке
GET_PLACES_DISTRIBUTION = """
SELECT place, count FROM places_distribution ORDER BY place
"""

# Получение всех турниров (опционально по сессии или с фильтром)
GET_TOURNAMENTS = """
SELECT * FROM tournaments
"""

# Получение всех финальных рук Hero (опционально по турниру или сессии)
GET_HERO_FINAL_TABLE_HANDS = """
SELECT * FROM hero_final_table_hands
"""

# SQL-запросы для обновления данных (примеры)

# Обновление общей статистики (пример)
UPDATE_OVERALL_STATS = """
UPDATE overall_stats SET
    total_tournaments = ?,
    total_final_tables = ?,
    total_knockouts = ?,
    avg_finish_place = ?,
    avg_finish_place_ft = ?,
    avg_finish_place_no_ft = ?,
    total_prize = ?,
    total_buy_in = ?,
    avg_ko_per_tournament = ?,
    avg_ft_initial_stack_chips = ?,
    avg_ft_initial_stack_bb = ?,
    big_ko_x1_5 = ?,
    big_ko_x2 = ?,
    big_ko_x10 = ?,
    big_ko_x100 = ?,
    big_ko_x1000 = ?,
    big_ko_x10000 = ?,
    early_ft_ko_count = ?,
    early_ft_ko_per_tournament = ?,
    early_ft_bust_count = ?,
    early_ft_bust_per_tournament = ?,
    last_updated = CURRENT_TIMESTAMP
WHERE id = 1
"""

# Обновление количества финишей на определенном месте
INCREMENT_PLACE_COUNT = """
UPDATE places_distribution SET count = count + 1 WHERE place = ?
"""