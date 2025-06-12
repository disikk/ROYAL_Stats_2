# План внедрения EV-движка в Royal Stats

## Общее описание

EV (Expected Value) движок будет рассчитывать математическое ожидание результатов игрока в покерных турнирах. Основные метрики:
- **EV BB/100** - математическое ожидание в больших блайндах на 100 рук
- **EV Chips** - математическое ожидание в фишках за турнир
- **EV $/tournament** - математическое ожидание прибыли за турнир с учетом ICM

## Фаза 1: Подготовка инфраструктуры

### 1.1 Расширение схемы базы данных

#### Новые таблицы:
1. **hand_details** - детальная информация о раздачах
   - hero_cards (карты Hero)
   - board_cards (общие карты по улицам)
   - pot_sizes (размеры банка по улицам)
   - showdown_hands (показанные руки)

2. **hand_actions** - все действия в раздаче
   - street (улица)
   - action_order (порядок действия)
   - player_name
   - action_type (bet/call/raise/fold/check/all-in)
   - amount
   - pot_after
   - player_stack_after

3. **ev_calculations** - результаты EV расчетов
   - preflop/flop/turn equity
   - ev_chips/ev_bb
   - actual_chips/actual_bb
   - all_in_ev (если был all-in)
   - icm_ev (для финальных столов)

4. **tournament_payouts** - структура выплат турниров
   - place и payout для каждого места
   - необходима для ICM расчетов

5. **ev_stats** - агрегированная EV статистика
   - ev_bb_per_100
   - all_in_ev_diff
   - ev_roi vs actual_roi

#### Изменения существующих таблиц:
- Добавить в **hero_final_table_hands**: ev_chips, ev_bb, all_in_occurred

### 1.2 Модификация парсера hand history

#### Дополнительные данные для извлечения:
1. **Карты**
   - Hero hole cards (из строки "Dealt to Hero [Ah Ks]")
   - Board cards (FLOP, TURN, RIVER)
   - Showdown hands (из SUMMARY секции)

2. **Детальные действия**
   - Все действия с точными размерами
   - Состояние банка после каждого действия
   - Стеки игроков после действий

3. **Информация об all-in**
   - Момент all-in (улица и размер банка)
   - Участники all-in ситуации
   - Side pots структура

#### Новые регулярные выражения:
```python
RE_HERO_CARDS = re.compile(r'Dealt to ([^[]+) \[([^\]]+)\]')
RE_FLOP = re.compile(r'\*\*\* FLOP \*\*\* \[([^\]]+)\]')
RE_TURN = re.compile(r'\*\*\* TURN \*\*\* \[[^\]]+\] \[([^\]]+)\]')
RE_RIVER = re.compile(r'\*\*\* RIVER \*\*\* \[[^\]]+\] \[([^\]]+)\]')
RE_SHOWDOWN = re.compile(r'^([^:]+): shows \[([^\]]+)\]')
```

## Фаза 2: Core EV Engine

### 2.1 Модуль расчета Equity

**Класс: EquityCalculator**
- Метод: calculate_equity(hero_cards, villain_cards, board, dead_cards)
- Использование Monte Carlo симуляции или точных расчетов
- Кеширование результатов для оптимизации

**Библиотеки:**
- poker (pip install poker) - для работы с картами
- pokereval или pyholdthem - для расчета equity

### 2.2 Модуль расчета EV

**Класс: EVCalculator**

Методы:
1. **calculate_hand_ev(hand_data)**
   - Расчет EV для конкретной раздачи
   - Учет размеров банка и действий
   - Обработка all-in ситуаций

2. **calculate_all_in_ev(hand_data)**
   - Специальный расчет для all-in
   - Определение equity в момент all-in
   - Расчет EV с учетом side pots

3. **calculate_session_ev(session_id)**
   - Агрегация EV по сессии
   - Расчет EV BB/100

### 2.3 Модуль ICM калькулятора

**Класс: ICMCalculator**

Методы:
1. **calculate_icm_equity(stacks, payouts)**
   - Расчет ICM equity для текущих стеков
   - Использование алгоритма Malmuth-Harville

2. **calculate_tournament_ev(tournament_data)**
   - Расчет EV в $ с учетом ICM
   - Сравнение с фактическими результатами

**Особенности:**
- Кеширование расчетов для типовых ситуаций
- Поддержка PKO (Progressive Knockout) турниров
- Учет bounty в EV расчетах

## Фаза 3: Интеграция с существующей архитектурой

### 3.1 Новые сервисы

**EVService** (services/ev_service.py)
- Координация всех EV расчетов
- Интеграция с EventBus
- Кеширование результатов

**Методы:**
- process_hand_for_ev(hand_data)
- update_tournament_ev(tournament_id)
- calculate_aggregated_stats(session_id)

### 3.2 Новые репозитории

1. **HandDetailsRepository**
   - CRUD для hand_details
   - Bulk insert для действий

2. **EVCalculationsRepository**
   - Сохранение результатов расчетов
   - Оптимизированные запросы для статистики

3. **TournamentPayoutsRepository**
   - Управление структурами выплат
   - Автоматическое определение из summary

### 3.3 Новые модели

1. **HandDetails** (models/hand_details.py)
2. **HandAction** (models/hand_action.py)
3. **EVCalculation** (models/ev_calculation.py)
4. **TournamentPayout** (models/tournament_payout.py)
5. **EVStats** (models/ev_stats.py)

### 3.4 События

Новые события для EventBus:
- HandParsedEvent (с полными данными)
- EVCalculatedEvent
- ICMUpdatedEvent

## Фаза 4: Оптимизация производительности

### 4.1 Стратегии оптимизации

1. **Batch processing**
   - Обработка раздач пакетами
   - Bulk insert в БД

2. **Параллельные вычисления**
   - Использование multiprocessing для equity расчетов
   - Thread pool для независимых расчетов

3. **Кеширование**
   - LRU cache для equity расчетов
   - Предрасчет типовых ситуаций

4. **Инкрементальные обновления**
   - Пересчет только измененных данных
   - Использование триггеров БД

### 4.2 Индексы БД

Критические индексы:
- hand_details(tournament_id, hand_id)
- hand_actions(tournament_id, hand_id, action_order)
- ev_calculations(tournament_id, all_in_ev_chips)

## Фаза 5: Валидация и тестирование

### 5.1 Unit тесты

1. **test_equity_calculator.py**
   - Тесты точности расчета equity
   - Граничные случаи

2. **test_ev_calculator.py**
   - Проверка расчета EV
   - All-in ситуации

3. **test_icm_calculator.py**
   - Валидация ICM расчетов
   - Сравнение с эталонными значениями

### 5.2 Integration тесты

1. **test_ev_service_integration.py**
   - Полный цикл обработки
   - Проверка событий

2. **test_parser_ev_integration.py**
   - Извлечение данных для EV
   - Корректность парсинга карт

### 5.3 Performance тесты

- Бенчмарки для больших объемов данных
- Профилирование узких мест
- Оптимизация запросов

## Фаза 6: Статистические модули

### 6.1 Новые stat плагины

1. **EVDifference** (stats/ev_difference.py)
   - Разница между EV и actual
   - Показатель "удачливости"

2. **AllInEVAdjusted** (stats/all_in_ev_adjusted.py)
   - Скорректированные результаты all-in

3. **ICMPressure** (stats/icm_pressure.py)
   - Анализ решений с учетом ICM

4. **EVByPosition** (stats/ev_by_position.py)
   - EV в зависимости от позиции за столом

### 6.2 Модификация существующих

- ROI → добавить EV ROI
- KO stats → добавить EV от knockouts

## Временные оценки

### Фаза 1: 2-3 дня
- Схема БД: 0.5 дня
- Модификация парсера: 2 дня

### Фаза 2: 3-4 дня
- Equity calculator: 1 день
- EV calculator: 1.5 дня
- ICM calculator: 1.5 дня

### Фаза 3: 2-3 дня
- Сервисы и репозитории: 1.5 дня
- Модели и события: 1 день

### Фаза 4: 1-2 дня
- Оптимизация: 1.5 дня

### Фаза 5: 2 дня
- Тестирование: 2 дня

### Фаза 6: 1-2 дня
- Новые стат модули: 1.5 дня

**Итого: 11-16 дней**

## Риски и митигация

1. **Производительность расчетов**
   - Риск: Медленные equity расчеты
   - Митигация: Использование C++ библиотек, кеширование

2. **Объем данных**
   - Риск: Большой размер БД
   - Митигация: Архивирование старых данных, индексы

3. **Точность расчетов**
   - Риск: Ошибки в equity/ICM
   - Митигация: Extensive testing, валидация с эталонами

4. **Обратная совместимость**
   - Риск: Нарушение работы с существующими БД
   - Митигация: Миграции, версионирование схемы

## Зависимости

### Python пакеты:
- poker>=0.30.0
- numpy>=1.20.0
- numba>=0.50.0 (для оптимизации)
- scipy>=1.7.0 (для статистических расчетов)

### Внешние библиотеки:
- pyholdthem или pokereval (C++ binding для быстрых расчетов)

## Определение успеха

1. Точность equity расчетов > 99.9%
2. Производительность: < 100ms на раздачу
3. EV BB/100 расчитывается корректно
4. ICM расчеты соответствуют стандартам
5. Все тесты проходят
6. Нет регрессии в существующем функционале