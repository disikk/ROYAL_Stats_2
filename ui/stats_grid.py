# -*- coding: utf-8 -*-

"""
Дашборд Hero: отображает ключевые статы в виде карточек и гистограмму мест.
Обновлен для работы с ApplicationService и новой структурой стат.
"""

from PyQt6 import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np # Для работы с массивами в графике
from ui.app_style import format_money, format_percentage, apply_cell_color_by_value # Используем форматтеры
from application_service import ApplicationService # Импортируем сервис

# Вспомогательный виджет для отображения одного стата в виде карточки
class StatCard(QtWidgets.QGroupBox):
    def __init__(self, name: str, value: Any, parent=None, format_func=str, value_color_threshold: Optional[float] = None):
        """
        Виджет-карточка для отображения одного статистического показателя.

        Args:
            name: Название стата.
            value: Значение стата.
            parent: Родительский виджет.
            format_func: Функция для форматирования значения (например, format_money, format_percentage).
            value_color_threshold: Порог для окраски значения (зеленый > порога, красный < порога).
                                   None - без окраски.
        """
        super().__init__(parent)
        self.setTitle(name)
        self.format_func = format_func
        self.value_color_threshold = value_color_threshold

        self.value_label = QtWidgets.QLabel(self.format_func(value))
        font = self.value_label.font()
        font.setPointSize(16) # Увеличиваем размер шрифта значения
        font.setBold(True)
        self.value_label.setFont(font)
        self.value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Применяем цвет текста, если задан порог
        self._apply_value_color(value)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.value_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter) # Центрируем значение
        self.setLayout(layout)
        self.setFixedHeight(80) # Немного увеличиваем высоту для лучшего вида

        # Тень для карточки
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QtGui.QColor(0, 0, 0, 80))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)

    def set_value(self, value: Any):
        """Обновляет значение в карточке и перекрашивает его."""
        self.value_label.setText(self.format_func(value))
        self._apply_value_color(value)

    def _apply_value_color(self, value: Any):
        """Применяет цвет к значению на основе порога."""
        if self.value_color_threshold is not None:
            try:
                val = float(value)
                if val > self.value_color_threshold:
                    self.value_label.setStyleSheet("color: #2ecc71;")  # Зеленый (для положительной прибыли/ROI)
                elif val < self.value_color_threshold:
                    self.value_label.setStyleSheet("color: #e74c3c;")  # Красный (для отрицательной прибыли/ROI)
                else:
                    self.value_label.setStyleSheet("") # Сброс цвета для нуля
            except (ValueError, TypeError):
                self.value_label.setStyleSheet("") # Сброс цвета для нечисловых значений


class StatsGrid(QtWidgets.QWidget):
    """
    Дашборд Hero: все ключевые статы в виде карточек + гистограмма мест на финалке.
    """

    def __init__(self, app_service: ApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service # Используем ApplicationService

        self._init_ui()
        # Данные загружаются при первом отображении вкладки или по сигналу обновления

    def _init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # Заголовок дашборда
        header_layout = QtWidgets.QHBoxLayout()
        self.header_label = QtWidgets.QLabel("Общая статистика игрока")
        self.header_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        # Кнопка обновления с иконкой
        self.refresh_btn = QtWidgets.QPushButton("Обновить")
        self.refresh_btn.setIcon(QtGui.QIcon.fromTheme("view-refresh"))
        self.refresh_btn.setToolTip("Обновить статистику")
        self.refresh_btn.clicked.connect(self.reload)
        header_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(header_layout)

        # --- Карточки статов (QGridLayout в ScrollArea) ---
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)

        self.cards_grid = QtWidgets.QGridLayout()
        self.cards_grid.setSpacing(16)
        self.cards_grid.setContentsMargins(10, 10, 10, 10) # Увеличим отступы
        self.cards_widget = QtWidgets.QWidget()
        self.cards_widget.setLayout(self.cards_grid)
        scroll_layout.addWidget(self.cards_widget)

        # --- Заголовок для гистограммы ---
        chart_header = QtWidgets.QLabel("Распределение занятых мест на финальном столе (1-9)")
        chart_header.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px; margin-bottom: 10px;")
        chart_header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(chart_header)

        # --- Гистограмма распределения мест ---
        self.figure = Figure(figsize=(8, 5)) # Увеличим размер фигуры
        self.canvas = FigureCanvas(self.figure)
        scroll_layout.addWidget(self.canvas)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)

        # Создаем карточки статов (изначально с нулями/прочерками)
        self._create_stat_cards()


    def _create_stat_cards(self):
        """Создает виджеты StatCard для всех отображаемых статистик."""
        # Очищаем существующие карточки из layout
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.stat_cards: Dict[str, StatCard] = {} # Словарь для доступа к карточкам по имени стата

        # Определяем, какие статы отображать и как их форматировать/красить
        # Имена ключей соответствуют полям OverallStats или ключам из compute() плагинов
        stats_to_display = [
            ("Всего турниров", "total_tournaments", str, None),
            ("Всего финалок", "total_final_tables", str, None),
            ("Всего KO", "total_knockouts", str, None),
            ("Среднее место (все)", "avg_finish_place", lambda v: f"{v:.2f}" if v is not None else "-", None),
            ("Среднее место (FT)", "avg_finish_place_ft", lambda v: f"{v:.2f}" if v is not None else "-", None),
            ("Общая прибыль", lambda stats: stats.total_prize - stats.total_buy_in if stats else 0.0, format_money, 0.0),
            ("Общий ROI", lambda stats: (stats.total_prize - stats.total_buy_in) / stats.total_buy_in * 100 if stats and stats.total_buy_in > 0 else 0.0, format_percentage, 0.0),
            ("Среднее KO / турнир", "avg_ko_per_tournament", lambda v: f"{v:.2f}" if v is not None else "-", None),
            ("Процент попадания в ITM", lambda stats: ITMStat().compute([], [], [], stats).get('itm_percent', 0.0) if stats else 0.0, format_percentage, 0.0), # ITM% из плагина
            ("Процент попадания на FT", lambda stats: FinalTableReachStat().compute([], [], [], stats).get('final_table_reach_percent', 0.0) if stats else 0.0, format_percentage, 0.0), # % Reach FT из плагина
            ("Средний стек FT (фишки)", "avg_ft_initial_stack_chips", lambda v: f"{v:.2f}" if v is not None else "-", None),
            ("Средний стек FT (BB)", "avg_ft_initial_stack_bb", lambda v: f"{v:.2f}" if v is not None else "-", None),
            ("KO в ранней финалке (9-6)", "early_ft_ko_count", str, None),
            ("Среднее KO в ранней финалке / турнир", "early_ft_ko_per_tournament", lambda v: f"{v:.2f}" if v is not None else "-", None),
            ("Big KO (x1.5)", "big_ko_x1_5", str, None),
            ("Big KO (x2)", "big_ko_x2", str, None),
            ("Big KO (x10)", "big_ko_x10", str, None),
            ("Big KO (x100)", "big_ko_x100", str, None),
            ("Big KO (x1000)", "big_ko_x1000", str, None),
            ("Big KO (x10000)", "big_ko_x10000", str, None),
        ]

        # Определяем количество колонок в гриде (адаптивно или фиксированно)
        # Давайте сделаем фиксировано, например, 4 колонки.
        cols = 4

        # Создаем карточки и добавляем их в грид
        for i, (name, key_or_lambda, format_func, color_threshold) in enumerate(stats_to_display):
            # Изначальное значение - прочерк или 0
            initial_value = "- " if isinstance(key_or_lambda, str) else 0.0
            card = StatCard(name, initial_value, format_func=format_func, value_color_threshold=color_threshold)
            self.stat_cards[name] = card # Сохраняем ссылку
            self.cards_grid.addWidget(card, i // cols, i % cols)

    def reload(self):
        """
        Обновляет данные в карточках статов и гистограмме.
        """
        # Получаем общую статистику из ApplicationService
        overall_stats = self.app_service.get_overall_stats()
        if not overall_stats:
             logger.warning("Общая статистика недоступна для обновления UI.")
             # Возможно, стоит очистить карточки или показать сообщение об отсутствии данных
             return

        logger.debug("Обновление UI StatsGrid...")

        # Обновляем значения в карточках статов
        # Проходимся по словарю stat_cards и обновляем значения
        for name, card in self.stat_cards.items():
             # Находим соответствующее значение в overall_stats
             # Используем getattr для доступа к полям по строковому имени
             # или вызываем lambda-функцию, если key_or_lambda - это функция
             try:
                 # Находим исходное определение стата, чтобы получить key_or_lambda
                 stat_def = next(
                     (item for item in stats_to_display if item[0] == name),
                     None
                 )
                 if stat_def:
                      key_or_lambda = stat_def[1] # Получаем второй элемент (ключ или lambda)

                      if isinstance(key_or_lambda, str):
                           # Это прямое поле в OverallStats
                           value = getattr(overall_stats, key_or_lambda, None) # Получаем значение по имени поля
                      else:
                           # Это lambda-функция, которая рассчитывает значение
                           value = key_or_lambda(overall_stats) # Вызываем lambda, передавая overall_stats

                      card.set_value(value)
             except Exception as e:
                  logger.error(f"Ошибка при обновлении карточки стата '{name}': {e}")
                  card.set_value("Ошибка") # Показываем ошибку в карточке


        # Обновляем гистограмму распределения мест
        self._update_places_chart()

    def _update_places_chart(self):
        """Обновляет график гистограммы распределения мест."""
        distribution = self.app_service.get_place_distribution()
        overall_stats = self.app_service.get_overall_stats()

        self.figure.clear() # Очищаем предыдущий график

        # Получаем текущие цвета из темы приложения
        # (Можно получить через QPalette или жестко задать для согласованности с QSS)
        # Используем жестко заданные для темной темы, как в app_style.py
        bg_color = '#353535'  # Фон графика
        text_color = '#ffffff'  # Цвет текста
        grid_color = '#555555'  # Цвет сетки
        # bar_color = '#2a82da'  # Основной цвет для столбцов (синий)

        # Настраиваем стиль графика для темной темы
        plt.style.use('dark_background')
        # Устанавливаем фон фигуры явно (может быть переопределен стилем)
        self.figure.patch.set_facecolor(bg_color)


        ax = self.figure.add_subplot(111)
        ax.set_facecolor(bg_color)

        places = list(distribution.keys()) # Места от 1 до 9
        counts = [distribution[p] for p in places] # Количество финишей на каждом месте

        total_final_tables = overall_stats.total_final_tables if overall_stats else sum(counts) # Общее количество финалок для нормализации

        percentages = [(count / total_final_tables * 100) if total_final_tables > 0 else 0.0 for count in counts]
        percentages = [round(p, 2) for p in percentages] # Округляем проценты

        # Создаем градиент цветов для столбцов: первые места - зеленые, последние - красные
        colors = ['#27ae60', '#2ecc71', '#3498db', '#3498db', '#f1c40f',
                 '#f1c40f', '#e67e22', '#e67e22', '#e74c3c'][:len(places)]

        # Строим гистограмму
        bars = ax.bar(places, counts, color=colors)

        # Добавляем количество и проценты над столбцами
        for i, (bar, count, percentage) in enumerate(zip(bars, counts, percentages)):
            height = bar.get_height()
            # Отображаем count только если он > 0
            if count > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5, # Небольшой отступ над столбцом
                        f'{count}', # Отображаем количество
                        ha='center', va='bottom', color=text_color, fontweight='bold', fontsize=10)

            # Отображаем процент только если он > 0
            if percentage > 0:
                 ax.text(bar.get_x() + bar.get_width()/2., height + (overall_stats.total_tournaments * 0.01), # Немного выше, чем count
                         f'{percentage:.1f}%', # Отображаем процент с одним знаком после запятой
                         ha='center', va='bottom', color=text_color, fontsize=9)


        ax.set_title(f"Распределение занятых мест на финальном столе",
                     color=text_color, fontsize=14, pad=20) # Увеличиваем отступ заголовка
        ax.set_xlabel("Место", color=text_color, fontsize=12)
        ax.set_ylabel("Количество финалок", color=text_color, fontsize=12) # Подпись оси Y
        ax.set_xticks(places) # Устанавливаем метки только для имеющихся мест
        ax.tick_params(colors=text_color) # Цвет меток на осях

        # Настраиваем внешний вид сетки
        ax.grid(True, linestyle='--', alpha=0.3, color=grid_color)

        # Устанавливаем пределы оси Y так, чтобы проценты не выходили за график
        # Находим максимальное значение количества + небольшой запас
        max_count = max(counts) if counts else 0
        # Определяем примерную высоту текста процента (зависит от размера шрифта и dpi)
        # Это сложно сделать точно без рендеринга, используем эвристику или относительный отступ
        # Зададим верхний предел Y как максимум count + 10-15% от максимума для текста
        ax.set_ylim(0, max_count * 1.2) # Добавляем 20% сверху для текста

        # Добавляем общее количество финалок в заголовок или подпись
        ax.text(0.98, 0.98, f"Всего финалок: {total_final_tables}",
                verticalalignment='top', horizontalalignment='right',
                transform=ax.transAxes,
                color=text_color, fontsize=10)


        # Удаляем рамку графика
        for spine in ax.spines.values():
            spine.set_visible(False)

        self.figure.tight_layout() # Автоматически корректируем расположение элементов
        self.canvas.draw() # Прорисовываем график