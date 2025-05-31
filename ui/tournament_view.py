# -*- coding: utf-8 -*-

"""
Представление для отображения списка турниров.
"""

from PyQt6 import QtWidgets, QtCore, QtGui
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ui.app_style import setup_table_widget, format_money, apply_cell_color_by_value, format_percentage
from application_service import ApplicationService
from models import Tournament
from ui.background import thread_manager
from db.repositories.tournament_repo import PaginationResult  # Импортируем новый класс

logger = logging.getLogger('ROYAL_Stats.TournamentView')
logger.setLevel(logging.DEBUG)


class TournamentView(QtWidgets.QWidget):
    """Виджет для отображения списка турниров с фильтрами."""
    
    def __init__(self, app_service: ApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        self.tournaments: List[Tournament] = []
        # Параметры пагинации
        self.current_page = 1
        self.page_size = 100  # Количество записей на странице
        self.total_pages = 1
        self.total_count = 0
        # Параметры сортировки
        self.sort_column = "start_time"
        self.sort_direction = "DESC"
        # Параметры фильтрации
        self.current_buyin_filter = None
        self._data_cache = {}  # Кеш для данных
        self._cache_valid = False  # Флаг валидности кеша
        self._init_ui()
        
    def _init_ui(self):
        """Инициализирует интерфейс."""
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Контейнер для содержимого
        self.content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок
        header = QtWidgets.QLabel("Список турниров")
        header.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #FAFAFA;
                margin-bottom: 16px;
            }
        """)
        content_layout.addWidget(header)
        
        # Панель фильтров
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.setSpacing(12)
        
        # Фильтр по бай-ину
        filter_layout.addWidget(QtWidgets.QLabel("Бай-ин:"))
        self.buyin_filter = QtWidgets.QComboBox()
        self.buyin_filter.setMinimumWidth(120)
        self.buyin_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.buyin_filter)
        
        # Фильтр по результату
        filter_layout.addWidget(QtWidgets.QLabel("Результат:"))
        self.result_filter = QtWidgets.QComboBox()
        self.result_filter.setMinimumWidth(150)
        self.result_filter.addItems(["Все", "В призах (1-3)", "Финальный стол", "Вне призов"])
        self.result_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.result_filter)
        
        # Размер страницы
        filter_layout.addWidget(QtWidgets.QLabel("На странице:"))
        self.page_size_combo = QtWidgets.QComboBox()
        self.page_size_combo.addItems(["50", "100", "200", "500"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        filter_layout.addWidget(self.page_size_combo)
        
        filter_layout.addStretch()
        
        # Информация о пагинации
        self.pagination_info = QtWidgets.QLabel("")
        self.pagination_info.setStyleSheet("color: #A1A1AA; font-size: 13px;")
        filter_layout.addWidget(self.pagination_info)
        
        content_layout.addLayout(filter_layout)
        
        # Таблица турниров
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(8)
        # Настраиваем заголовки с сортировкой
        headers = [
            ("ID турнира", "tournament_id"),
            ("Дата", "start_time"),
            ("Бай-ин", "buyin"),
            ("Место", "finish_place"),
            ("Выплата", "payout"),
            ("KO", "ko_count"),
            ("Старт стек\nна ФТ", "final_table_initial_stack_chips"),
            ("Профит", "profit")
        ]
        header_labels = [h[0] for h in headers]
        self.column_mappings = {i: h[1] for i, h in enumerate(headers)}
        self.table.setHorizontalHeaderLabels(header_labels)

        setup_table_widget(self.table)
        # Отключаем встроенную сортировку Qt, чтобы сортировка происходила через БД
        # и затрагивала весь набор данных, а не только текущую страницу
        self.table.setSortingEnabled(False)

        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)

        # Контекстное меню для копирования ID
        self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Настройка ширины колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        
        content_layout.addWidget(self.table)
        
        # Панель пагинации
        pagination_layout = QtWidgets.QHBoxLayout()
        pagination_layout.setSpacing(8)
        self.first_page_btn = QtWidgets.QPushButton("<<")
        self.first_page_btn.setMaximumWidth(40)
        self.first_page_btn.clicked.connect(lambda: self._go_to_page(1))
        pagination_layout.addWidget(self.first_page_btn)
        self.prev_page_btn = QtWidgets.QPushButton("<")
        self.prev_page_btn.setMaximumWidth(40)
        self.prev_page_btn.clicked.connect(lambda: self._go_to_page(self.current_page - 1))
        pagination_layout.addWidget(self.prev_page_btn)
        self.page_info_label = QtWidgets.QLabel("Страница 1 из 1")
        self.page_info_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.page_info_label.setMinimumWidth(120)
        pagination_layout.addWidget(self.page_info_label)
        self.next_page_btn = QtWidgets.QPushButton(">")
        self.next_page_btn.setMaximumWidth(40)
        self.next_page_btn.clicked.connect(lambda: self._go_to_page(self.current_page + 1))
        pagination_layout.addWidget(self.next_page_btn)
        self.last_page_btn = QtWidgets.QPushButton(">>")
        self.last_page_btn.setMaximumWidth(40)
        self.last_page_btn.clicked.connect(lambda: self._go_to_page(self.total_pages))
        pagination_layout.addWidget(self.last_page_btn)
        pagination_layout.addStretch()
        pagination_layout.addWidget(QtWidgets.QLabel("Перейти к:"))
        self.goto_page_input = QtWidgets.QLineEdit()
        self.goto_page_input.setMaximumWidth(60)
        self.goto_page_input.setPlaceholderText("№")
        self.goto_page_input.returnPressed.connect(self._on_goto_page)
        pagination_layout.addWidget(self.goto_page_input)
        content_layout.addLayout(pagination_layout)
        
        # Статистика внизу
        self.stats_label = QtWidgets.QLabel("")
        self.stats_label.setStyleSheet("""
            QLabel {
                color: #E4E4E7;
                font-size: 14px;
                padding: 12px;
                background-color: #27272A;
                border-radius: 8px;
                margin-top: 8px;
            }
        """)
        content_layout.addWidget(self.stats_label)
        
        self.main_layout.addWidget(self.content_widget)
        
        # Создаем loading overlay
        self._create_loading_overlay()
        
    def _create_loading_overlay(self):
        """Создает оверлей загрузки."""
        self.loading_overlay = QtWidgets.QWidget(self)
        self.loading_overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.7);
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self.loading_overlay)
        
        # Контейнер для индикатора
        container = QtWidgets.QWidget()
        container.setMaximumWidth(300)
        container.setStyleSheet("""
            QWidget {
                background-color: #27272A;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        container_layout = QtWidgets.QVBoxLayout(container)
        
        # Индикатор загрузки
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3F3F46;
                border-radius: 6px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 6px;
            }
        """)
        container_layout.addWidget(self.progress_bar)
        
        # Текст загрузки
        self.loading_label = QtWidgets.QLabel("Загрузка турниров...")
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #FAFAFA;
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
            }
        """)
        self.loading_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.loading_label)
        
        layout.addWidget(container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        
        self.loading_overlay.hide()
        
    def show_loading_overlay(self):
        """Показывает оверлей загрузки."""
        self.loading_overlay.resize(self.size())
        self.loading_overlay.raise_()
        self.loading_overlay.show()
        
    def hide_loading_overlay(self):
        """Скрывает оверлей загрузки."""
        self.loading_overlay.hide()
        
    def resizeEvent(self, event):
        """Обрабатывает изменение размера виджета."""
        super().resizeEvent(event)
        # Обновляем размер оверлея при изменении размера виджета
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(self.size())
            
    def invalidate_cache(self):
        """Сбрасывает кеш данных."""
        self._cache_valid = False
        self._data_cache.clear()
        
    def reload(self, show_overlay: bool = True):
        """Перезагружает данные из ApplicationService."""
        logger.debug("Перезагрузка TournamentView...")
        self._show_overlay = show_overlay
        if show_overlay:
            self.show_loading_overlay()
        def load_filter_data():
            return self.app_service.get_distinct_buyins()
        thread_manager.run_in_thread(
            widget_id=f"{id(self)}_filters",
            fn=load_filter_data,
            callback=self._on_filter_data_loaded,
            error_callback=lambda e: logger.error(f"Ошибка загрузки фильтров TournamentView: {e}"),
            owner=self
        )
    def _on_filter_data_loaded(self, buyins):
        self._data_cache['buyins'] = buyins
        self._update_buyin_filter()
        self._load_tournaments_data()
    def _load_tournaments_data(self):
        def load_data():
            result_filter_map = {
                "В призах (1-3)": "prizes",
                "Финальный стол": "final_table",
                "Вне призов": "out_of_prizes",
                "Все": None
            }
            buyin = self.buyin_filter.currentText()
            buyin_filter = float(buyin) if buyin and buyin != "Все" else None
            result_filter = result_filter_map.get(self.result_filter.currentText())
            return self.app_service.tournament_repo.get_tournaments_paginated(
                page=self.current_page,
                page_size=int(self.page_size_combo.currentText()),
                buyin_filter=buyin_filter,
                result_filter=result_filter,
                sort_column=self.sort_column,
                sort_direction=self.sort_direction
            )
        thread_manager.run_in_thread(
            widget_id=f"{id(self)}_tournaments",
            fn=load_data,
            callback=self._on_tournaments_data_loaded,
            error_callback=lambda e: logger.error(f"Ошибка загрузки турниров TournamentView: {e}"),
            owner=self
        )
    def _on_tournaments_data_loaded(self, pagination_result: PaginationResult):
        self.tournaments = pagination_result.tournaments
        self.current_page = pagination_result.current_page
        self.page_size = pagination_result.page_size
        self.total_pages = pagination_result.total_pages
        self.total_count = pagination_result.total_count
        self._update_tournaments_table(self.tournaments)
        self._update_pagination_info()
        self.hide_loading_overlay()
    def _update_buyin_filter(self):
        self.buyin_filter.blockSignals(True)
        self.buyin_filter.clear()
        self.buyin_filter.addItem("Все")
        for b in sorted(self._data_cache.get('buyins', [])):
            self.buyin_filter.addItem(str(b))
        self.buyin_filter.blockSignals(False)
    def _on_filter_changed(self):
        self.current_page = 1
        self._load_tournaments_data()
    def _on_page_size_changed(self):
        self.current_page = 1
        self._load_tournaments_data()
    def _on_header_clicked(self, logical_index):
        col = self.column_mappings.get(logical_index)
        if not col:
            return
        if self.sort_column == col:
            self.sort_direction = "ASC" if self.sort_direction == "DESC" else "DESC"
        else:
            self.sort_column = col
            self.sort_direction = "DESC"
        self.current_page = 1
        self._load_tournaments_data()
    def _go_to_page(self, page):
        if 1 <= page <= self.total_pages:
            self.current_page = page
            self._load_tournaments_data()
    def _on_goto_page(self):
        try:
            page = int(self.goto_page_input.text())
            self._go_to_page(page)
        except Exception:
            pass
    def _update_pagination_info(self):
        self.page_info_label.setText(f"Страница {self.current_page} из {self.total_pages}")
        self.pagination_info.setText(f"Всего турниров: {self.total_count}")
    def _update_tournaments_table(self, tournaments: List[Tournament]):
        """Обновляет таблицу турниров."""
        self.table.setRowCount(len(tournaments))
        
        for row, t in enumerate(tournaments):
            # ID турнира
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(t.tournament_id))

            # Дата
            date = t.start_time or "-"
            if t.start_time:
                for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        dt = datetime.strptime(t.start_time, fmt)
                        date = dt.strftime("%d.%m.%Y %H:%M:%S")
                        break
                    except ValueError:
                        continue
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(date))

            # Бай-ин
            buyin_item = QtWidgets.QTableWidgetItem(format_money(t.buyin, decimals=0))
            buyin_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 2, buyin_item)

            # Место
            place_text = str(t.finish_place) if t.finish_place else "-"
            place_item = QtWidgets.QTableWidgetItem(place_text)
            place_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            # Раскрашиваем места 1-3
            if t.finish_place:
                if t.finish_place == 1:
                    place_item.setForeground(QtGui.QBrush(QtGui.QColor("#10B981")))
                elif t.finish_place == 2:
                    place_item.setForeground(QtGui.QBrush(QtGui.QColor("#6EE7B7")))
                elif t.finish_place == 3:
                    place_item.setForeground(QtGui.QBrush(QtGui.QColor("#FCD34D")))
            self.table.setItem(row, 3, place_item)

            # Выплата
            payout_item = QtWidgets.QTableWidgetItem(format_money(t.payout))
            payout_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(payout_item, t.payout)
            self.table.setItem(row, 4, payout_item)

            # KO
            ko_item = QtWidgets.QTableWidgetItem(str(t.ko_count))
            ko_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if t.ko_count > 0:
                ko_item.setForeground(QtGui.QBrush(QtGui.QColor("#10B981")))
            self.table.setItem(row, 5, ko_item)

            # Стартовый стек на финалке
            stack_text = "—"
            if t.final_table_initial_stack_chips is not None:
                # format stack with space as thousands separator
                stack_text = f"{int(t.final_table_initial_stack_chips):,}".replace(",", " ")
            stack_item = QtWidgets.QTableWidgetItem(stack_text)
            stack_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 6, stack_item)

            # Профит
            profit = (t.payout if t.payout is not None else 0) - (t.buyin if t.buyin is not None else 0)
            profit_item = QtWidgets.QTableWidgetItem(format_money(profit, with_plus=True))
            profit_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(profit_item, profit)
            self.table.setItem(row, 7, profit_item)
            
    def _update_statistics(self, tournaments: List[Tournament]):
        """Обновляет статистику для отфильтрованных турниров."""
        if not tournaments:
            self.stats_label.setText("Нет турниров для отображения")
            return
            
        total = len(tournaments)
        total_buyin = sum(t.buyin for t in tournaments if t.buyin is not None)
        total_payout = sum(t.payout if t.payout is not None else 0 for t in tournaments)
        total_profit = total_payout - total_buyin
        total_ko = sum(t.ko_count for t in tournaments)
        itm_count = sum(1 for t in tournaments if t.finish_place and 1 <= t.finish_place <= 3)
        itm_percent = (itm_count / total * 100) if total > 0 else 0
        
        roi = ((total_profit / total_buyin) * 100) if total_buyin > 0 else 0
        
        self.stats_label.setText(
            f"Турниров: {total} | "
            f"Бай-ин: {format_money(total_buyin)} | "
            f"Выплаты: {format_money(total_payout)} | "
            f"Профит: {format_money(total_profit, with_plus=True)} | "
            f"ROI: {roi:+.1f}% | "
            f"ITM: {itm_percent:.1f}% | "
            f"KO: {total_ko}"
        )

    def _show_context_menu(self, position):
        """Контекстное меню для копирования ID турнира."""
        item = self.table.itemAt(position)
        if not item:
            return
        row = item.row()
        menu = QtWidgets.QMenu(self)
        copy_action = menu.addAction("Копировать ID турнира")
        copy_action.triggered.connect(lambda: self._copy_tournament_id(row))
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _copy_tournament_id(self, row: int):
        """Копирует ID турнира в буфер обмена."""
        if 0 <= row < len(self.tournaments):
            t_id = self.tournaments[row].tournament_id
            QtWidgets.QApplication.clipboard().setText(t_id)
