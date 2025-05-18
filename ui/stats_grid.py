from PyQt6 import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from ui.app_style import format_money, apply_cell_color_by_value

class StatCard(QtWidgets.QGroupBox):
    def __init__(self, name, value, parent=None, is_money=False, with_plus=False):
        super().__init__(parent)
        self.setTitle(name)
        self.is_money = is_money
        self.with_plus = with_plus
        
        self.value_label = QtWidgets.QLabel(self._format_value(value))
        font = self.value_label.font()
        font.setPointSize(14)
        font.setBold(True)
        self.value_label.setFont(font)
        self.value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # Добавляем иконку тренда (опционально)
        self.trend_icon = QtWidgets.QLabel()
        self.trend_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # Контейнер для верхней строки (значения и иконки тренда)
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addStretch()
        top_layout.addWidget(self.value_label)
        top_layout.addWidget(self.trend_icon)
        top_layout.addStretch()
        
        # Устанавливаем цвет текста в зависимости от значения для денежных показателей
        if is_money:
            try:
                val = float(value)
                if val > 0:
                    self.value_label.setStyleSheet("color: #2ecc71;")  # Зеленый
                    if self.trend_icon:
                        self.trend_icon.setPixmap(QtGui.QIcon.fromTheme("go-up").pixmap(16, 16))
                elif val < 0:
                    self.value_label.setStyleSheet("color: #e74c3c;")  # Красный
                    if self.trend_icon:
                        self.trend_icon.setPixmap(QtGui.QIcon.fromTheme("go-down").pixmap(16, 16))
            except (ValueError, TypeError):
                pass
        
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(top_layout)
        self.setLayout(layout)
        self.setFixedHeight(60)  # Компактнее
        
        # Тень для карточки
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QtGui.QColor(0, 0, 0, 80))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)

    def _format_value(self, value):
        if self.is_money:
            return format_money(value, self.with_plus)
        return str(value)

    def set_value(self, value):
        self.value_label.setText(self._format_value(value))
        
        # Обновляем цвет при изменении значения (для денежных показателей)
        if self.is_money:
            try:
                val = float(value)
                if val > 0:
                    self.value_label.setStyleSheet("color: #2ecc71;")  # Зеленый
                    if self.trend_icon:
                        self.trend_icon.setPixmap(QtGui.QIcon.fromTheme("go-up").pixmap(16, 16))
                elif val < 0:
                    self.value_label.setStyleSheet("color: #e74c3c;")  # Красный
                    if self.trend_icon:
                        self.trend_icon.setPixmap(QtGui.QIcon.fromTheme("go-down").pixmap(16, 16))
                else:
                    self.value_label.setStyleSheet("")
                    if self.trend_icon:
                        self.trend_icon.clear()
            except (ValueError, TypeError):
                pass


class StatsGrid(QtWidgets.QWidget):
    """
    Дашборд Hero: все ключевые статы в виде карточек + гистограмма мест
    """

    def __init__(self, stats_repo, tournament_repo, knockout_repo, session_repo, parent=None):
        super().__init__(parent)
        self.stats_repo = stats_repo
        self.tournament_repo = tournament_repo
        self.knockout_repo = knockout_repo
        self.session_repo = session_repo

        self.cards = []
        self.card_names = []
        self._init_ui()
        self.reload()

    def _init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # Заголовок дашборда
        header_layout = QtWidgets.QHBoxLayout()
        self.header_label = QtWidgets.QLabel("Статистика игрока")
        self.header_label.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(self.header_label)
        
        # Кнопка обновления с иконкой
        self.refresh_btn = QtWidgets.QPushButton()
        self.refresh_btn.setIcon(QtGui.QIcon.fromTheme("view-refresh"))
        self.refresh_btn.setToolTip("Обновить статистику")
        self.refresh_btn.clicked.connect(self.reload)
        header_layout.addWidget(self.refresh_btn)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Виджет прокрутки для всего содержимого
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        
        # --- Карточки статов (QGridLayout) ---
        self.cards_grid = QtWidgets.QGridLayout()
        self.cards_grid.setSpacing(16)
        self.cards_grid.setContentsMargins(8, 8, 8, 8)
        self.cards_widget = QtWidgets.QWidget()
        self.cards_widget.setLayout(self.cards_grid)
        scroll_layout.addWidget(self.cards_widget)
        
        # --- Заголовок для гистограммы ---
        chart_header = QtWidgets.QLabel("Распределение занятых мест")
        chart_header.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        chart_header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(chart_header)

        # --- Гистограмма распределения мест ---
        self.figure = Figure(figsize=(6, 3))
        # Устанавливаем фон в соответствии с темной темой
        self.figure.patch.set_facecolor('#353535')
        self.canvas = FigureCanvas(self.figure)
        scroll_layout.addWidget(self.canvas)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)

    def reload(self):
        tournaments = self.tournament_repo.get_all_hero_tournaments()
        knockouts = self.knockout_repo.get_hero_knockouts() if hasattr(self.knockout_repo, 'get_hero_knockouts') else []
        sessions = self.session_repo.get_all_hero_sessions() if hasattr(self.session_repo, 'get_all_hero_sessions') else []

        # --- Считаем все статы через плагины ---
        from stats.itm import ITMStat
        from stats.roi import ROIStat
        from stats.big_ko import BigKOStat
        from stats.total_ko import TotalKOStat

        plugins = [ITMStat(), ROIStat(), BigKOStat(), TotalKOStat()]
        stats_flat = []
        self.card_names = []
        
        # Определяем, какие статы являются денежными значениями
        money_stats = ["ROI", "Доход", "Прибыль", "Выплата", "Бай-ин"]

        # Отображаем только необходимые показатели
        required_keys = {
            "ITM": ["itm_percent"],
            "ROI": ["roi"],
            "Total KO": ["total_ko"],
            "Big KO": ["x1.5", "x2", "x10", "x100"],
        }

        for plugin in plugins:
            try:
                result = plugin.compute(tournaments, knockouts, sessions)

                # Какие ключи из результата нужно показать
                need_keys = required_keys.get(plugin.name, [])

                if isinstance(result, dict):
                    for k, v in result.items():
                        if k not in need_keys:
                            continue  # пропускаем лишние данные
                        # Проверяем, является ли стат денежным показателем
                        is_money = any(money_term in plugin.name or money_term in k for money_term in money_stats)
                        # Удобно отобразить человеко-читаемый заголовок
                        display_name = {
                            ("ITM", "itm_percent"): "ITM%",
                            ("ROI", "roi"): "ROI%",
                            ("Total KO", "total_ko"): "Нокауты",
                        }.get((plugin.name, k), f"{k}")
                        # Для Big KO выводим как x1.5 и т.п.
                        if plugin.name == "Big KO":
                            display_name = k
                        stats_flat.append((display_name, v, is_money))
                        self.card_names.append(display_name)
                else:
                    if not need_keys:
                        continue
                    # Если результат не словарь, но метрика одна (не используется сейчас)
                    is_money = any(money_term in plugin.name for money_term in money_stats)
                    display_name = plugin.name
                    stats_flat.append((display_name, result, is_money))
                    self.card_names.append(display_name)
            except Exception as e:
                stats_flat.append((plugin.name, f"Ошибка: {e}", False))
                self.card_names.append(plugin.name)

        # --- Рендерим карточки ---
        # Удалить старые карточки из layout
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.cards = []

        # Dynamically determine columns based on available width
        # StatCard has fixed height 100, let's assume a min/avg width for calculation
        # Min card width might be around 200-250px with title and value.
        # Spacing is 16px.
        card_min_width_plus_spacing = 140 + self.cards_grid.spacing() 
        
        # Use the width of the container for cards, or StatsGrid itself as a fallback
        container_width = self.cards_widget.width()
        if container_width <= 0: # If not yet sized (e.g. during init)
            container_width = self.width()
        if container_width <= 0: # Still not sized (e.g. hidden tab)
            container_width = 800 # Default reasonable width
            
        cols = max(1, int(container_width / card_min_width_plus_spacing))
        # Cap columns to a reasonable max, e.g., 5 or 6, to avoid tiny cards if width is huge
        cols = min(cols, 6) 

        for i, (name, value, is_money) in enumerate(stats_flat):
            card = StatCard(name, value, is_money=is_money, with_plus="ROI" in name)
            self.cards.append(card)
            self.cards_grid.addWidget(card, i // cols, i % cols)

        # --- Гистограмма ---
        self._update_places_chart(tournaments)

    def _update_places_chart(self, tournaments):
        distribution = self._place_distribution(tournaments)
        self.figure.clear()
        
        # Получаем текущие цвета из темы приложения
        bg_color = '#353535'  # Фон графика
        text_color = '#ffffff'  # Цвет текста
        grid_color = '#555555'  # Цвет сетки
        bar_color = '#2a82da'  # Основной цвет для столбцов
        
        # Настраиваем стиль графика для темной темы
        plt.style.use('dark_background')
        
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(bg_color)
        
        places = list(range(1, 10))
        counts = [distribution[p][0] for p in places]
        percentages = [distribution[p][1] for p in places]
        
        # Создаем градиент цветов для столбцов: первые места - зеленые, последние - красные
        colors = ['#27ae60', '#2ecc71', '#3498db', '#3498db', '#f1c40f', 
                 '#f1c40f', '#e67e22', '#e67e22', '#e74c3c'][:len(places)]
        
        bars = ax.bar(places, counts, color=colors)
        
        # Добавляем проценты над столбцами
        for i, (bar, percentage) in enumerate(zip(bars, percentages)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{percentage}%',
                    ha='center', va='bottom', color=text_color, fontweight='bold')
        
        ax.set_title("Распределение занятых мест", color=text_color, fontsize=14, pad=20)
        ax.set_xlabel("Место", color=text_color, fontsize=12)
        ax.set_ylabel("Количество турниров", color=text_color, fontsize=12)
        ax.set_xticks(places)
        ax.tick_params(colors=text_color)
        
        # Настраиваем внешний вид сетки
        ax.grid(True, linestyle='--', alpha=0.3, color=grid_color)
        
        # Добавляем общее количество турниров в заголовок
        total_tournaments = sum(counts)
        ax.set_title(f"Распределение занятых мест (всего турниров: {total_tournaments})", 
                     color=text_color, fontsize=14, pad=20)
        
        # Удаляем рамку
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        self.figure.tight_layout()
        self.canvas.draw()

    @staticmethod
    def _place_distribution(tournaments, places=9):
        counter = {i: 0 for i in range(1, places + 1)}
        total = len(tournaments)
        if total == 0:
            return {i: (0, 0.0) for i in range(1, places + 1)}
        for t in tournaments:
            place = t.get("place") if isinstance(t, dict) else getattr(t, "place", None)
            if isinstance(place, int) and 1 <= place <= places:
                counter[place] += 1
        return {place: (count, round(count / total * 100, 2)) for place, count in counter.items()}