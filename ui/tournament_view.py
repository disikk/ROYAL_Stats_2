# -*- coding: utf-8 -*-

"""
Представление для отображения списка турниров.
"""

from PyQt6 import QtWidgets, QtCore, QtGui
import logging
from typing import List, Optional

from ui.app_style import setup_table_widget, format_money, apply_cell_color_by_value, format_percentage
from application_service import ApplicationService
from models import Tournament

logger = logging.getLogger('ROYAL_Stats.TournamentView')
logger.setLevel(logging.DEBUG)


class TournamentView(QtWidgets.QWidget):
    """Виджет для отображения списка турниров с фильтрами."""
    
    def __init__(self, app_service: ApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        self.tournaments: List[Tournament] = []
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
        self.buyin_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.buyin_filter)
        
        # Фильтр по результату
        filter_layout.addWidget(QtWidgets.QLabel("Результат:"))
        self.result_filter = QtWidgets.QComboBox()
        self.result_filter.setMinimumWidth(150)
        self.result_filter.addItems(["Все", "В призах (1-3)", "Финальный стол", "Вне призов"])
        self.result_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.result_filter)
        
        filter_layout.addStretch()
        
        # Информация о фильтрации
        self.filter_info = QtWidgets.QLabel("")
        self.filter_info.setStyleSheet("color: #A1A1AA; font-size: 13px;")
        filter_layout.addWidget(self.filter_info)
        
        content_layout.addLayout(filter_layout)
        
        # Таблица турниров
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID турнира", "Название", "Дата", "Бай-ин", 
            "Место", "Выплата", "KO", "Профит"
        ])
        
        setup_table_widget(self.table)
        
        # Настройка ширины колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        
        content_layout.addWidget(self.table)
        
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
        
    def reload(self):
        """Перезагружает данные из ApplicationService."""
        logger.debug("Перезагрузка TournamentView...")
        
        # Показываем индикатор загрузки
        self.show_loading_overlay()
        
        # Используем QTimer для небольшой задержки, чтобы UI успел обновиться
        QtCore.QTimer.singleShot(10, self._do_reload)
        
    def _do_reload(self):
        """Выполняет фактическую перезагрузку данных."""
        try:
            # Загружаем данные только если кеш невалиден
            if not self._cache_valid:
                self._load_data()
                self._cache_valid = True
            
            # Обновляем фильтр бай-инов
            self._update_buyin_filter()
            
            # Применяем фильтры и обновляем таблицу
            self._apply_filters()
            
            logger.debug("Перезагрузка TournamentView завершена.")
            
        finally:
            # Скрываем индикатор загрузки
            self.hide_loading_overlay()
            
    def _load_data(self):
        """Загружает данные из ApplicationService в кеш."""
        logger.debug("Загрузка данных в кеш TournamentView...")
        
        # Загружаем все турниры
        self.tournaments = self.app_service.get_all_tournaments()
        self._data_cache['tournaments'] = self.tournaments
        
        # Загружаем уникальные бай-ины
        self._data_cache['buyins'] = self.app_service.get_distinct_buyins()
        
        logger.debug(f"Загружено {len(self.tournaments)} турниров")
        
    def _update_buyin_filter(self):
        """Обновляет список доступных бай-инов."""
        current_text = self.buyin_filter.currentText()
        self.buyin_filter.clear()
        
        # Получаем уникальные бай-ины из кеша
        buyins = self._data_cache.get('buyins', [])
        
        # Добавляем "Все" и отсортированные бай-ины
        self.buyin_filter.addItem("Все")
        for buyin in sorted(buyins):
            self.buyin_filter.addItem(format_money(buyin, decimals=0))
            
        # Восстанавливаем выбор, если возможно
        index = self.buyin_filter.findText(current_text)
        if index >= 0:
            self.buyin_filter.setCurrentIndex(index)
            
    def _apply_filters(self):
        """Применяет выбранные фильтры к списку турниров."""
        logger.debug("Применение фильтров в TournamentView...")
        
        # Фильтрация по бай-ину
        buyin_text = self.buyin_filter.currentText()
        if buyin_text and buyin_text != "Все":
            # Извлекаем числовое значение из "$10" -> 10.0
            try:
                buyin_value = float(buyin_text.replace("$", "").replace(",", ""))
                filtered = [t for t in self.tournaments if t.buyin == buyin_value]
            except ValueError:
                filtered = self.tournaments
        else:
            filtered = self.tournaments[:]
            
        # Фильтрация по результату
        result_text = self.result_filter.currentText()
        if result_text == "В призах (1-3)":
            filtered = [t for t in filtered if t.finish_place and 1 <= t.finish_place <= 3]
        elif result_text == "Финальный стол":
            filtered = [t for t in filtered if t.reached_final_table]
        elif result_text == "Вне призов":
            filtered = [t for t in filtered if t.finish_place and t.finish_place > 3]
            
        # Обновляем таблицу
        self._update_tournaments_table(filtered)
        
        # Обновляем информацию о фильтрации
        self.filter_info.setText(f"Показано: {len(filtered)} из {len(self.tournaments)}")
        
        # Обновляем статистику
        self._update_statistics(filtered)
        
    def _update_tournaments_table(self, tournaments: List[Tournament]):
        """Обновляет таблицу турниров."""
        self.table.setRowCount(len(tournaments))
        
        for row, t in enumerate(tournaments):
            # ID турнира
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(t.tournament_id))
            
            # Название
            name = t.tournament_name or "-"
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(name))
            
            # Дата
            date = t.start_time or "-"
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(date))
            
            # Бай-ин
            buyin_item = QtWidgets.QTableWidgetItem(format_money(t.buyin, decimals=0))
            buyin_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, buyin_item)
            
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
            self.table.setItem(row, 4, place_item)
            
            # Выплата
            payout_item = QtWidgets.QTableWidgetItem(format_money(t.payout))
            payout_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(payout_item, t.payout)
            self.table.setItem(row, 5, payout_item)
            
            # KO
            ko_item = QtWidgets.QTableWidgetItem(str(t.ko_count))
            ko_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if t.ko_count > 0:
                ko_item.setForeground(QtGui.QBrush(QtGui.QColor("#10B981")))
            self.table.setItem(row, 6, ko_item)
            
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