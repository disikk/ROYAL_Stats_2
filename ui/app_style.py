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
    dark_color = QtGui.QColor(53, 53, 53)
    darker_color = QtGui.QColor(35, 35, 35)
    # highlight_color = QtGui.QColor(42, 130, 218) # Синий из примера
    highlight_color = QtGui.QColor(52, 152, 219) # Более "приятный" синий
    disabled_color = QtGui.QColor(127, 127, 127)
    text_color = QtGui.QColor(255, 255, 255)
    bright_text = QtGui.QColor(255, 255, 255)
    link_color = QtGui.QColor(52, 152, 219) # Цвет ссылок

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
        QToolTip {
            color: #ffffff;
            background-color: #2c3e50; /* Темно-синий фон для тултипов */
            border: 1px solid #3498db;
            padding: 3px;
            border-radius: 4px;
            opacity: 200; /* Небольшая прозрачность */
        }

        QMainWindow {
             background-color: #353535;
        }

        QTabWidget::pane {
            border: 1px solid #444;
            border-radius: 4px;
            padding: 6px;
            background-color: #3a3a3a; /* Фон содержимого вкладки */
        }

        QTabBar::tab {
            background: #2c2c2c; /* Фон неактивной вкладки */
            color: #b1b1b1;
            border: 1px solid #444;
            border-bottom: none; /* Нижняя граница неактивной вкладки */
            padding: 6px 12px;
            margin-right: 3px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }

        QTabBar::tab:selected {
            background: #3a3a3a; /* Фон активной вкладки */
            color: white;
            border: 1px solid #444;
            border-bottom-color: #3a3a3a; /* Цвет нижней границы активной вкладки совпадает с фоном pane */
        }

        QTabBar::tab:hover {
             background: #404040; /* Цвет при наведении */
        }

        QTableView {
            gridline-color: #555555; /* Цвет сетки */
            selection-background-color: #3498db; /* Цвет фона выделенной строки */
            selection-color: white; /* Цвет текста выделенной строки */
            alternate-background-color: #404040; /* Чередующийся фон строк */
            background-color: #3a3a3a; /* Фон таблицы */
            border: 1px solid #444;
            border-radius: 4px;
        }

        QTableView::item {
             padding: 4px; /* Внутренние отступы ячеек */
        }

        QTableView::item:selected {
            color: white;
        }

        QTableView::item:hover {
            background-color: #4a4a4a; /* Цвет фона ячейки при наведении */
        }

        QHeaderView::section {
            background-color: #2c3e50; /* Темно-синий фон заголовков */
            padding: 5px;
            border: 1px solid #444;
            border-bottom: 1px solid #555; /* Нижняя граница заголовков */
            color: white;
            font-weight: bold;
        }

        QHeaderView::section::horizontal {
            border-right: 1px solid #444; /* Вертикальные разделители в заголовке */
        }

        QHeaderView::section::vertical {
            border-bottom: 1px solid #444;
        }

        QGroupBox {
            border: 1px solid #444;
            border-radius: 6px; /* Слегка увеличенный радиус */
            margin-top: 25px; /* Отступ сверху для заголовка */
            background-color: #3a3a3a;
            padding: 10px; /* Внутренние отступы */
            padding-top: 20px; /* Отступ сверху для содержимого под заголовком */
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 10px;
            background-color: #2c2c2c; /* Фон заголовка GroupBox */
            color: white;
            font-weight: bold;
            border-radius: 4px; /* Скругление фона заголовка */
        }

        QPushButton {
            background-color: #3498db; /* Синяя кнопка */
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #2980b9; /* Цвет при наведении */
        }

        QPushButton:pressed {
            background-color: #2471a3; /* Цвет при нажатии */
        }

        QPushButton:disabled {
            background-color: #7f8c8d; /* Серый цвет для неактивных кнопок */
        }

        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit {
            background-color: #4a4a4a;
            color: white;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 5px;
        }

        QComboBox::drop-down {
            border-left: 1px solid #555;
        }

        QComboBox::down-arrow {
            image: url(./icons/down_arrow_white.png); /* Если есть иконка стрелки */
        }

        QScrollArea {
            border: none; /* Убираем рамку вокруг ScrollArea */
        }

        QScrollBar:vertical {
            border: 1px solid #444;
            background: #3a3a3a;
            width: 12px;
            margin: 12px 0 12px 0;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical {
            background: #555;
            min-height: 20px;
            border-radius: 5px;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }

        QScrollBar:horizontal {
            border: 1px solid #444;
            background: #3a3a3a;
            height: 12px;
            margin: 0 12px 0 12px;
            border-radius: 6px;
        }

        QScrollBar::handle:horizontal {
            background: #555;
            min-width: 20px;
            border-radius: 5px;
        }
         QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
        }

        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
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