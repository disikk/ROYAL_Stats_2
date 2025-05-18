from PyQt6 import QtWidgets, QtGui, QtCore
from ui.app_style import setup_table_widget, format_money, apply_cell_color_by_value

class TournamentView(QtWidgets.QWidget):
    """
    Таблица со всеми турнирами Hero: место, выплата, KO, бай-ин, дата.
    """

    def __init__(self, tournament_repo, parent=None):
        super().__init__(parent)
        self.tournament_repo = tournament_repo
        self._init_ui()
        self.reload()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Верхний блок с заголовком и фильтрами
        header_layout = QtWidgets.QHBoxLayout()
        
        # Заголовок
        self.title_label = QtWidgets.QLabel("Турниры игрока")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(self.title_label)
        
        # Фильтры (по дате, типу турнира и т.д.)
        self.date_filter = QtWidgets.QComboBox()
        self.date_filter.addItems(["Все даты", "Последний месяц", "Последние 3 месяца", "Текущий год"])
        self.date_filter.setToolTip("Фильтр по дате")
        self.date_filter.currentIndexChanged.connect(self.reload)
        
        self.tournament_filter = QtWidgets.QComboBox()
        self.tournament_filter.addItems(["Все турниры", "Только ITM", "Только победы"])
        self.tournament_filter.setToolTip("Фильтр по результату")
        self.tournament_filter.currentIndexChanged.connect(self.reload)
        
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Дата:"))
        filter_layout.addWidget(self.date_filter)
        filter_layout.addWidget(QtWidgets.QLabel("Результат:"))
        filter_layout.addWidget(self.tournament_filter)
        
        header_layout.addLayout(filter_layout)
        header_layout.addStretch()
        
        # Кнопка обновления
        self.refresh_btn = QtWidgets.QPushButton()
        self.refresh_btn.setIcon(QtGui.QIcon.fromTheme("view-refresh"))
        self.refresh_btn.setToolTip("Обновить данные")
        self.refresh_btn.clicked.connect(self.reload)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Блок с статистикой по текущему выбору
        stats_layout = QtWidgets.QHBoxLayout()
        
        self.tournament_count = QtWidgets.QLabel("Всего: 0")
        self.tournament_count.setStyleSheet("font-weight: bold;")
        
        self.avg_place = QtWidgets.QLabel("Среднее место: -")
        self.avg_place.setStyleSheet("font-weight: bold;")
        
        self.total_profit = QtWidgets.QLabel("Общая прибыль: 0.00 ₽")
        self.total_profit.setStyleSheet("font-weight: bold;")
        
        self.roi = QtWidgets.QLabel("ROI: 0.0%")
        self.roi.setStyleSheet("font-weight: bold;")
        
        stats_layout.addWidget(self.tournament_count)
        stats_layout.addWidget(self.avg_place)
        stats_layout.addWidget(self.total_profit)
        stats_layout.addWidget(self.roi)
        stats_layout.addStretch()
        
        # Добавляем разделитель
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        
        layout.addWidget(separator)
        layout.addLayout(stats_layout)
        layout.addWidget(separator)
        
        # Таблица турниров
        self.table = QtWidgets.QTableWidget(0, 7)  # Добавлена колонка для прибыли
        self.table.setHorizontalHeaderLabels(["ID", "Турнир", "Место", "Выплата", "KO", "Бай-ин", "Прибыль", "Дата"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        
        # Применяем улучшения к таблице
        setup_table_widget(self.table)
        
        # Скрываем колонку ID (будем показывать при наведении курсора)
        self.table.hideColumn(0)
        
        layout.addWidget(self.table)
        
        # Добавляем строку поиска
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(QtWidgets.QLabel("Поиск:"))
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Введите ID турнира или ключевое слово...")
        self.search_field.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_field)
        
        layout.addLayout(search_layout)
        
        self.setLayout(layout)

    def reload(self):
        tournaments = self.tournament_repo.get_all_hero_tournaments()
        
        # Применяем фильтры
        filtered_tournaments = self._apply_filters(tournaments)
        
        # Обновляем статистику
        self._update_stats(filtered_tournaments)
        
        # Обновляем таблицу
        self.table.setRowCount(0)
        for t in filtered_tournaments:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # ID турнира
            id_item = QtWidgets.QTableWidgetItem(str(t.get("tournament_id", "")))
            self.table.setItem(row, 0, id_item)
            
            # Название турнира (с иконкой типа)
            tournament_item = QtWidgets.QTableWidgetItem(str(t.get("tournament_id", "")))
            if "knockout" in str(t.get("tournament_id", "")).lower():
                tournament_item.setIcon(QtGui.QIcon.fromTheme("view-media-artist"))
            tournament_item.setToolTip(f"ID: {t.get('tournament_id', '')}")
            self.table.setItem(row, 1, tournament_item)
            
            # Место
            place_item = QtWidgets.QTableWidgetItem(str(t.get("place", "")))
            place_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            
            # Подсветка места разными цветами
            try:
                place = int(t.get("place", 0))
                if place == 1:
                    place_item.setForeground(QtGui.QBrush(QtGui.QColor(255, 215, 0)))  # Золото
                elif place == 2:
                    place_item.setForeground(QtGui.QBrush(QtGui.QColor(192, 192, 192)))  # Серебро
                elif place == 3:
                    place_item.setForeground(QtGui.QBrush(QtGui.QColor(205, 127, 50)))  # Бронза
                elif place <= 9:
                    place_item.setForeground(QtGui.QBrush(QtGui.QColor(46, 204, 113)))  # Зеленый для ITM
            except (ValueError, TypeError):
                pass
            self.table.setItem(row, 2, place_item)
            
            # Выплата
            payout = t.get("payout", 0)
            payout_item = QtWidgets.QTableWidgetItem(format_money(payout))
            payout_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(payout_item, payout)
            self.table.setItem(row, 3, payout_item)
            
            # KO
            ko_count = t.get("ko_count", 0)
            ko_item = QtWidgets.QTableWidgetItem(str(ko_count))
            ko_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, ko_item)
            
            # Бай-ин
            buyin = t.get("buyin", 0)
            buyin_item = QtWidgets.QTableWidgetItem(format_money(buyin))
            buyin_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, buyin_item)
            
            # Прибыль (выплата - бай-ин)
            profit = float(t.get("payout", 0)) - float(t.get("buyin", 0))
            profit_item = QtWidgets.QTableWidgetItem(format_money(profit, with_plus=True))
            profit_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(profit_item, profit)
            self.table.setItem(row, 6, profit_item)
            
            # Дата
            date_item = QtWidgets.QTableWidgetItem(str(t.get("date", ""))) if "date" in t else QtWidgets.QTableWidgetItem("")
            date_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 7, date_item)
        
        # Возвращаем поиск
        self.filter_table()

    def _apply_filters(self, tournaments):
        """Применяет выбранные фильтры к списку турниров"""
        # Копия списка для фильтрации
        filtered = tournaments.copy()
        
        # Фильтр по дате
        date_filter = self.date_filter.currentText()
        if date_filter != "Все даты":
            # Здесь должна быть логика фильтрации по дате
            # Для примера просто вернем исходный список
            pass
        
        # Фильтр по результату турнира
        tournament_filter = self.tournament_filter.currentText()
        if tournament_filter == "Только ITM":
            filtered = [t for t in filtered if isinstance(t.get("place", 0), int) and t.get("place", 0) <= 9]
        elif tournament_filter == "Только победы":
            filtered = [t for t in filtered if t.get("place", 0) == 1]
            
        return filtered

    def _update_stats(self, tournaments):
        """Обновляет виджеты статистики на основе текущего выбора"""
        # Количество турниров
        self.tournament_count.setText(f"Всего турниров: {len(tournaments)}")
        
        # Среднее место
        places = [t.get("place", 0) for t in tournaments if isinstance(t.get("place", 0), int)]
        avg_place = sum(places) / len(places) if places else 0
        self.avg_place.setText(f"Среднее место: {avg_place:.2f}")
        
        # Общая прибыль
        total_buyin = sum(float(t.get("buyin", 0)) for t in tournaments)
        total_payout = sum(float(t.get("payout", 0)) for t in tournaments)
        profit = total_payout - total_buyin
        self.total_profit.setText(f"Общая прибыль: {format_money(profit, with_plus=True)}")
        
        # Окрашиваем прибыль
        if profit > 0:
            self.total_profit.setStyleSheet("font-weight: bold; color: #2ecc71;")
        elif profit < 0:
            self.total_profit.setStyleSheet("font-weight: bold; color: #e74c3c;")
        else:
            self.total_profit.setStyleSheet("font-weight: bold;")
        
        # ROI
        roi = (profit / total_buyin * 100) if total_buyin > 0 else 0
        self.roi.setText(f"ROI: {roi:.2f}%")
        
        # Окрашиваем ROI
        if roi > 0:
            self.roi.setStyleSheet("font-weight: bold; color: #2ecc71;")
        elif roi < 0:
            self.roi.setStyleSheet("font-weight: bold; color: #e74c3c;")
        else:
            self.roi.setStyleSheet("font-weight: bold;")
    
    def filter_table(self):
        """Фильтрует таблицу по поисковому запросу"""
        search_text = self.search_field.text().lower()
        for row in range(self.table.rowCount()):
            show_row = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    show_row = True
                    break
            self.table.setRowHidden(row, not show_row)