# -*- coding: utf-8 -*-

"""
Таблица со всеми турнирами Hero: место, выплата, KO, бай-ин, дата.
Обновлен для работы с ApplicationService и фильтрацией по бай-ину.
"""

from PyQt6 import QtWidgets, QtGui, QtCore
from typing import List, Optional
from ui.app_style import setup_table_widget, format_money, apply_cell_color_by_value, format_percentage
from application_service import ApplicationService # Импортируем сервис
import config # Для доступа к имени Hero

import logging
logger = logging.getLogger('ROYAL_Stats.TournamentView')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)


class TournamentView(QtWidgets.QWidget):
    """
    Таблица всех турниров Hero.
    """

    def __init__(self, app_service: ApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service # Используем ApplicationService
        self._all_tournaments = [] # Храним полный список турниров для фильтрации
        self._init_ui()
        # Данные загружаются при первом отображении вкладки или по сигналу обновления

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Верхний блок с заголовком и фильтрами
        header_layout = QtWidgets.QHBoxLayout()

        # Заголовок
        self.title_label = QtWidgets.QLabel("Турниры игрока")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Фильтр по бай-ину
        self.buyin_filter_combo = QtWidgets.QComboBox()
        self.buyin_filter_combo.setToolTip("Фильтр по бай-ину")
        self.buyin_filter_combo.addItem("Все бай-ины") # Добавляем опцию "Все"
        self.buyin_filter_combo.currentIndexChanged.connect(self._apply_filters) # Применяем фильтры при смене значения
        buyin_filter_layout = QtWidgets.QHBoxLayout()
        buyin_filter_layout.addWidget(QtWidgets.QLabel("Бай-ин:"))
        buyin_filter_layout.addWidget(self.buyin_filter_combo)
        header_layout.addLayout(buyin_filter_layout)


        # Фильтр по результату (оставляем из старой версии)
        self.tournament_result_filter = QtWidgets.QComboBox()
        self.tournament_result_filter.addItems(["Все турниры", "Только ITM", "Только победы", "Только финалки"]) # Добавим фильтр на финалки
        self.tournament_result_filter.setToolTip("Фильтр по результату")
        self.tournament_result_filter.currentIndexChanged.connect(self._apply_filters) # Применяем фильтры при смене значения
        result_filter_layout = QtWidgets.QHBoxLayout()
        result_filter_layout.addWidget(QtWidgets.QLabel("Результат:"))
        result_filter_layout.addWidget(self.tournament_result_filter)
        header_layout.addLayout(result_filter_layout)

        # Фильтр по диапазону дат (из старой версии)
        # Пока отключим сложные фильтры по датам, оставим их в ApplicationService если потребуются
        # self.date_from = QtWidgets.QDateTimeEdit()
        # self.date_to = QtWidgets.QDateTimeEdit()
        # self.date_from.setCalendarPopup(True)
        # self.date_to.setCalendarPopup(True)
        # self.date_from.dateTimeChanged.connect(self._apply_filters)
        # self.date_to.dateTimeChanged.connect(self._apply_filters)
        # date_filter_layout = QtWidgets.QHBoxLayout()
        # date_filter_layout.addWidget(QtWidgets.QLabel("C:"))
        # date_filter_layout.addWidget(self.date_from)
        # date_filter_layout.addWidget(QtWidgets.QLabel("по:"))
        # date_filter_layout.addWidget(self.date_to)
        # header_layout.addLayout(date_filter_layout)


        # Кнопка обновления
        self.refresh_btn = QtWidgets.QPushButton("Обновить")
        self.refresh_btn.setIcon(QtGui.QIcon.fromTheme("view-refresh"))
        self.refresh_btn.setToolTip("Обновить данные турниров")
        self.refresh_btn.clicked.connect(self.reload)
        header_layout.addWidget(self.refresh_btn)


        layout.addLayout(header_layout)

        # Статистика по текущему выбору (пересчитывается при фильтрации)
        stats_layout = QtWidgets.QHBoxLayout()

        self.filtered_tournament_count = QtWidgets.QLabel("Турниров (фильтр): 0")
        self.filtered_tournament_count.setStyleSheet("font-weight: bold;")

        self.filtered_avg_place = QtWidgets.QLabel("Среднее место: -")
        self.filtered_avg_place.setStyleSheet("font-weight: bold;")

        self.filtered_total_profit = QtWidgets.QLabel("Общая прибыль: -")
        self.filtered_total_profit.setStyleSheet("font-weight: bold;")

        self.filtered_roi = QtWidgets.QLabel("ROI: -")
        self.filtered_roi.setStyleSheet("font-weight: bold;")

        stats_layout.addWidget(self.filtered_tournament_count)
        stats_layout.addWidget(self.filtered_avg_place)
        stats_layout.addWidget(self.filtered_total_profit)
        stats_layout.addWidget(self.filtered_roi)
        stats_layout.addStretch()

        # Добавляем разделитель
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

        layout.addWidget(separator)
        layout.addLayout(stats_layout)
        layout.addWidget(separator)

        # Таблица турниров
        self.table = QtWidgets.QTableWidget(0, 8) # ID, Турнир, Место, Выплата, KO, Бай-ин, Прибыль, Дата
        self.table.setHorizontalHeaderLabels(["ID", "Турнир", "Место", "Выплата", "KO", "Бай-ин", "Прибыль", "Дата"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True) # Включаем сортировку по колонкам

        # Применяем улучшения к таблице
        setup_table_widget(self.table)

        # Скрываем колонку ID
        self.table.hideColumn(0)

        layout.addWidget(self.table)

        # Строка поиска (из старой версии)
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(QtWidgets.QLabel("Поиск:"))
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Поиск по названию турнира или ID...")
        self.search_field.textChanged.connect(self._filter_table_by_text) # Применяем текстовый фильтр
        search_layout.addWidget(self.search_field)

        layout.addLayout(search_layout)

        self.setLayout(layout)


    def reload(self):
        """
        Загружает все турниры Hero из ApplicationService и обновляет UI.
        """
        logger.debug("Перезагрузка TournamentView...")
        # Получаем полный список турниров
        self._all_tournaments = self.app_service.get_all_tournaments()

        # Обновляем фильтр по бай-ину
        self._populate_buyin_filter()

        # Применяем текущие фильтры и заполняем таблицу
        self._apply_filters()
        logger.debug("Перезагрузка TournamentView завершена.")

    def _populate_buyin_filter(self):
        """Заполняет комбобокс фильтра по бай-ину."""
        self.buyin_filter_combo.blockSignals(True) # Блокируем сигналы, пока заполняем
        self.buyin_filter_combo.clear()
        self.buyin_filter_combo.addItem("Все бай-ины") # Опция по умолчанию

        # Получаем список уникальных бай-инов из ApplicationService
        distinct_buyins = self.app_service.get_distinct_buyins()
        for buyin in sorted(distinct_buyins): # Сортируем бай-ины
             self.buyin_filter_combo.addItem(format_money(buyin), userData=buyin) # Сохраняем числовое значение в userData

        self.buyin_filter_combo.blockSignals(False)


    def _apply_filters(self):
        """
        Применяет выбранные фильтры (бай-ин, результат) к полному списку турниров
        и обновляет таблицу и статистику.
        """
        logger.debug("Применение фильтров в TournamentView...")

        # 1. Фильтр по бай-ину
        selected_buyin = self.buyin_filter_combo.currentData() # Получаем числовое значение бай-ина
        if selected_buyin is None: # Выбрано "Все бай-ины"
             filtered_by_buyin = self._all_tournaments
        else:
             filtered_by_buyin = [t for t in self._all_tournaments if t.buyin == selected_buyin]

        # 2. Фильтр по результату турнира
        tournament_result_filter = self.tournament_result_filter.currentText()
        if tournament_result_filter == "Все турниры":
            filtered_by_result = filtered_by_buyin
        elif tournament_result_filter == "Только ITM":
            # ITM = 1, 2 или 3 место
            filtered_by_result = [t for t in filtered_by_buyin if t.finish_place in (1, 2, 3)]
        elif tournament_result_filter == "Только победы":
            filtered_by_result = [t for t in filtered_by_buyin if t.finish_place == 1]
        elif tournament_result_filter == "Только финалки":
             # Турниры, где Hero достиг финального стола (по флагу reached_final_table)
             filtered_by_result = [t for t in filtered_by_buyin if t.reached_final_table]


        # Теперь filtered_by_result содержит турниры, прошедшие все фильтры.
        # Обновляем таблицу и статистику на основе этого списка.
        self._update_tournaments_table(filtered_by_result)
        self._update_stats(filtered_by_result)

        # Применяем текстовый поиск поверх этих фильтров
        self._filter_table_by_text() # Вызываем текстовый фильтр после применения основных


    def _update_tournaments_table(self, tournaments_to_display: List[Tournament]):
        """Заполняет таблицу турниров на основе предоставленного списка."""
        self.table.setRowCount(0)
        if not tournaments_to_display:
            logger.debug("Нет турниров для отображения после фильтрации.")
            return

        # Сортируем турниры по дате перед отображением (для единообразия)
        # Сортировка уже происходит в репозитории, но если фильтры применяются здесь, нужно повторно
        # sorted_tournaments = sorted(tournaments_to_display, key=lambda t: t.start_time or '', reverse=False) # Сортировка по дате

        for t in tournaments_to_display: # Используем отфильтрованный список
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ID турнира (скрытая колонка)
            id_item = QtWidgets.QTableWidgetItem(str(t.id))
            self.table.setItem(row, 0, id_item)

            # Название турнира (с иконкой типа?) + ID в тултипе
            tournament_name = t.tournament_name or f"Турнир #{t.tournament_id}"
            tournament_item = QtWidgets.QTableWidgetItem(tournament_name)
            # if "knockout" in tournament_name.lower() or "mystery" in tournament_name.lower(): # Пример определения по названию
            #     tournament_item.setIcon(QtGui.QIcon.fromTheme("view-media-artist")) # Иконка для KO турниров
            tournament_item.setToolTip(f"ID: {t.tournament_id}\nСессия: {t.session_id}\nДата: {t.start_time}")
            self.table.setItem(row, 1, tournament_item)

            # Место
            place_text = str(t.finish_place) if t.finish_place is not None else "-"
            place_item = QtWidgets.QTableWidgetItem(place_text)
            place_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            # Подсветка места разными цветами (для ITM мест на финалке)
            if t.finish_place is not None and t.reached_final_table: # Красим только если достиг финалки
                try:
                    place = int(t.finish_place)
                    if place == 1:
                        place_item.setForeground(QtGui.QBrush(QtGui.QColor(255, 215, 0)))  # Золото
                    elif place == 2:
                        place_item.setForeground(QtGui.QBrush(QtGui.QColor(192, 192, 192)))  # Серебро
                    elif place == 3:
                        place_item.setForeground(QtGui.QBrush(QtGui.QColor(205, 127, 50)))  # Бронза
                    elif 4 <= place <= 9: # ITM на финалке, но не топ 3 (если такое бывает)
                        place_item.setForeground(QtGui.QBrush(QtGui.QColor(46, 204, 113))) # Зеленый
                except (ValueError, TypeError):
                    pass # Не красим, если место не число

            self.table.setItem(row, 2, place_item)

            # Выплата
            payout_item = QtWidgets.QTableWidgetItem(format_money(t.payout))
            payout_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(payout_item, t.payout) # Окрашиваем выплату
            self.table.setItem(row, 3, payout_item)

            # KO
            ko_count_item = QtWidgets.QTableWidgetItem(str(t.ko_count))
            ko_count_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, ko_count_item)

            # Бай-ин
            buyin_item = QtWidgets.QTableWidgetItem(format_money(t.buyin))
            buyin_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, buyin_item)

            # Прибыль (Выплата - Бай-ин)
            profit = (t.payout or 0.0) - (t.buyin or 0.0) # Учитываем None значения
            profit_item = QtWidgets.QTableWidgetItem(format_money(profit, with_plus=True))
            profit_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(profit_item, profit) # Окрашиваем прибыль
            self.table.setItem(row, 6, profit_item)

            # Дата старта турнира
            date_item = QtWidgets.QTableWidgetItem(str(t.start_time) if t.start_time else "-")
            date_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 7, date_item)


        self.table.resizeColumnsToContents() # Подгоняем ширину колонок
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch) # Название турнира - растягивается


    def _update_stats(self, tournaments_for_stats: List[Tournament]):
        """
        Обновляет виджеты статистики на основе текущего отфильтрованного списка турниров.
        """
        # Количество турниров
        self.filtered_tournament_count.setText(f"Турниров (фильтр): {len(tournaments_for_stats)}")

        # Среднее место
        places = [t.finish_place for t in tournaments_for_stats if t.finish_place is not None]
        avg_place = sum(places) / len(places) if places else 0.0
        self.filtered_avg_place.setText(f"Среднее место: {avg_place:.2f}")

        # Общая прибыль
        total_buyin = sum(t.buyin or 0.0 for t in tournaments_for_stats)
        total_payout = sum(t.payout or 0.0 for t in tournaments_for_stats)
        profit = total_payout - total_buyin
        self.filtered_total_profit.setText(f"Общая прибыль: {format_money(profit, with_plus=True)}")
        apply_cell_color_by_value(self.filtered_total_profit, profit) # Окрашиваем

        # ROI
        roi = (profit / total_buyin * 100) if total_buyin > 0 else 0.0
        self.filtered_roi.setText(f"ROI: {roi:.2f}%")
        apply_cell_color_by_value(self.filtered_roi, roi) # Окрашиваем


    def _filter_table_by_text(self):
        """Фильтрует видимые строки таблицы по поисковому запросу (на основе текущих фильтров)."""
        search_text = self.search_field.text().lower()
        for row in range(self.table.rowCount()):
            # Изначально строка считается видимой (если она прошла _apply_filters)
            is_hidden_by_filter = self.table.isRowHidden(row)

            if not is_hidden_by_filter: # Применяем текстовый фильтр только к уже видимым строкам
                show_row_by_text = False
                # Проверяем текст в колонках "Турнир" и "ID" (ID скрыт, но поиск может по нему идти)
                for col in [0, 1]: # col 0 для ID, col 1 для Названия
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        show_row_by_text = True
                        break

                # Скрываем строку, если она не соответствует текстовому поиску
                self.table.setRowHidden(row, not show_row_by_text)

    # Переопределяем showEvent для первой загрузки данных
    def showEvent(self, event: QtGui.QShowEvent):
        super().showEvent(event)
        # Загружаем данные только при первом показе виджета
        if not hasattr(self, '_first_show_done'):
            self.reload()
            self._first_show_done = True