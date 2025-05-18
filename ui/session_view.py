from PyQt6 import QtWidgets, QtGui, QtCore
from ui.app_style import setup_table_widget, format_money, apply_cell_color_by_value
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class SessionView(QtWidgets.QWidget):
    """
    Таблица всех сессий Hero: список турниров, общий бай-ин, выплаты, KO.
    """

    def __init__(self, session_repo, parent=None):
        super().__init__(parent)
        self.session_repo = session_repo
        self._init_ui()
        self.reload()

    def _init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # Верхний блок с заголовком и поиском
        header_layout = QtWidgets.QHBoxLayout()
        
        # Заголовок
        self.title_label = QtWidgets.QLabel("Игровые сессии")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(self.title_label)
        
        # Поле поиска
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Поиск по сессиям...")
        self.search_field.textChanged.connect(self.filter_table)
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(QtWidgets.QLabel("Поиск:"))
        search_layout.addWidget(self.search_field)
        header_layout.addLayout(search_layout)
        
        header_layout.addStretch()
        
        # Кнопка обновления
        self.refresh_btn = QtWidgets.QPushButton()
        self.refresh_btn.setIcon(QtGui.QIcon.fromTheme("view-refresh"))
        self.refresh_btn.setToolTip("Обновить данные")
        self.refresh_btn.clicked.connect(self.reload)
        header_layout.addWidget(self.refresh_btn)
        
        main_layout.addLayout(header_layout)
        
        # Создаем разделитель на две части: слева таблица, справа графики
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        
        # Левая часть: таблица и статистика
        table_widget = QtWidgets.QWidget()
        table_layout = QtWidgets.QVBoxLayout(table_widget)
        
        # Статистика сессий
        stats_layout = QtWidgets.QHBoxLayout()
        
        self.session_count = QtWidgets.QLabel("Всего сессий: 0")
        self.session_count.setStyleSheet("font-weight: bold;")
        
        self.total_profit = QtWidgets.QLabel("Общая прибыль: 0.00 ₽")
        self.total_profit.setStyleSheet("font-weight: bold;")
        
        self.avg_buyin = QtWidgets.QLabel("Средний бай-ин: 0.00 ₽")
        self.avg_buyin.setStyleSheet("font-weight: bold;")
        
        stats_layout.addWidget(self.session_count)
        stats_layout.addWidget(self.total_profit)
        stats_layout.addWidget(self.avg_buyin)
        stats_layout.addStretch()
        
        # Добавляем разделитель
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        
        table_layout.addLayout(stats_layout)
        table_layout.addWidget(separator)
        
        # Таблица сессий
        self.table = QtWidgets.QTableWidget(0, 7)  # Добавлены колонки для прибыли и даты
        self.table.setHorizontalHeaderLabels(["ID", "Сессия", "Турниры", "Бай-ин", "Выплата", "KO", "Прибыль", "Дата"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        
        # Применяем улучшения к таблице
        setup_table_widget(self.table)
        
        # Скрываем колонку ID
        self.table.hideColumn(0)
        
        # Подключаем сигнал выбора строки для обновления графика
        self.table.itemSelectionChanged.connect(self.update_graph)
        
        table_layout.addWidget(self.table)
        
        # Правая часть: графики
        graph_widget = QtWidgets.QWidget()
        graph_layout = QtWidgets.QVBoxLayout(graph_widget)
        
        # Заголовок графиков
        graph_title = QtWidgets.QLabel("Динамика прибыли")
        graph_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        graph_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        graph_layout.addWidget(graph_title)
        
        # График динамики прибыли
        self.figure = Figure(figsize=(4, 4))
        self.figure.patch.set_facecolor('#353535')  # Фон графика для темной темы
        self.canvas = FigureCanvas(self.figure)
        graph_layout.addWidget(self.canvas)
        
        # Круговая диаграмма распределения выигрышей
        self.pie_figure = Figure(figsize=(4, 4))
        self.pie_figure.patch.set_facecolor('#353535')  # Фон графика для темной темы
        self.pie_canvas = FigureCanvas(self.pie_figure)
        graph_layout.addWidget(self.pie_canvas)
        
        # Добавляем виджеты в разделитель
        splitter.addWidget(table_widget)
        splitter.addWidget(graph_widget)
        
        # Устанавливаем соотношение размеров
        splitter.setSizes([600, 400])
        
        main_layout.addWidget(splitter)
        
        self.setLayout(main_layout)

    def reload(self):
        sessions = self.session_repo.get_all_hero_sessions()
        
        # Обновляем статистику
        self._update_stats(sessions)
        
        # Обновляем таблицу
        self.table.setRowCount(0)
        for s in sessions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # ID
            id_item = QtWidgets.QTableWidgetItem(str(s.get("id", "")))
            self.table.setItem(row, 0, id_item)
            
            # Сессия (название/идентификатор)
            session_id = s.get("session_id", "")
            session_item = QtWidgets.QTableWidgetItem(str(session_id))
            session_item.setToolTip(f"ID сессии: {session_id}")
            self.table.setItem(row, 1, session_item)
            
            # Турниры (список через запятую)
            tournaments = s.get("tournaments", [])
            tournaments_text = ", ".join(tournaments) if tournaments else ""
            tournament_item = QtWidgets.QTableWidgetItem(tournaments_text)
            tournament_item.setToolTip(tournaments_text)
            self.table.setItem(row, 2, tournament_item)
            
            # Бай-ин
            buyin = s.get("total_buyin", 0)
            buyin_item = QtWidgets.QTableWidgetItem(format_money(buyin))
            buyin_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, buyin_item)
            
            # Выплата
            payout = s.get("total_payout", 0)
            payout_item = QtWidgets.QTableWidgetItem(format_money(payout))
            payout_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(payout_item, payout)
            self.table.setItem(row, 4, payout_item)
            
            # KO
            ko = s.get("total_ko", 0)
            ko_item = QtWidgets.QTableWidgetItem(format_money(ko))
            ko_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(ko_item, ko)
            self.table.setItem(row, 5, ko_item)
            
            # Прибыль (выплата + KO - бай-ин)
            profit = float(payout) + float(ko) - float(buyin)
            profit_item = QtWidgets.QTableWidgetItem(format_money(profit, with_plus=True))
            profit_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            apply_cell_color_by_value(profit_item, profit)
            self.table.setItem(row, 6, profit_item)
            
            # Дата
            date_item = QtWidgets.QTableWidgetItem(str(s.get("date", ""))) if "date" in s else QtWidgets.QTableWidgetItem("")
            date_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 7, date_item)
        
        # Обновляем графики
        self._update_profit_graph(sessions)
        self._update_pie_chart(sessions)
        
        # Применяем текущий поисковый фильтр
        self.filter_table()

    def _update_stats(self, sessions):
        """Обновляет виджеты статистики сессий"""
        # Количество сессий
        self.session_count.setText(f"Всего сессий: {len(sessions)}")
        
        # Общая прибыль
        total_buyin = sum(float(s.get("total_buyin", 0)) for s in sessions)
        total_payout = sum(float(s.get("total_payout", 0)) for s in sessions)
        total_ko = sum(float(s.get("total_ko", 0)) for s in sessions)
        profit = total_payout + total_ko - total_buyin
        self.total_profit.setText(f"Общая прибыль: {format_money(profit, with_plus=True)}")
        
        # Окрашиваем прибыль
        if profit > 0:
            self.total_profit.setStyleSheet("font-weight: bold; color: #2ecc71;")
        elif profit < 0:
            self.total_profit.setStyleSheet("font-weight: bold; color: #e74c3c;")
        else:
            self.total_profit.setStyleSheet("font-weight: bold;")
        
        # Средний бай-ин
        avg_buyin = total_buyin / len(sessions) if sessions else 0
        self.avg_buyin.setText(f"Средний бай-ин: {format_money(avg_buyin)}")
    
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
    
    def update_graph(self):
        """Обновляет графики при выборе сессии в таблице"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # Получаем выбранную сессию
        row = selected_rows[0].row()
        session_id = self.table.item(row, 1).text()
        
        # Здесь можно добавить логику для обновления графиков для конкретной сессии
        # Например, показать распределение выигрышей по турнирам в сессии
        
    def _update_profit_graph(self, sessions):
        """Обновляет график динамики прибыли"""
        self.figure.clear()
        
        # Настраиваем стиль для темной темы
        plt.style.use('dark_background')
        
        # Цвета для темной темы
        bg_color = '#353535'  # Фон графика
        text_color = '#ffffff'  # Цвет текста
        grid_color = '#555555'  # Цвет сетки
        line_color = '#2a82da'  # Цвет линии
        
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(bg_color)
        
        # Проверяем, есть ли данные для отображения
        if not sessions:
            ax.set_title("Нет данных для отображения", color=text_color)
            self.figure.tight_layout()
            self.canvas.draw()
            return
        
        # Подготавливаем данные (сортируем по дате, если есть)
        # Для примера - просто используем индексы сессий
        dates = list(range(len(sessions)))
        profits = []
        cumulative_profit = 0
        
        for s in sessions:
            buyin = float(s.get("total_buyin", 0))
            payout = float(s.get("total_payout", 0))
            ko = float(s.get("total_ko", 0))
            profit = payout + ko - buyin
            cumulative_profit += profit
            profits.append(cumulative_profit)
        
        # Проверяем, есть ли данные после обработки
        if not profits:
            ax.set_title("Нет данных для отображения", color=text_color)
            self.figure.tight_layout()
            self.canvas.draw()
            return
            
        # Рисуем график
        ax.plot(dates, profits, 'o-', color=line_color, linewidth=2)
        
        # Заполняем область под линией - проверяем последнее значение
        fill_color = line_color if profits[-1] > 0 else '#e74c3c'
        ax.fill_between(dates, 0, profits, alpha=0.3, color=fill_color)
        
        # Добавляем линию y=0
        ax.axhline(y=0, color='#e74c3c', linestyle='--', alpha=0.7)
        
        # Настраиваем оси и подписи
        ax.set_xlabel("Номер сессии", color=text_color)
        ax.set_ylabel("Накопленная прибыль, ₽", color=text_color)
        ax.set_title("Динамика прибыли", color=text_color, fontsize=14)
        ax.tick_params(colors=text_color)
        
        # Аннотации для важных точек
        if profits:
            max_profit = max(profits)
            min_profit = min(profits)
            max_idx = profits.index(max_profit)
            min_idx = profits.index(min_profit)
            
            # Аннотация для максимума
            ax.annotate(f"{format_money(max_profit)}", 
                         xy=(max_idx, max_profit),
                         xytext=(max_idx, max_profit + (max_profit * 0.1 if max_profit > 0 else max_profit * 0.1)),
                         color='#2ecc71',
                         fontweight='bold',
                         arrowprops=dict(facecolor='#2ecc71', shrink=0.05, alpha=0.7),
                         ha='center')
            
            # Аннотация для минимума (если отрицательный)
            if min_profit < 0:
                ax.annotate(f"{format_money(min_profit)}", 
                             xy=(min_idx, min_profit),
                             xytext=(min_idx, min_profit - (abs(min_profit) * 0.1)),
                             color='#e74c3c',
                             fontweight='bold',
                             arrowprops=dict(facecolor='#e74c3c', shrink=0.05, alpha=0.7),
                             ha='center')
        
        # Настраиваем сетку
        ax.grid(True, linestyle='--', alpha=0.3, color=grid_color)
        
        # Удаляем рамку
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _update_pie_chart(self, sessions):
        """Обновляет круговую диаграмму распределения прибыли"""
        self.pie_figure.clear()
        
        # Настраиваем стиль для темной темы
        plt.style.use('dark_background')
        
        # Цвета для темной темы
        bg_color = '#353535'  # Фон графика
        text_color = '#ffffff'  # Цвет текста
        
        # Цвета для диаграммы
        colors = ['#2ecc71', '#3498db', '#e74c3c', '#f1c40f', '#9b59b6']
        
        ax = self.pie_figure.add_subplot(111)
        ax.set_facecolor(bg_color)
        
        # Готовим данные
        if not sessions:
            # Если нет данных, рисуем пустую диаграмму
            ax.set_title("Нет данных для отображения", color=text_color)
            self.pie_figure.tight_layout()
            self.pie_canvas.draw()
            return
        
        # Для примера: распределение прибыли по разным компонентам
        total_buyin = sum(float(s.get("total_buyin", 0)) for s in sessions)
        total_payout = sum(float(s.get("total_payout", 0)) for s in sessions)
        total_ko = sum(float(s.get("total_ko", 0)) for s in sessions)
        
        # Проверяем, что есть какие-то ненулевые значения для диаграммы
        if total_buyin == 0 and total_payout == 0 and total_ko == 0:
            ax.set_title("Нет данных для отображения", color=text_color)
            self.pie_figure.tight_layout()
            self.pie_canvas.draw()
            return
        
        # Абсолютные значения для диаграммы
        labels = ['Бай-ины', 'Выплаты', 'Нокауты']
        sizes = [total_buyin, total_payout, total_ko]
        
        # Вычисляем прибыль
        profit = total_payout + total_ko - total_buyin
        
        # Рисуем круговую диаграмму
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            shadow=True,
            wedgeprops=dict(width=0.5)  # Создаем кольцевую диаграмму
        )
        
        # Настраиваем внешний вид
        for text in texts:
            text.set_color(text_color)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title("Распределение денежных потоков", color=text_color, fontsize=14)
        
        # Добавляем текст с итоговой прибылью в центр
        ax.text(0, 0, f"Прибыль:\n{format_money(profit)}", 
                ha='center', va='center', 
                fontsize=12, fontweight='bold',
                color='#2ecc71' if profit >= 0 else '#e74c3c')
        
        # Убираем рамку
        ax.set_frame_on(False)
        
        self.pie_figure.tight_layout()
        self.pie_canvas.draw()