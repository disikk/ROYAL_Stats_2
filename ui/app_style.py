# -*- coding: utf-8 -*-

"""
Модуль для стилизации приложения с помощью QSS (CSS для Qt).
Содержит темную тему и вспомогательные функции для форматирования/стилизации виджетов.
"""
import logging
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import Qt, QLocale # Импортируем QLocale для форматирования денег
from typing import Optional

logger = logging.getLogger('ROYAL_Stats.AppStyle')

def apply_dark_theme(app: QtWidgets.QApplication):
    """Применяет темную тему ко всему приложению"""
    app.setStyle("Fusion")

    # Создаем темную палитру
    dark_palette = QtGui.QPalette()

    # Определяем цвета
    dark_color = QtGui.QColor(42, 42, 42)  # #2a2a2a
    darker_color = QtGui.QColor(26, 26, 26)  # #1a1a1a
    highlight_color = QtGui.QColor(34, 197, 94)  # #22c55e
    disabled_color = QtGui.QColor(127, 127, 127)
    text_color = QtGui.QColor(255, 255, 255)
    bright_text = QtGui.QColor(255, 255, 255)
    link_color = QtGui.QColor(99, 102, 241)
    accent_color = QtGui.QColor(236, 72, 153)  # Розовый акцент для важных элементов

    # Устанавливаем цвета в палитру
    dark_palette.setColor(QtGui.QPalette.ColorRole.Window, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.WindowText, text_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Base, darker_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, dark_color.lighter(105)) # Слегка светлее для чередования строк
    dark_palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, darker_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, text_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Text, text_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Button, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ButtonText, text_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.BrightText, bright_text)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Link, link_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Highlight, highlight_color) # Цвет выделения
    dark_palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, text_color) # Цвет текста в выделенном элементе
    dark_palette.setColor(QtGui.QPalette.ColorRole.PlaceholderText, disabled_color) # Цвет текста-подсказки

    # Для неактивных элементов
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, disabled_color)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, disabled_color)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText, disabled_color)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.HighlightedText, disabled_color)


    # Применяем палитру
    app.setPalette(dark_palette)

    # Дополнительный QSS для улучшения стиля
    # Используем более мягкие границы и фон
    app.setStyleSheet("""
    * {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    QMainWindow {
        background-color: #1a1a1a;
    }
    QTabWidget::pane {
        border: 1px solid #374151;
        border-radius: 4px;
        padding: 4px;
        background-color: #2a2a2a;
    }
    QTabBar::tab {
        background: #2a2a2a;
        color: #9ca3af;
        border: 1px solid #374151;
        border-bottom: none;
        padding: 4px 8px;
        margin-right: 3px;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        font-size: 12px;
    }
    QTabBar::tab:selected {
        background: #2a2a2a;
        color: #ffffff;
        border: 1px solid #374151;
        border-bottom-color: #2a2a2a;
    }
    QTabBar::tab:hover {
        background: #374151;
    }
    QPushButton {
        background-color: #22c55e;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #16a34a;
    }
    QGroupBox {
        border: 1px solid #374151;
        border-radius: 6px;
        margin-top: 20px;
        background-color: #2a2a2a;
        padding: 8px;
        padding-top: 16px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 8px;
        background-color: #2a2a2a;
        color: #9ca3af;
        font-weight: 600;
        font-size: 12px;
        border-radius: 4px;
    }
    """)


def format_money(value: Optional[float], with_plus: bool = False) -> str:
    """
    Форматирует денежное значение с символом валюты и локалью.
    Всегда использует US English локаль для форматирования в формате "$X.XX".
    """
    if value is None:
        return "$-.--"

    try:
        # Используем US English локаль для постоянного форматирования в формате $X.XX
        locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        # Отключаем стандартный символ валюты локали, чтобы добавить $ вручную
        locale.setNumberOptions(QLocale.NumberOption.OmitGroupSeparator | QLocale.NumberOption.OmitLeadingZeroInExponent)
        formatted_value = locale.toString(value, 'f', 2)  # 2 знака после запятой

        prefix = "+" if with_plus and value > 0 else ""
        # Возвращаем отформатированное значение с символом валюты в начале
        return f"{prefix}${formatted_value}"
    except (ValueError, TypeError):
        return str(value)  # Возвращаем исходное значение как строку, если форматирование не удалось

def format_percentage(value: Optional[float], decimals: int = 2) -> str:
    """
    Форматирует значение как процент.
    Всегда использует US English локаль для постоянного форматирования.
    """
    if value is None:
        return "-.-- %"
    try:
        locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        # Отключаем разделители групп для обеспечения единообразного форматирования
        locale.setNumberOptions(QLocale.NumberOption.OmitGroupSeparator | QLocale.NumberOption.OmitLeadingZeroInExponent)
        formatted_value = locale.toString(value, 'f', decimals)
        return f"{formatted_value} %"
    except (ValueError, TypeError):
         return str(value)


def apply_cell_color_by_value(item, value: Optional[float]):
    """
    Применяет цвет текста к виджету в зависимости от значения (для прибыли/убытка).
    Поддерживает как QTableWidgetItem, так и QLabel.
    """
    if value is None:
        color = QtGui.QColor(200, 200, 200)  # Серый для None
    else:
        try:
            val = float(value)
            if val > 0:
                color = QtGui.QColor(46, 204, 113)  # Зеленый
            elif val < 0:
                color = QtGui.QColor(231, 76, 60)  # Красный
            else:
                color = QtGui.QColor(255, 255, 255)  # Белый или нейтральный
        except (ValueError, TypeError):
            color = QtGui.QColor(200, 200, 200)  # Серый для нечисловых
            
    # Применяем цвет в зависимости от типа виджета
    if isinstance(item, QtWidgets.QTableWidgetItem):
        item.setForeground(QtGui.QBrush(color))
    elif isinstance(item, QtWidgets.QLabel):
        item.setStyleSheet(f"color: rgb({color.red()}, {color.green()}, {color.blue()});")
    else:
        logger.warning(f"Неподдерживаемый тип виджета для apply_cell_color_by_value: {type(item)}")

def setup_table_widget(table: QtWidgets.QTableWidget):
    """
    Настраивает таблицу с улучшенным внешним видом и поведением.
    """
    # Настройка растяжения содержимого
    # table.horizontalHeader().setStretchLastSection(True) # Последняя секция растягивается
    table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive) # Пользователь может менять размер
    table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents) # ID по содержимому
    table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch) # Название турнира - растягивается
    # Остальные колонки - ResizeToContents или Interactive по необходимости

    # Альтернативная окраска строк
    table.setAlternatingRowColors(True)

    # Подсказки на всю ячейку (можно убрать, если не нужно)
    # table.setMouseTracking(True)
    # table.setToolTipDuration(5000)

    # Полноразмерная прокрутка
    # scrollbar = table.verticalScrollBar()
    # scrollbar.setSingleStep(1) # Оставляем дефолтный шаг или настраиваем

    # Убираем фокусную рамку (может влиять на доступность)
    # table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    table.setWordWrap(False) # Отключаем перенос слов в ячейках

    # Выравнивание текста в ячейках (по умолчанию слева)
    # Можно настроить для конкретных колонок при заполнении данными


    return table