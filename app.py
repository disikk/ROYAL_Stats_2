#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROYAL_Stats 2.0 - Покерный трекер для анализа статистики игрока

Основной модуль запуска приложения.
Инициализирует компоненты системы и запускает графический интерфейс.

Функциональность:
1. Подсчет нокаутов (когда Hero выбил другого игрока)
2. Подсчет среднего места, с которого игрок вылетел (1-9)
3. Подсчет количества крупных нокаутов (x2, x10, x100, x1000, x10000)
4. Построение гистограммы распределения позиций
5. Модульная система для легкого добавления новых типов статистики
6. Управление несколькими базами данных

Автор: Royal Team
Версия: 2.0
Дата: 2025
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import QLocale

# Импорт из модулей приложения
from ui.main_window import MainWindow
from core.plugin_manager import PluginManager
from db.manager import DatabaseManager
from config.settings import AppSettings

# Инициализируем UI расширения
from ui_extender import UIExtender

# Настройка кодировки
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def setup_logging():
    """Настраивает систему логирования приложения"""
    # Создаем папку для логов, если она не существует
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/royal_stats.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Создаем логгер
    logger = logging.getLogger('ROYAL_Stats')
    logger.info('Запуск приложения ROYAL_Stats 2.0')
    
    return logger


def main():
    """
    Основная функция запуска приложения.
    Инициализирует компоненты системы и запускает графический интерфейс.
    """
    # Настраиваем логирование
    logger = setup_logging()
    
    try:
        # Создаем приложение Qt
        app = QApplication(sys.argv)
        app.setApplicationName("ROYAL_Stats")
        app.setApplicationVersion("2.0")
        
        # Настраиваем локализацию для поддержки кириллицы
        locale = QLocale(QLocale.Language.Russian)
        QLocale.setDefault(locale)
        
        # Настраиваем стиль приложения с указанием шрифта, поддерживающего кириллицу
        app.setStyle("Fusion")
        default_font = QFont("Arial", 9)  # Arial обычно хорошо поддерживает кириллицу
        app.setFont(default_font)
        
        # Загружаем настройки приложения
        settings = AppSettings()
        
        # Инициализируем менеджер базы данных
        db_manager = DatabaseManager(db_folder=settings.get('db_folder', 'databases'))
        
        # Инициализируем менеджер плагинов
        plugin_manager = PluginManager(db_manager)
        
        # Загружаем доступные модули статистики
        plugin_manager.discover_modules()
        
        # Инициализируем расширения UI-компонентов
        UIExtender.initialize()
        
        # Инициализируем модули
        plugin_manager.initialize_modules()
        
        # Создаем главное окно приложения
        window = MainWindow(db_manager, plugin_manager, settings)
        window.show()
        
        # Запускаем цикл обработки событий
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        raise


# Точка входа при запуске скрипта
if __name__ == "__main__":
    main()