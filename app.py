# -*- coding: utf-8 -*-

"""
Точка входа в приложение Royal Stats (Hero-only).
"""

import os
import sys
from PyQt6 import QtWidgets
from ui.main_window import MainWindow # Импортируем главное окно
from ui.app_style import apply_dark_theme # Импортируем функцию стилизации
import config # Для доступа к настройкам

import logging
# Настройка базового логгирования
# Уровень логирования можно настроить в config.py
logging.basicConfig(level=logging.DEBUG if config.DEBUG else logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ROYAL_Stats.App')

def main():
    """
    Главная функция запуска приложения.
    """
    logger.info(f"Запуск приложения {config.APP_TITLE} v{config.APP_VERSION}")
    logger.info(f"Текущая рабочая директория: {os.getcwd()}")

    app = QtWidgets.QApplication(sys.argv)

    # Применяем тему
    apply_dark_theme(app)

    # Создаем и показываем главное окно
    main_window = MainWindow()
    main_window.show()

    # Сохраняем конфиг при выходе из приложения
    exit_code = app.exec()
    logger.info("Приложение завершило работу.")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()