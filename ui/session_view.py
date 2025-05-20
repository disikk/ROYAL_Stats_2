# -*- coding: utf-8 -*-

"""
Таблица всех сессий Hero: список турниров, общий бай-ин, выплаты, KO, статы сессии.
Обновлен для работы с ApplicationService и отображения статистики сессий.
"""

from PyQt6 import QtWidgets, QtGui, QtCore
from typing import List, Optional
from ui.app_style import setup_table_widget, format_money, apply_cell_color_by_value, format_percentage
from application_service import ApplicationService # Импортируем сервис
from ui.stats_grid import StatCard
from models import Session
import config # Для доступа к настройкам

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np # Для работы с графиками

import logging
logger = logging.getLogger('ROYAL_Stats.SessionView')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)


class SessionView(QtWidgets.QWidget):
    """
    Представление игровых сессий Hero.
    Показывает список сессий и статистику по выбранной сессии, включая гистограмму мест на финалке.
    """

    def __init__(self, app_service: ApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service # Используем ApplicationService
        self._selected_session_id: Optional[str] = None # ID выбранной сессии

        self._init_ui()
        # Данные загружаются при первом отображении вкладки или по сигналу обновления

    def _init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # Верхний блок с заголовком и поиском
        header_layout = QtWidgets.QHBoxLayout()

        # Заголовок
        self.title_label = QtWidgets.QLabel("Игровые сессии")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Поле поиска
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Поиск по сессиям...")
        self.search_field.textChanged.connect(self.filter_table)
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(QtWidgets.QLabel("Поиск:"))
        search_layout.addWidget(self.search_field)
        header_layout.addLayout(search_layout)

        # Кнопка обновления
        self.refresh_btn = QtWidgets.QPushButton("Обновить")
        self.refresh_btn.setIcon(QtGui.QIcon.fromTheme("view-refresh"))
        self.refresh_btn.setToolTip("Обновить данные сессий")
        self.refresh_btn.clicked.connect(self.reload)
        header_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(header_layout)

        # Разделитель на две части: слева таблица, справа статистика и графики выбранной сессии
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # Левая часть: Таблица сессий
        table_widget = QtWidgets.QWidget()
        table_layout = QtWidgets.QVBoxLayout(table_widget)

        # Таблица сессий
        self.table = QtWidgets.QTableWidget(0, 7) # ID, Сессия, Турниры, Бай-ин, Выплата, KO, Прибыль
        self.table.setHorizontalHeaderLabels(["ID", "Сессия", "Турниры", "Бай-ин", "Выплата", "KO", "Прибыль"]) # Дата будет в имени сессии или tooltip
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)

        # Применяем улучшения к таблице
        setup_table_widget(self.table)

        # Скрываем колонку ID
        self.table.hideColumn(0)

        # Подключаем сигнал выбора строки для отображения деталей сессии
        self.table.itemSelectionChanged.connect(self._session_selected)

        table_layout.addWidget(self.table)
        table_layout.setContentsMargins(0, 0, 0, 0) # Убираем отступы для корректного отображения в сплиттере

        # Правая часть: Статистика и графики выбранной сессии
        details_widget = QtWidgets.QScrollArea() # Используем ScrollArea для прокрутки деталей
        details_widget.setWidgetResizable(True)
        details_content = QtWidgets.QWidget()
        self.details_layout = QtWidgets.QVBoxLayout(details_content)
        details_widget.setWidget(details_content)


        # Статистические карточки для выбранной сессии (динамическое создание)
        self.session_stat_cards_widget = QtWidgets.QWidget()
        self.session_stat_cards_layout = QtWidgets.QGridLayout(self.session_stat_cards_widget)
        self.session_stat_cards_layout.setSpacing(10)
        self.details_layout.addWidget(self.session_stat_cards_widget)

        # Заголовок для графиков
        graph_title = QtWidgets.QLabel("Графики сессии")
        graph_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        graph_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.details_layout.addWidget(graph_title)

        # График 1 (например, динамика прибыли по турнирам в сессии - опционально, требует данных по турнирам в сессии)
        # Пока оставим место для графиков, но рисовать будем только гистограмму мест

        # Гистограмма распределения мест на финалке для выбранной сессии
        chart_header = QtWidgets.QLabel("Распределение занятых мест на финальном столе (1-9) в сессии")
        chart_header.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px; margin-bottom: 5px;")
        chart_header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.details_layout.addWidget(chart_header)

        self.ft_places_figure = Figure(figsize=(8, 5))
        self.ft_places_canvas = FigureCanvas(self.ft_places_figure)
        self.details_layout.addWidget(self.ft_places_canvas)


        # Добавляем виджеты в разделитель
        splitter.addWidget(table_widget)
        splitter.addWidget(details_widget)

        # Устанавливаем начальное соотношение размеров
        splitter.setSizes([400, 800]) # Таблица слева уже, детали справа шире

        main_layout.addWidget(splitter)
        main_layout.setContentsMargins(0, 0, 0, 0) # Убираем отступы для основного layout


    def reload(self):
        """
        Загружает данные сессий из ApplicationService и обновляет таблицу.
        """
        logger.debug("Перезагрузка SessionView...")
        sessions = self.app_service.get_all_sessions()

        self._update_sessions_table(sessions)

        # Очищаем панель деталей, пока сессия не выбрана
        self._clear_session_details()

        # Применяем текущий поисковый фильтр
        self.filter_table()
        logger.debug("Перезагрузка SessionView завершена.")


    def _update_sessions_table(self, sessions: List[Session]):
        """Обновляет данные в таблице сессий."""
        self.table.setRowCount(0)
        if not sessions:
            logger.debug("Нет данных по сессиям для отображения.")
            return

        for s in sessions:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ID (скрытая колонка)
            id_item = QtWidgets.QTableWidgetItem(str(s.id))
            self.table.setItem(row, 0, id_item)

            # Сессия (название/идентификатор)
            session_name_item = QtWidgets.QTableWidgetItem(s.session_name)
            # Добавляем ID сессии и дату создания в тултип
            tooltip_text = f"ID сессии: {s.session_id}\nСоздана: {s.created_at}"
            session_name_item.setToolTip(tooltip_text)
            self.table.setItem(row, 1, session_name_item)

            # Турниры (количество)
            tournaments_count_item = QtWidgets.QTableWidgetItem(str(s.tournaments_count))
            tournaments_count_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, tournaments_count_item)

            # Бай-ин (общий)
            buyin_item = QtWidgets.QTableWidgetItem(format_money(s.total_buy_in))
            buyin_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, buyin_item)

            # Выплата (общая)
            payout_item = QtWidgets.QTableWidgetItem(format_money(s.total_prize))
            payout_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(payout_item, s.total_prize) # Окрашиваем выплату (хотя прибыль нагляднее)
            self.table.setItem(row, 4, payout_item)

            # KO (общее)
            ko_item = QtWidgets.QTableWidgetItem(str(s.knockouts_count))
            ko_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, ko_item)

            # Прибыль (Выплата - Бай-ин)
            profit = s.total_prize - s.total_buy_in
            profit_item = QtWidgets.QTableWidgetItem(format_money(profit, with_plus=True))
            profit_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(profit_item, profit) # Окрашиваем прибыль
            self.table.setItem(row, 6, profit_item)


        self.table.resizeColumnsToContents() # Подгоняем ширину колонок

    def filter_table(self):
        """Фильтрует таблицу сессий по поисковому запросу."""
        search_text = self.search_field.text().lower()
        for row in range(self.table.rowCount()):
            show_row = False
            # Проверяем текст во всех видимых колонках
            for col in range(1, self.table.columnCount()): # Начинаем с 1, чтобы пропустить скрытый ID
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    show_row = True
                    break
            self.table.setRowHidden(row, not show_row)

    @QtCore.pyqtSlot()
    def _session_selected(self):
        """Обрабатывает выбор сессии в таблице и обновляет панель деталей."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            self._clear_session_details()
            self._selected_session_id = None
            return

        # Получаем session_id из скрытой колонки (col 0)
        row = selected_items[0].row()
        session_id_item = self.table.item(row, 0)
        if session_id_item:
             self._selected_session_id = session_id_item.text()
             self._update_session_details(self._selected_session_id)
        else:
             self._clear_session_details()
             self._selected_session_id = None


    def _update_session_details(self, session_id: str):
        """
        Загружает и отображает подробную статистику и графики для выбранной сессии.
        """
        logger.debug(f"Обновление деталей для сессии: {session_id}")
        session_stats = self.app_service.get_session_stats(session_id)

        self._clear_session_details() # Очищаем предыдущие детали

        if not session_stats:
             logger.warning(f"Статистика для сессии {session_id} не найдена.")
             # Отобразить сообщение об отсутствии данных
             no_data_label = QtWidgets.QLabel("Данные по выбранной сессии не найдены.")
             no_data_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
             self.details_layout.addWidget(no_data_label)
             return

        # --- Отображаем статистические карточки для сессии ---
        self._populate_session_stat_cards(session_stats)

        # --- Отображаем гистограмму мест на финалке для сессии ---
        self._update_session_places_chart(session_id)


    def _clear_session_details(self):
        """Очищает правую панель деталей сессии."""
        # Удаляем все виджеты из layout деталей сессии
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout(): # Если это вложенный layout
                 # Рекурсивно удаляем виджеты из вложенного layout
                 while item.layout().count():
                     sub_item = item.layout().takeAt(0)
                     sub_widget = sub_item.widget()
                     if sub_widget is not None:
                         sub_widget.deleteLater()
                 item.layout().deleteLater()
            # Удаляем также пустые пространства (spacers)
            del item

        # Восстанавливаем основные заголовки графиков
        graph_title = QtWidgets.QLabel("Графики сессии")
        graph_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        graph_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.details_layout.addWidget(graph_title)

        chart_header = QtWidgets.QLabel("Распределение занятых мест на финальном столе (1-9) в сессии")
        chart_header.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px; margin-bottom: 5px;")
        chart_header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.details_layout.addWidget(chart_header)

        # Пересоздаем виджеты для графиков (matplotlib canvases)
        self.ft_places_figure = Figure(figsize=(8, 5))
        self.ft_places_canvas = FigureCanvas(self.ft_places_figure)
        self.details_layout.addWidget(self.ft_places_canvas)


    def _populate_session_stat_cards(self, session_stats: Session):
        """
        Создает и заполняет статистические карточки для выбранной сессии.
        """
        # Очищаем текущие карточки
        while self.session_stat_cards_layout.count():
             item = self.session_stat_cards_layout.takeAt(0)
             widget = item.widget()
             if widget is not None:
                 widget.deleteLater()

        # Определяем статы сессии для отображения в карточках
        # Используем атрибуты объекта Session
        session_stats_to_display = [
            ("Турниров в сессии", "tournaments_count", str, None),
            ("Общий бай-ин", "total_buy_in", format_money, None),
            ("Общая выплата", "total_prize", format_money, None),
            ("Прибыль сессии", lambda s: s.total_prize - s.total_buy_in, format_money, 0.0), # Вычисляем прибыль
            ("Всего KO в сессии", "knockouts_count", str, None),
            ("Среднее место в сессии", "avg_finish_place", lambda v: f"{v:.2f}" if v is not None else "-", None), # Среднее место по всем турнирам сессии
            # Дополнительные статы сессии, если они будут добавлены в модель Session
            # ("Среднее место FT в сессии", "avg_finish_place_ft", lambda v: f"{v:.2f}" if v is not None else "-", None), # Требует добавления в модель Session
        ]

        cols = 3 # Количество колонок для карточек сессии

        for i, (name, key_or_attr, format_func, color_threshold) in enumerate(session_stats_to_display):
            try:
                if isinstance(key_or_attr, str):
                     # Это прямое поле в объекте Session
                     value = getattr(session_stats, key_or_attr, None)
                else:
                     # Это lambda-функция, которая рассчитывает значение
                     value = key_or_attr(session_stats) # Вызываем lambda, передавая объект Session

                card = StatCard(name, value, format_func=format_func, value_color_threshold=color_threshold)
                self.session_stat_cards_layout.addWidget(card, i // cols, i % cols)
            except Exception as e:
                logger.error(f"Ошибка при создании карточки стата сессии '{name}': {e}")
                card = StatCard(name, "Ошибка", format_func=str) # Показываем ошибку
                self.session_stat_cards_layout.addWidget(card, i // cols, i % cols)


    def _update_session_places_chart(self, session_id: str):
        """
        Рисует гистограмму распределения мест на финальном столе для выбранной сессии.
        """
        # Получаем распределение мест и общее количество финалок для этой сессии
        distribution, total_final_tables_in_session = self.app_service.get_place_distribution_for_session(session_id)

        self.ft_places_figure.clear() # Очищаем предыдущий график

        # Настраиваем стиль для темной темы
        plt.style.use('dark_background')
        bg_color = '#3a3a3a' # Фон для графика внутри панели деталей
        text_color = '#ffffff'
        grid_color = '#555555'

        self.ft_places_figure.patch.set_facecolor(bg_color)

        ax = self.ft_places_figure.add_subplot(111)
        ax.set_facecolor(bg_color)

        places = list(distribution.keys()) # Места от 1 до 9
        counts = [distribution[p] for p in places] # Количество финишей на каждом месте

        percentages = [(count / total_final_tables_in_session * 100) if total_final_tables_in_session > 0 else 0.0 for count in counts]
        percentages = [round(p, 2) for p in percentages] # Округляем проценты

        # Создаем градиент цветов для столбцов: первые места - зеленые, последние - красные
        colors = ['#27ae60', '#2ecc71', '#3498db', '#3498db', '#f1c40f',
                 '#f1c40f', '#e67e22', '#e67e22', '#e74c3c'][:len(places)]

        # Строим гистограмму
        bars = ax.bar(places, counts, color=colors)

        # Добавляем количество и проценты над столбцами
        for i, (bar, count, percentage) in enumerate(zip(bars, counts, percentages)):
            height = bar.get_height()
            if count > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{count}',
                        ha='center', va='bottom', color=text_color, fontweight='bold', fontsize=10)

            if percentage > 0:
                 ax.text(bar.get_x() + bar.get_width()/2., height + (total_final_tables_in_session * 0.01),
                         f'{percentage:.1f}%',
                         ha='center', va='bottom', color=text_color, fontsize=9)


        ax.set_title(f"Распределение мест на финалке (всего финалок: {total_final_tables_in_session})",
                     color=text_color, fontsize=14, pad=20)
        ax.set_xlabel("Место", color=text_color, fontsize=12)
        ax.set_ylabel("Количество финалок", color=text_color, fontsize=12)
        ax.set_xticks(places)
        ax.tick_params(colors=text_color)

        ax.grid(True, linestyle='--', alpha=0.3, color=grid_color)

        # Устанавливаем пределы оси Y
        max_count = max(counts) if counts else 0
        ax.set_ylim(0, max_count * 1.2)

        # Удаляем рамку графика
        for spine in ax.spines.values():
            spine.set_visible(False)

        self.ft_places_figure.tight_layout()
        self.ft_places_canvas.draw()