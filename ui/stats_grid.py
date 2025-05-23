# -*- coding: utf-8 -*-

"""
Компонент для отображения общей статистики и графиков.
Отображает карточки с ключевыми показателями и гистограмму распределения мест.
"""

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
import logging
from typing import Dict, List, Any

import config
from application_service import ApplicationService
from models import OverallStats

# Импортируем функции стилизации
from ui.app_style import format_money, format_percentage, apply_cell_color_by_value

# Импортируем плагины для получения их результатов
from stats import (
    TotalKOStat,
    ITMStat,
    ROIStat,
    BigKOStat,
    AvgKOPerTournamentStat,
    FinalTableReachStat,
    AvgFTInitialStackStat,
    EarlyFTKOStat,
)

logger = logging.getLogger('ROYAL_Stats.StatsGrid')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)


class StatCard(QtWidgets.QFrame):
    """Карточка для отображения одного показателя статистики."""
    
    def __init__(self, title: str, value: str = "-", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QtWidgets.QFrame.Shape.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: #27272A;
                border-radius: 8px;
                padding: 4px 8px;
                border: 1px solid #3F3F46;
            }
            QFrame:hover {
                border: 1px solid #52525B;
                background-color: #2D2D30;
            }
        """)
        
        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 12px;
                font-weight: 500;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.title_label)
        
        # Растягиваем пространство между заголовком и значением
        layout.addStretch()
        
        self.value_label = QtWidgets.QLabel(value)
        self.value_label.setStyleSheet("""
            QLabel {
                color: #FAFAFA;
                font-size: 18px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.value_label)
        
        # Сохраняем subtitle для специальных карточек
        self.subtitle = subtitle
        
    def update_value(self, value: str, subtitle: str = ""):
        """Обновляет значение карточки."""
        self.value_label.setText(value)
        self.subtitle = subtitle


class SpecialStatCard(QtWidgets.QFrame):
    """Специальная карточка для статов с переносом строки (FT стек и Early FT KO)."""
    
    def __init__(self, title: str, value: str = "-", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QtWidgets.QFrame.Shape.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: #27272A;
                border-radius: 8px;
                padding: 4px 8px;
                border: 1px solid #3F3F46;
            }
            QFrame:hover {
                border: 1px solid #52525B;
                background-color: #2D2D30;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Верхняя строка с заголовком и значением
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setSpacing(4)
        
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 12px;
                font-weight: 500;
                background-color: transparent;
            }
        """)
        top_layout.addWidget(self.title_label)
        
        top_layout.addStretch()
        
        self.value_label = QtWidgets.QLabel(value)
        self.value_label.setStyleSheet("""
            QLabel {
                color: #FAFAFA;
                font-size: 18px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        top_layout.addWidget(self.value_label)
        
        layout.addLayout(top_layout)
        
        # Подзаголовок (для отображения дополнительной информации)
        if subtitle:
            self.subtitle_label = QtWidgets.QLabel(subtitle)
            self.subtitle_label.setStyleSheet("""
                QLabel {
                    color: #71717A;
                    font-size: 11px;
                    background-color: transparent;
                    margin-top: 0px;
                }
            """)
            self.subtitle_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            layout.addWidget(self.subtitle_label)
        else:
            self.subtitle_label = None
            
    def update_value(self, value: str, subtitle: str = ""):
        """Обновляет значение и подзаголовок карточки."""
        self.value_label.setText(value)
        if self.subtitle_label and subtitle:
            self.subtitle_label.setText(subtitle)
        elif subtitle and not self.subtitle_label:
            self.subtitle_label = QtWidgets.QLabel(subtitle)
            self.subtitle_label.setStyleSheet("""
                QLabel {
                    color: #71717A;
                    font-size: 11px;
                    background-color: transparent;
                    margin-top: 0px;
                }
            """)
            self.subtitle_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            self.layout().addWidget(self.subtitle_label)


class StatsGrid(QtWidgets.QWidget):
    """Виджет с сеткой статистических показателей и графиками."""
    
    def __init__(self, app_service: ApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        self._init_ui()
        
    def _init_ui(self):
        """Инициализирует UI компоненты."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Создаем QScrollArea для всего содержимого
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        
        # Контейнер для всего содержимого
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)
        
        # Заголовок
        header = QtWidgets.QLabel("Общая статистика")
        header.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #FAFAFA;
                margin-bottom: 4px;
            }
        """)
        content_layout.addWidget(header)
        
        # Сетка карточек статистики
        stats_grid = QtWidgets.QGridLayout()
        stats_grid.setSpacing(3)
        
        # Создаем карточки для основных показателей
        self.cards = {
            'tournaments': StatCard("Турниров сыграно", "-"),
            'knockouts': StatCard("Всего нокаутов", "-"),
            'avg_ko': StatCard("Среднее KO за турнир", "-"),
            'roi': StatCard("ROI", "-"),
            'itm': StatCard("ITM%", "-"),
            'ft_reach': StatCard("% Достижения FT", "-"),
            'avg_ft_stack': SpecialStatCard("Средний стек на FT", "-"),
            'early_ft_ko': SpecialStatCard("KO в ранней FT", "-"),
        }
        
        # Размещаем карточки в сетке (4 колонки)
        positions = [
            ('tournaments', 0, 0), ('knockouts', 0, 1), ('avg_ko', 0, 2), ('roi', 0, 3),
            ('itm', 1, 0), ('ft_reach', 1, 1), ('avg_ft_stack', 1, 2), ('early_ft_ko', 1, 3),
        ]
        
        for key, row, col in positions:
            stats_grid.addWidget(self.cards[key], row, col)
            
        content_layout.addLayout(stats_grid)
        
        # Разделитель
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { background-color: #3F3F46; max-height: 1px; margin: 5px 0; }")
        content_layout.addWidget(separator)
        
        # График распределения мест
        chart_header = QtWidgets.QLabel("Распределение финишных мест на финальном столе")
        chart_header.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #FAFAFA;
                margin-bottom: 3px;
            }
        """)
        content_layout.addWidget(chart_header)
        
        # Создаем виджет для графика
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumHeight(350)
        self.chart_view.setMaximumHeight(450)
        content_layout.addWidget(self.chart_view)
        
        # Разделитель
        separator2 = QtWidgets.QFrame()
        separator2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator2.setStyleSheet("QFrame { background-color: #3F3F46; max-height: 1px; margin: 5px 0; }")
        content_layout.addWidget(separator2)
        
        # Карточки для Big KO
        bigko_header = QtWidgets.QLabel("Статистика больших нокаутов")
        bigko_header.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #FAFAFA;
                margin-top: 1px;
                margin-bottom: 3px;
            }
        """)
        content_layout.addWidget(bigko_header)
        
        # Горизонтальный layout для всех карточек Big KO в одну строку
        bigko_layout = QtWidgets.QHBoxLayout()
        bigko_layout.setSpacing(3)
        
        self.bigko_cards = {
            'x1.5': StatCard("KO x1.5", "-"),
            'x2': StatCard("KO x2", "-"),
            'x10': StatCard("KO x10", "-"),
            'x100': StatCard("KO x100", "-"),
            'x1000': StatCard("KO x1000", "-"),
            'x10000': StatCard("KO x10000", "-"),
        }
        
        # Добавляем все карточки Big KO в горизонтальный layout
        for key in ['x1.5', 'x2', 'x10', 'x100', 'x1000', 'x10000']:
            bigko_layout.addWidget(self.bigko_cards[key])
            
        content_layout.addLayout(bigko_layout)
        
        # Добавляем отступ внизу
        content_layout.addSpacing(5)
        
        # Устанавливаем контент в scroll area
        scroll_area.setWidget(content_widget)
        
        # Добавляем scroll area в основной layout
        main_layout.addWidget(scroll_area)
        
    def reload(self):
        """Перезагружает все данные из ApplicationService."""
        logger.debug("=== Начало reload StatsGrid ===")
        logger.debug("Обновление UI StatsGrid...")
        overall_stats = self.app_service.get_overall_stats()
        logger.debug(f"Overall stats: tournaments={overall_stats.total_tournaments}, ko={overall_stats.total_knockouts}")
        all_tournaments = self.app_service.get_all_tournaments()
        
        self.cards['tournaments'].update_value(str(overall_stats.total_tournaments))
        logger.debug(f"Обновлена карточка tournaments: {overall_stats.total_tournaments}")
        
        self.cards['knockouts'].update_value(str(overall_stats.total_knockouts))
        logger.debug(f"Обновлена карточка knockouts: {overall_stats.total_knockouts}")
        
        self.cards['avg_ko'].update_value(f"{overall_stats.avg_ko_per_tournament:.2f}")
        logger.debug(f"Обновлена карточка avg_ko: {overall_stats.avg_ko_per_tournament:.2f}")
        
        roi_result = ROIStat().compute([], [], [], overall_stats)
        logger.debug(f"ROI result: {roi_result}")
        roi_value = roi_result.get('roi', 0.0)
        roi_text = f"{roi_value:+.1f}%"
        self.cards['roi'].update_value(roi_text)
        logger.debug(f"Обновлена карточка roi: {roi_text}")
        # Применяем цвет только к тексту, а не к фону
        apply_cell_color_by_value(self.cards['roi'].value_label, roi_value)
        
        itm_result = ITMStat().compute(all_tournaments, [], [], overall_stats)
        logger.debug(f"ITM result: {itm_result}")
        itm_value = itm_result.get('itm_percent', 0.0)
        self.cards['itm'].update_value(f"{itm_value:.1f}%")
        logger.debug(f"Обновлена карточка itm: {itm_value:.1f}%")
        
        ft_reach_result = FinalTableReachStat().compute(all_tournaments, [], [], overall_stats)
        logger.debug(f"FT Reach result: {ft_reach_result}")
        ft_reach_value = ft_reach_result.get('final_table_reach_percent', 0.0)
        self.cards['ft_reach'].update_value(f"{ft_reach_value:.1f}%")
        logger.debug(f"Обновлена карточка ft_reach: {ft_reach_value:.1f}%")
        
        avg_ft_stack_result = AvgFTInitialStackStat().compute(all_tournaments, [], [], overall_stats)
        logger.debug(f"Avg FT Stack result: {avg_ft_stack_result}")
        avg_chips = avg_ft_stack_result.get('avg_ft_initial_stack_chips', 0.0)
        avg_bb = avg_ft_stack_result.get('avg_ft_initial_stack_bb', 0.0)
        # Форматируем основное значение и подзаголовок
        self.cards['avg_ft_stack'].update_value(
            f"{avg_chips:,.0f}",
            f"{avg_chips:,.0f} фишек / {avg_bb:.1f} BB"
        )
        logger.debug(f"Обновлена карточка avg_ft_stack: {avg_chips:,.0f} / {avg_bb:.1f} BB")
        
        early_ft_result = EarlyFTKOStat().compute([], [], [], overall_stats)
        logger.debug(f"Early FT KO result: {early_ft_result}")
        early_ko_count = early_ft_result.get('early_ft_ko_count', 0)
        early_ko_per = early_ft_result.get('early_ft_ko_per_tournament', 0.0)
        # Форматируем основное значение и подзаголовок
        self.cards['early_ft_ko'].update_value(
            str(early_ko_count),
            f"{early_ko_per:.2f} за турнир с FT"
        )
        logger.debug(f"Обновлена карточка early_ft_ko: {early_ko_count} / {early_ko_per:.2f}")
        
        self.bigko_cards['x1.5'].update_value(str(overall_stats.big_ko_x1_5))
        self.bigko_cards['x2'].update_value(str(overall_stats.big_ko_x2))
        self.bigko_cards['x10'].update_value(str(overall_stats.big_ko_x10))
        self.bigko_cards['x100'].update_value(str(overall_stats.big_ko_x100))
        self.bigko_cards['x1000'].update_value(str(overall_stats.big_ko_x1000))
        self.bigko_cards['x10000'].update_value(str(overall_stats.big_ko_x10000))
        logger.debug(f"Обновлены карточки Big KO: x1.5={overall_stats.big_ko_x1_5}, x2={overall_stats.big_ko_x2}, x10={overall_stats.big_ko_x10}, x100={overall_stats.big_ko_x100}, x1000={overall_stats.big_ko_x1000}, x10000={overall_stats.big_ko_x10000}")
        
        self._update_chart()
        logger.debug("=== Конец reload StatsGrid ===")
        
    def _update_chart(self):
        """Обновляет гистограмму распределения мест."""
        place_dist = self.app_service.get_place_distribution()
        
        # Проверяем, есть ли данные
        if not place_dist or all(count == 0 for count in place_dist.values()):
            logger.warning("Нет данных для построения гистограммы распределения мест")
            chart = QChart()
            chart.setTitle("Нет данных о финишах на финальном столе")
            chart.setTheme(QChart.ChartTheme.ChartThemeDark)
            chart.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#18181B")))
            self.chart_view.setChart(chart)
            return
            
        chart = QChart()
        chart.setTitle("")  # Убираем заголовок, так как он уже есть над графиком
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setTheme(QChart.ChartTheme.ChartThemeDark)
        chart.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#18181B")))
        chart.legend().setVisible(False)
        
        # Создаем серию баров
        series = QBarSeries()
        
        # Создаем один QBarSet со всеми значениями
        bar_set = QBarSet("")
        
        # Добавляем значения для каждого места
        for place in range(1, 10):
            count = place_dist.get(place, 0)
            bar_set.append(count)
            
        series.append(bar_set)
        chart.addSeries(series)
        
        # Настройка оси X (категории) - места от 1 до 9
        axis_x = QBarCategoryAxis()
        axis_x.append([str(i) for i in range(1, 10)])
        axis_x.setTitleText("Место")
        axis_x.setLabelsColor(QtGui.QColor("#E4E4E7"))
        axis_x.setGridLineVisible(False)
        
        # Настройка оси Y (значения)
        axis_y = QValueAxis()
        axis_y.setTitleText("Количество финишей")
        axis_y.setLabelsColor(QtGui.QColor("#E4E4E7"))
        axis_y.setGridLineColor(QtGui.QColor("#3F3F46"))
        axis_y.setMinorGridLineVisible(False)
        
        max_count = max(place_dist.values()) if place_dist.values() else 1
        axis_y.setRange(0, max_count * 1.1)
        
        if max_count <= 10:
            axis_y.setTickCount(max_count + 1)
        else:
            axis_y.setTickCount(min(11, max_count // 5 + 1))
            
        axis_y.setLabelFormat("%d")
        
        # Привязываем оси к графику
        chart.addAxis(axis_x, QtCore.Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, QtCore.Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        
        # Устанавливаем отступы для графика
        chart.setMargins(QtCore.QMargins(10, 10, 10, 10))
        
        # Настраиваем цвета для столбцов через делегат отрисовки
        colors = [
            "#10B981",  # 1 место - ярко-зеленый
            "#34D399",  # 2 место - зеленый
            "#6EE7B7",  # 3 место - светло-зеленый
            "#FCD34D",  # 4 место - желтый
            "#F59E0B",  # 5 место - оранжевый
            "#EF4444",  # 6 место - красный
            "#DC2626",  # 7 место - темно-красный
            "#B91C1C",  # 8 место - еще темнее
            "#991B1B",  # 9 место - самый темный красный
        ]
        
        # Применяем градиент к bar_set
        gradient = QtGui.QLinearGradient(0, 0, 1, 0)
        gradient.setCoordinateMode(QtGui.QGradient.CoordinateMode.ObjectBoundingMode)
        gradient.setColorAt(0.0, QtGui.QColor(colors[0]))
        gradient.setColorAt(0.5, QtGui.QColor(colors[4]))
        gradient.setColorAt(1.0, QtGui.QColor(colors[8]))
        bar_set.setBrush(QtGui.QBrush(gradient))
        
        self.chart_view.setChart(chart)