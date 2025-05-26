# -*- coding: utf-8 -*-

"""
Стили и функции форматирования для приложения Royal Stats.
"""

from PyQt6 import QtWidgets, QtGui, QtCore
from typing import Optional


def apply_dark_theme(app: QtWidgets.QApplication):
    """Применяет темную тему к приложению."""
    app.setStyle("Fusion")
    
    # Основная палитра темной темы
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(24, 24, 27))  # #18181B
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(244, 244, 245))  # #F4F4F5
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(39, 39, 42))  # #27272A
    palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(45, 45, 48))  # #2D2D30
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtCore.Qt.GlobalColor.black)
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtCore.Qt.GlobalColor.white)
    palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(228, 228, 231))  # #E4E4E7
    palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(63, 63, 70))  # #3F3F46
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(244, 244, 245))  # #F4F4F5
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtCore.Qt.GlobalColor.red)
    palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(59, 130, 246))  # #3B82F6
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(59, 130, 246))  # #3B82F6
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtCore.Qt.GlobalColor.white)
    
    app.setPalette(palette)
    
    # Дополнительные стили для виджетов
    app.setStyleSheet("""
        QToolTip {
            color: #FAFAFA;
            background-color: #27272A;
            border: 1px solid #3F3F46;
            padding: 4px;
            border-radius: 4px;
        }
        
        QMenu {
            background-color: #27272A;
            border: 1px solid #3F3F46;
            padding: 4px;
            border-radius: 8px;
        }
        
        QMenu::item {
            padding: 8px 20px;
            border-radius: 4px;
        }
        
        QMenu::item:selected {
            background-color: #3F3F46;
        }
        
        QPushButton {
            background-color: #3F3F46;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 500;
        }
        
        QPushButton:hover {
            background-color: #52525B;
        }
        
        QPushButton:pressed {
            background-color: #27272A;
        }
        
        QLineEdit {
            background-color: #27272A;
            border: 1px solid #3F3F46;
            padding: 8px;
            border-radius: 6px;
            selection-background-color: #3B82F6;
        }
        
        QLineEdit:focus {
            border: 1px solid #3B82F6;
        }
        
        QComboBox {
            background-color: #27272A;
            border: 1px solid #3F3F46;
            padding: 6px 12px;
            border-radius: 6px;
            min-width: 100px;
        }
        
        QComboBox:hover {
            border: 1px solid #52525B;
        }
        
        QComboBox::drop-down {
            border: none;
            padding-right: 8px;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #A1A1AA;
            margin-right: 5px;
        }

        /* Подсветка пунктов выпадающих списков */
        QComboBox QListView::item:hover {
            background-color: #52525B;
            color: #FFD700;
        }
        
        QTableWidget {
            background-color: #18181B;
            gridline-color: #3F3F46;
            border: none;
        }
        
        QTableWidget::item {
            padding: 8px;
            border: none;
        }
        
        QTableWidget::item:selected {
            background-color: #3B82F6;
        }
        
        QHeaderView::section {
            background-color: #27272A;
            color: #A1A1AA;
            padding: 8px;
            border: none;
            border-bottom: 2px solid #3F3F46;
            font-weight: 600;
        }
        
        QScrollBar:vertical {
            background-color: #18181B;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #3F3F46;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #52525B;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QTabWidget::pane {
            border: none;
            background-color: #18181B;
        }
        
        QTabBar::tab {
            background-color: #27272A;
            color: #A1A1AA;
            padding: 10px 20px;
            margin-right: 4px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }
        
        QTabBar::tab:selected {
            background-color: #18181B;
            color: #FAFAFA;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #3F3F46;
        }
        
        QProgressDialog {
            background-color: #27272A;
            border-radius: 12px;
        }
        
        QProgressBar {
            background-color: #3F3F46;
            border-radius: 6px;
            text-align: center;
            color: #FAFAFA;
        }
        
        QProgressBar::chunk {
            background-color: #3B82F6;
            border-radius: 6px;
        }
        
        QLabel {
            background-color: transparent;
        }
        
        QScrollArea {
            background-color: transparent;
            border: none;
        }
        
        QScrollBar:horizontal {
            background-color: #18181B;
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #3F3F46;
            border-radius: 6px;
            min-width: 20px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #52525B;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
    """)


def format_money(value: Optional[float], decimals: int = 2, currency: str = "$", with_plus: bool = False) -> str:
    """
    Форматирует денежное значение.
    
    Args:
        value: Числовое значение (может быть None)
        decimals: Количество знаков после запятой
        currency: Символ валюты
        with_plus: Добавлять ли знак + для положительных значений
    
    Returns:
        Отформатированная строка
    """
    # Обрабатываем None значения как 0
    if value is None:
        value = 0.0
    
    if value >= 0:
        sign = "+" if with_plus else ""
    else:
        sign = "-"
        value = abs(value)
    
    if decimals == 0:
        return f"{sign}{currency}{value:,.0f}"
    else:
        return f"{sign}{currency}{value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 1, with_plus: bool = False) -> str:
    """
    Форматирует процентное значение.
    
    Args:
        value: Числовое значение процента
        decimals: Количество знаков после запятой
        with_plus: Добавлять ли знак + для положительных значений
    
    Returns:
        Отформатированная строка
    """
    if value >= 0 and with_plus:
        return f"+{value:.{decimals}f}%"
    else:
        return f"{value:.{decimals}f}%"


def apply_cell_color_by_value(widget_or_item, value: Optional[float]):
    """
    Применяет цвет к виджету или элементу таблицы в зависимости от значения (красный/зеленый).
    
    Args:
        widget_or_item: QWidget или QTableWidgetItem для изменения цвета
        value: Значение для определения цвета (может быть None)
    """
    # Обрабатываем None значения
    if value is None:
        color = "#71717A"  # Темно-серый для None
    elif value > 0:
        color = "#10B981"  # Зеленый для положительных
    elif value < 0:
        color = "#EF4444"  # Красный для отрицательных
    else:
        color = "#A1A1AA"  # Серый для нулевых
    
    # Проверяем тип объекта
    if isinstance(widget_or_item, QtWidgets.QTableWidgetItem):
        # Для QTableWidgetItem используем setForeground
        widget_or_item.setForeground(QtGui.QBrush(QtGui.QColor(color)))
    elif isinstance(widget_or_item, QtWidgets.QLabel):
        # Для QLabel просто устанавливаем color через styleSheet
        widget_or_item.setStyleSheet(f"color: {color}; font-weight: bold;")
    elif hasattr(widget_or_item, 'setStyleSheet'):
        # Для других виджетов используем styleSheet
        widget_or_item.setStyleSheet(f"color: {color};")


def apply_bigko_x10_color(label: QtWidgets.QLabel, total_tournaments: int, x10_count: int):
    """Applies color to the x10 Big KO label based on average frequency."""
    if not isinstance(label, QtWidgets.QLabel):
        return

    # Default color is gray if we cannot compute frequency
    color = "#A1A1AA"

    if x10_count <= 0 or total_tournaments <= 0:
        color = "#EF4444"  # Red when there were no x10 knockouts
    else:
        avg_interval = total_tournaments / x10_count

        if avg_interval <= 51:
            # Bright green color and add fire emoji when very frequent
            color = "#00FF00"
            label.setText(f"{label.text()} \U0001F525")
        elif 52 <= avg_interval <= 58:
            color = "#10B981"  # Green
        elif 59 <= avg_interval <= 65:
            color = "#F59E0B"  # Orange
        elif avg_interval > 65:
            color = "#EF4444"  # Red

    label.setStyleSheet(f"color: {color}; font-weight: bold;")


def apply_bigko_high_tier_color(label: QtWidgets.QLabel, count: int):
    """Applies bright green color and fire emoji for high tier Big KO counts."""
    if not isinstance(label, QtWidgets.QLabel):
        return

    if count > 0:
        color = "#00FF00"  # Bright green
        label.setText(f"{label.text()} \U0001F525")
    elif count == 0:
        # Default white color for zero counts on x100+ cards
        color = "#FAFAFA"
    else:
        # Safeguard: red color if somehow count turns negative
        color = "#EF4444"

    label.setStyleSheet(f"color: {color}; font-weight: bold;")


def create_separator() -> QtWidgets.QFrame:
    """Создает горизонтальный разделитель."""
    separator = QtWidgets.QFrame()
    separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    separator.setStyleSheet("QFrame { background-color: #3F3F46; max-height: 1px; margin: 16px 0; }")
    return separator


def setup_table_widget(table: QtWidgets.QTableWidget):
    """
    Настраивает внешний вид таблицы в соответствии с темной темой.
    
    Args:
        table: Виджет таблицы для настройки
    """
    # Растягиваем последнюю колонку
    table.horizontalHeader().setStretchLastSection(True)
    
    # Скрываем вертикальные линии сетки
    table.setShowGrid(False)
    
    # Чередующиеся цвета строк
    table.setAlternatingRowColors(True)
    
    # Выделение целой строки
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    
    # Запрет редактирования
    table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    
    # Сортировка по клику на заголовок
    table.setSortingEnabled(True)
    
    # Дополнительные стили
    table.setStyleSheet("""
        QTableWidget {
            background-color: #18181B;
            alternate-background-color: #1F1F23;
            border: none;
            gridline-color: #3F3F46;
        }
        
        QTableWidget::item {
            padding: 8px;
            border: none;
        }
        
        QTableWidget::item:selected {
            background-color: #3B82F6;
            color: white;
        }
        
        QHeaderView::section {
            background-color: #27272A;
            color: #A1A1AA;
            padding: 10px;
            border: none;
            border-bottom: 2px solid #3F3F46;
            font-weight: 600;
            text-align: left;
        }
        
        QHeaderView::section:hover {
            background-color: #3F3F46;
            color: #FAFAFA;
        }
        
        QTableWidget::item:hover {
            background-color: #27272A;
        }
        
        QTableCornerButton::section {
            background-color: #27272A;
            border: none;
        }
    """)