# -*- coding: utf-8 -*-
"""Тесты для проверки подсчета попыток КО."""

import unittest
import tempfile
import os
import config

# Временно устанавливаем имя Hero для тестов
config.HERO_NAME = "TestHero"

from parsers.hand_history import HandHistoryParser, HandData

class TestKOAttempts(unittest.TestCase):
    def setUp(self):
        self.parser = HandHistoryParser("TestHero")
    
    def test_hero_bets_all_in_attempt(self):
        """Тест: Hero ставит >= стека оппонента = попытка."""
        hand_content = """
Poker Hand #HH20231201-001: Tournament #12345678, $10.00+$0.00 USD Hold'em No Limit - Level10(250/500) - 2023/12/01 10:00:00 ET
Table '12345678 1' 9-max Seat #1 is the button
Seat 1: Player1 (5000 in chips)
Seat 2: TestHero (15000 in chips)
Seat 3: Player3 (3000 in chips)
Player1: posts small blind 250
TestHero: posts big blind 500
*** HOLE CARDS ***
Player3: raises 2500 to 3000 and is all-in
Player1: folds
TestHero: calls 2500
*** FLOP *** [Kc 7h 2d]
*** TURN *** [Kc 7h 2d] [9s]
*** RIVER *** [Kc 7h 2d 9s] [Ah]
*** SHOWDOWN ***
Player3: shows [Qd Jd] (high card Ace)
TestHero: shows [Ac Kh] (two pair, Aces and Kings)
TestHero collected 6250 from pot
Player3 finished the tournament in 9th place
*** SUMMARY ***
Total pot 6250 | Rake 0
Board [Kc 7h 2d 9s Ah]
Seat 1: Player1 (button) folded before Flop (didn't bet)
Seat 2: TestHero (big blind) showed [Ac Kh] and won (6250) with two pair, Aces and Kings
Seat 3: Player3 showed [Qd Jd] and lost with high card Ace
"""
        result = self.parser.parse(hand_content, "test.txt")
        hands_data = result.get('final_table_hands_data', [])
        
        self.assertEqual(len(hands_data), 1)
        hand = hands_data[0]
        
        # Hero покрывал стек Player3 и коллировал его олл-ин = попытка
        self.assertEqual(hand['hero_ko_attempts'], 1)
        self.assertEqual(hand['hero_ko_this_hand'], 1)  # И успешно выбил
    
    def test_hero_folds_to_all_in_no_attempt(self):
        """Тест: Оппонент all-in + Hero фолдит = НЕ попытка."""
        hand_content = """
Poker Hand #HH20231201-002: Tournament #12345678, $10.00+$0.00 USD Hold'em No Limit - Level10(250/500) - 2023/12/01 10:05:00 ET
Table '12345678 1' 9-max Seat #1 is the button
Seat 1: Player1 (5000 in chips)
Seat 2: TestHero (15000 in chips)
Seat 3: Player3 (3000 in chips)
Player1: posts small blind 250
TestHero: posts big blind 500
*** HOLE CARDS ***
Player3: raises 2500 to 3000 and is all-in
Player1: folds
TestHero: folds
Uncalled bet (2500) returned to Player3
Player3 collected 1250 from pot
*** SUMMARY ***
Total pot 1250 | Rake 0
Seat 1: Player1 (button) folded before Flop (didn't bet)
Seat 2: TestHero (big blind) folded before Flop
Seat 3: Player3 collected (1250)
"""
        result = self.parser.parse(hand_content, "test.txt")
        hands_data = result.get('final_table_hands_data', [])
        
        self.assertEqual(len(hands_data), 1)
        hand = hands_data[0]
        
        # Hero сфолдил на олл-ин = НЕ попытка
        self.assertEqual(hand['hero_ko_attempts'], 0)
        self.assertEqual(hand['hero_ko_this_hand'], 0)
    
    def test_hero_initiates_with_big_bet(self):
        """Тест: Hero инициирует с бетом >= стека оппонента = попытка."""
        hand_content = """
Poker Hand #HH20231201-003: Tournament #12345678, $10.00+$0.00 USD Hold'em No Limit - Level10(250/500) - 2023/12/01 10:10:00 ET
Table '12345678 1' 9-max Seat #1 is the button
Seat 1: Player1 (5000 in chips)
Seat 2: TestHero (15000 in chips)
Seat 3: Player3 (2000 in chips)
Player1: posts small blind 250
TestHero: posts big blind 500
*** HOLE CARDS ***
Player3: folds
Player1: calls 250
TestHero: raises 2000 to 2500
Player1: folds
Uncalled bet (2000) returned to TestHero
TestHero collected 1000 from pot
*** SUMMARY ***
Total pot 1000 | Rake 0
Seat 1: Player1 (button) folded before Flop
Seat 2: TestHero (big blind) collected (1000)
Seat 3: Player3 folded before Flop (didn't bet)
"""
        result = self.parser.parse(hand_content, "test.txt")
        hands_data = result.get('final_table_hands_data', [])
        
        self.assertEqual(len(hands_data), 1)
        hand = hands_data[0]
        
        # Hero поставил 2500, что >= стека Player3 (2000) = попытка на Player3
        # Но Player3 уже сфолдил, так что попытка не засчитывается
        self.assertEqual(hand['hero_ko_attempts'], 0)
    
    def test_hero_doesnt_cover_no_attempt(self):
        """Тест: Hero не покрывает стек оппонента = НЕ попытка."""
        hand_content = """
Poker Hand #HH20231201-004: Tournament #12345678, $10.00+$0.00 USD Hold'em No Limit - Level10(250/500) - 2023/12/01 10:15:00 ET
Table '12345678 1' 9-max Seat #1 is the button
Seat 1: Player1 (20000 in chips)
Seat 2: TestHero (5000 in chips)
Seat 3: Player3 (10000 in chips)
Player1: posts small blind 250
TestHero: posts big blind 500
*** HOLE CARDS ***
Player3: raises 9500 to 10000 and is all-in
Player1: folds
TestHero: calls 4500 and is all-in
Uncalled bet (5000) returned to Player3
*** FLOP *** [Kc 7h 2d]
*** TURN *** [Kc 7h 2d] [9s]
*** RIVER *** [Kc 7h 2d 9s] [Ah]
*** SHOWDOWN ***
TestHero: shows [Ac Kh] (two pair, Aces and Kings)
Player3: shows [Qd Jd] (high card Ace)
TestHero collected 10250 from pot
*** SUMMARY ***
Total pot 10250 | Rake 0
Board [Kc 7h 2d 9s Ah]
Seat 1: Player1 (button) folded before Flop (didn't bet)
Seat 2: TestHero (big blind) showed [Ac Kh] and won (10250) with two pair, Aces and Kings
Seat 3: Player3 showed [Qd Jd] and lost with high card Ace
"""
        result = self.parser.parse(hand_content, "test.txt")
        hands_data = result.get('final_table_hands_data', [])
        
        self.assertEqual(len(hands_data), 1)
        hand = hands_data[0]
        
        # Hero не покрывал стек Player3 (5000 < 10000) = НЕ попытка
        self.assertEqual(hand['hero_ko_attempts'], 0)
        self.assertEqual(hand['hero_ko_this_hand'], 0)

if __name__ == '__main__':
    unittest.main()