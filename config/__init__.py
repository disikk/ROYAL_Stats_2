#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROYAL_Stats - Конфигурация приложения.
Данный модуль служит для импорта настроек.
"""

from config.settings import (
    APP_NAME, 
    APP_VERSION, 
    DB_FOLDER, 
    LOGS_FOLDER, 
    DEFAULT_HERO_NAME,
    DEFAULT_LANGUAGE
)

__all__ = [
    'APP_NAME', 
    'APP_VERSION', 
    'DB_FOLDER', 
    'LOGS_FOLDER', 
    'DEFAULT_HERO_NAME',
    'DEFAULT_LANGUAGE'
]