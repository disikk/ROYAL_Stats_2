#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки исправления определения типов файлов
в методе import_files класса ApplicationService.
"""

import os
import logging
import sys
from datetime import datetime
from application_service import ApplicationService

# Настраиваем логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('ROYAL_Stats.FileDetectionTest')

def test_file_detection():
    """
    Тестирует определение типа файла на основе содержимого в методе import_files.
    """
    # Создаем экземпляр ApplicationService
    app_service = ApplicationService()
    
    # Путь к тестовому файлу Tournament Summary
    test_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'hh_examples', 
        'GG20250515 - Tournament #206881959 - Mystery Battle Royale 10.txt'
    )
    
    if not os.path.exists(test_file_path):
        logger.error(f"Тестовый файл не найден: {test_file_path}")
        return False
    
    logger.info(f"Тестирование файла: {test_file_path}")
    
    # Создаем временную сессию для теста
    session_name = f"Test Session {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Вызываем метод import_files с нашим тестовым файлом
    try:
        app_service.import_files([test_file_path], session_name)
        
        # Получаем данные импортированного турнира по ID из имени файла
        tournament_id = "206881959"  # ID из имени файла
        
        tournament = app_service.tournament_repo.get_tournament_by_id(tournament_id)
        
        if tournament:
            logger.info(f"Турнир найден в БД, ID: {tournament.tournament_id}")
            logger.info(f"Название турнира: {tournament.tournament_name}")
            logger.info(f"Бай-ин: {tournament.buyin}")
            logger.info(f"Выплата: {tournament.payout}")
            logger.info(f"Место: {tournament.finish_place}")
            
            # Проверяем, что важные поля заполнены
            success = all([
                tournament.tournament_name is not None,
                tournament.buyin is not None and tournament.buyin > 0,
                tournament.payout is not None and tournament.payout > 0,
                tournament.finish_place is not None and tournament.finish_place > 0
            ])
            
            if success:
                logger.info("ТЕСТ ПРОЙДЕН: Все поля турнира корректно заполнены!")
            else:
                logger.error("ТЕСТ НЕ ПРОЙДЕН: Некоторые поля турнира не заполнены:")
                logger.error(f"tournament_name: {tournament.tournament_name}")
                logger.error(f"buyin: {tournament.buyin}")
                logger.error(f"payout: {tournament.payout}")
                logger.error(f"finish_place: {tournament.finish_place}")
            
            return success
        else:
            logger.error(f"Турнир с ID {tournament_id} не найден в БД после импорта")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при импорте файла: {e}")
        return False

if __name__ == "__main__":
    result = test_file_detection()
    if result:
        logger.info("Тест успешно пройден! Определение типа файла работает корректно.")
    else:
        logger.error("Тест не пройден. Проверьте логи выше для деталей.")