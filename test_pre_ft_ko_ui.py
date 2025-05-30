#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from application_service import ApplicationService
import time

def test_pre_ft_ko_stat():
    app = QApplication(sys.argv)
    app_service = ApplicationService()
    
    # Load data
    overall_stats = app_service.get_overall_stats()
    
    print(f"Overall Stats loaded:")
    print(f"  - Total tournaments: {overall_stats.total_tournaments}")
    print(f"  - Total knockouts: {overall_stats.total_knockouts}")
    print(f"  - Pre-FT KO count: {overall_stats.pre_ft_ko_count}")
    
    # Test PreFTKOStat
    from stats import PreFTKOStat
    stat_result = PreFTKOStat().compute([], [], [], overall_stats)
    print(f"\nPreFTKOStat result: {stat_result}")
    
    # Create main window
    window = MainWindow(app_service)
    window.show()
    
    # Give it time to load and render
    app.processEvents()
    time.sleep(1)
    app.processEvents()
    
    # Check if pre_ft_ko card exists
    if hasattr(window, 'stats_grid') and hasattr(window.stats_grid, 'cards'):
        if 'pre_ft_ko' in window.stats_grid.cards:
            card = window.stats_grid.cards['pre_ft_ko']
            print(f"\nPre-FT KO card found!")
            print(f"  - Title: {card.title_label.text()}")
            print(f"  - Value: {card.value_label.text()}")
        else:
            print("\nERROR: Pre-FT KO card not found in stats grid!")
            print(f"Available cards: {list(window.stats_grid.cards.keys())}")
    
    # Keep window open for 3 seconds
    for _ in range(30):
        app.processEvents()
        time.sleep(0.1)
    
    window.close()

if __name__ == "__main__":
    test_pre_ft_ko_stat()