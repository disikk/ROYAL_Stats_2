from PyQt6 import QtWidgets, QtGui, QtCore
from ui.app_style import setup_table_widget, format_money, apply_cell_color_by_value

class KnockoutTable(QtWidgets.QWidget):
    """
    Таблица всех нокаутов Hero (по турниру, по раздаче, с флагом split).
    """

    def __init__(self, knockout_repo, parent=None):
        super().__init__(parent)
        self.knockout_repo = knockout_repo
        self._init_ui()
        self.reload()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Верхний блок с заголовком и фильтрами
        header_layout = QtWidgets.QHBoxLayout()
        
        # Заголовок
        self.title_label = QtWidgets.QLabel("Нокауты игрока")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(self.title_label)
        
        # Поле поиска
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Поиск по турниру...")
        self.search_field.textChanged.connect(self.filter_table)
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(QtWidgets.QLabel("Поиск:"))
        search_layout.addWidget(self.search_field)
        header_layout.addLayout(search_layout)
        
        # Фильтр по типу нокаута
        self.ko_filter = QtWidgets.QComboBox()
        self.ko_filter.addItems(["Все нокауты", "Только Split KO", "Только обычные KO"])
        self.ko_filter.currentIndexChanged.connect(self.reload)
        
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Тип:"))
        filter_layout.addWidget(self.ko_filter)
        header_layout.addLayout(filter_layout)
        
        header_layout.addStretch()
        
        # Кнопка обновления
        self.refresh_btn = QtWidgets.QPushButton()
        self.refresh_btn.setIcon(QtGui.QIcon.fromTheme("view-refresh"))
        self.refresh_btn.setToolTip("Обновить данные")
        self.refresh_btn.clicked.connect(self.reload)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Блок с статистикой по нокаутам
        stats_layout = QtWidgets.QHBoxLayout()
        
        self.ko_count = QtWidgets.QLabel("Всего нокаутов: 0")
        self.ko_count.setStyleSheet("font-weight: bold;")
        
        self.split_count = QtWidgets.QLabel("Split нокаутов: 0")
        self.split_count.setStyleSheet("font-weight: bold;")
        
        self.unique_tournaments = QtWidgets.QLabel("Уникальных турниров: 0")
        self.unique_tournaments.setStyleSheet("font-weight: bold;")
        
        stats_layout.addWidget(self.ko_count)
        stats_layout.addWidget(self.split_count)
        stats_layout.addWidget(self.unique_tournaments)
        stats_layout.addStretch()
        
        # Добавляем разделитель
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        
        layout.addWidget(separator)
        layout.addLayout(stats_layout)
        layout.addWidget(separator)
        
        # Таблица нокаутов
        self.table = QtWidgets.QTableWidget(0, 6)  # Добавлены колонки для даты и стоимости
        self.table.setHorizontalHeaderLabels(["ID", "Турнир", "№ Раздачи", "Split KO", "Стоимость", "Дата"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        
        # Применяем улучшения к таблице
        setup_table_widget(self.table)
        
        # Скрываем колонку ID
        self.table.hideColumn(0)
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)

    def reload(self):
        knockouts = self.knockout_repo.get_hero_knockouts()
        
        # Применяем фильтр по типу нокаута
        ko_filter = self.ko_filter.currentText()
        if ko_filter == "Только Split KO":
            knockouts = [ko for ko in knockouts if ko.get("split")]
        elif ko_filter == "Только обычные KO":
            knockouts = [ko for ko in knockouts if not ko.get("split")]
        
        # Обновляем статистику
        self._update_stats(knockouts)
        
        # Обновляем таблицу
        self.table.setRowCount(0)
        for ko in knockouts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # ID 
            id_item = QtWidgets.QTableWidgetItem(str(ko.get("id", "")))
            self.table.setItem(row, 0, id_item)
            
            # Турнир
            tournament_id = ko.get("tournament_id", "")
            tournament_item = QtWidgets.QTableWidgetItem(str(tournament_id))
            tournament_item.setToolTip(f"ID турнира: {tournament_id}")
            self.table.setItem(row, 1, tournament_item)
            
            # № Раздачи
            hand_idx = ko.get("hand_idx", "")
            hand_item = QtWidgets.QTableWidgetItem(str(hand_idx))
            hand_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, hand_item)
            
            # Split KO
            is_split = ko.get("split", False)
            split_item = QtWidgets.QTableWidgetItem()
            split_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            
            # Используем иконки для наглядности
            if is_split:
                split_item.setText("Да")
                split_item.setIcon(QtGui.QIcon.fromTheme("emblem-shared"))
                split_item.setForeground(QtGui.QBrush(QtGui.QColor(46, 204, 113)))  # Зеленый
            else:
                split_item.setText("Нет")
                split_item.setIcon(QtGui.QIcon.fromTheme("user-away"))
            
            self.table.setItem(row, 3, split_item)
            
            # Стоимость (для примера, если в данных нет, можно добавить)
            ko_value = ko.get("value", 0)
            value_item = QtWidgets.QTableWidgetItem(format_money(ko_value))
            value_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(value_item, ko_value)
            self.table.setItem(row, 4, value_item)
            
            # Дата 
            date_item = QtWidgets.QTableWidgetItem(str(ko.get("date", ""))) if "date" in ko else QtWidgets.QTableWidgetItem("")
            date_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, date_item)
        
        # Применяем текущий поисковый фильтр
        self.filter_table()

    def _update_stats(self, knockouts):
        """Обновляет виджеты статистики нокаутов"""
        # Общее количество нокаутов
        self.ko_count.setText(f"Всего нокаутов: {len(knockouts)}")
        
        # Количество Split нокаутов
        split_kos = [ko for ko in knockouts if ko.get("split")]
        self.split_count.setText(f"Split нокаутов: {len(split_kos)}")
        
        # Количество уникальных турниров
        unique_tournaments = set(ko.get("tournament_id", "") for ko in knockouts)
        self.unique_tournaments.setText(f"Уникальных турниров: {len(unique_tournaments)}")
    
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