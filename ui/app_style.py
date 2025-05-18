"""
Модуль для стилизации приложения с помощью QSS (CSS для Qt).
"""
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import Qt

def apply_dark_theme(app):
    """Применяет темную тему ко всему приложению"""
    app.setStyle("Fusion")
    
    # Создаем темную палитру
    dark_palette = QtGui.QPalette()
    
    # Определяем цвета
    dark_color = QtGui.QColor(53, 53, 53)
    darker_color = QtGui.QColor(35, 35, 35)
    highlight_color = QtGui.QColor(42, 130, 218)
    disabled_color = QtGui.QColor(127, 127, 127)
    text_color = QtGui.QColor(255, 255, 255)
    bright_text = QtGui.QColor(255, 255, 255)
    
    # Устанавливаем цвета в палитру
    dark_palette.setColor(QtGui.QPalette.ColorRole.Window, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.WindowText, text_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Base, darker_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, highlight_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, text_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Text, text_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Button, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ButtonText, text_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.BrightText, bright_text)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Link, highlight_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Highlight, highlight_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, text_color)
    
    # Для неактивных элементов
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, disabled_color)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, disabled_color)
    
    # Применяем палитру
    app.setPalette(dark_palette)
    
    # Дополнительный QSS для улучшения стиля
    app.setStyleSheet("""
        QToolTip { 
            color: #ffffff; 
            background-color: #2a82da;
            border: 1px solid white;
            padding: 2px;
            border-radius: 3px;
        }
        
        QTabWidget::pane {
            border: 1px solid #444;
            border-radius: 3px;
            padding: 5px;
        }
        
        QTabBar::tab {
            background: #3a3a3a;
            color: #b1b1b1;
            border: 1px solid #444;
            padding: 5px 10px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background: #4a4a4a;
            color: white;
            border-bottom-color: #4a4a4a;
        }
        
        QTableView {
            gridline-color: #444444;
            selection-background-color: #2a82da;
            selection-color: white;
            alternate-background-color: #404040;
        }
        
        QTableView::item:hover {
            background-color: #333333;
        }
        
        QHeaderView::section {
            background-color: #3a3a3a;
            padding: 4px;
            border: 1px solid #444;
            color: white;
            font-weight: bold;
        }
        
        QGroupBox {
            border: 1px solid #444;
            border-radius: 5px;
            margin-top: 20px;
            background-color: #3a3a3a;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 10px 0 10px;
            background-color: #2a2a2a;
            color: white;
            font-weight: bold;
        }
    """)


def format_money(value, with_plus=False):
    """Форматирует денежное значение с символом валюты"""
    try:
        val = float(value)
        prefix = "+" if with_plus and val > 0 else ""
        return f"{prefix}{val:.2f} ₽"
    except (ValueError, TypeError):
        return str(value)


def apply_cell_color_by_value(table_item, value):
    """Применяет цвет к ячейке в зависимости от значения (для прибыли/убытка)"""
    try:
        val = float(value)
        if val > 0:
            table_item.setForeground(QtGui.QBrush(QtGui.QColor(46, 204, 113)))  # Зеленый
        elif val < 0:
            table_item.setForeground(QtGui.QBrush(QtGui.QColor(231, 76, 60)))  # Красный
    except (ValueError, TypeError):
        pass  # Не применяем окраску, если не число


def setup_table_widget(table):
    """Настраивает таблицу с улучшенным внешним видом"""
    # Настройка растяжения содержимого
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    
    # Альтернативная окраска строк
    table.setAlternatingRowColors(True)
    
    # Подсказки на всю ячейку
    table.setMouseTracking(True)
    table.setToolTipDuration(5000)
    
    # Полноразмерная прокрутка
    scrollbar = table.verticalScrollBar()
    scrollbar.setSingleStep(1)
    
    # Убираем фокусную рамку
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    return table