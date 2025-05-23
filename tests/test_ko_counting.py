import unittest
from parsers.hand_history import HandHistoryParser
import config

class TestKOCounting(unittest.TestCase):
    def setUp(self):
        self.parser = HandHistoryParser("Hero")
        # Save original hero name and set it for tests
        self.original_hero = config.HERO_NAME
        config.HERO_NAME = "Hero"
    
    def tearDown(self):
        # Restore original hero name
        config.HERO_NAME = self.original_hero
    
    def test_ko_with_ante_sb_raise_allin(self):
        """Test knockout detection when player posts ante, SB, raises and goes all-in"""
        # Hand history showing:
        # - Player starts with 5401 chips
        # - Posts ante 80
        # - Posts SB 200
        # - Makes raise to 5321 (raises 4921 more than BB)
        # - Goes all-in with total contribution = 80 + 200 + 5121 = 5401
        hand_text = """Poker Hand #GG1234567890: Tournament #206881959, 10 Hold'em No Limit - Level10(200/400) - 2025/01/01 16:38:15
Table '206881959' 9-max Seat #1 is the button
Seat 1: Hero (15000 in chips)
Seat 2: Victim (5401 in chips)
Seat 3: Player3 (10000 in chips)
Hero: posts ante 80
Victim: posts ante 80
Player3: posts ante 80
Victim: posts small blind 200
Player3: posts big blind 400
*** HOLE CARDS ***
Dealt to Hero [Kc Kd]
Hero: raises 800 to 1200
Victim: raises 4,921 to 5,321 and is all-in
Player3: folds
Hero: calls 4121
*** FLOP *** [2h 7d 9s]
*** TURN *** [2h 7d 9s] [3h]
*** RIVER *** [2h 7d 9s 3h] [Jd]
*** SHOWDOWN ***
Victim: shows [Ac Qc]
Hero: shows [Kc Kd]
Hero collected 11522 from pot
*** SUMMARY ***
Total pot 11522
"""
        
        result = self.parser.parse(hand_text)
        
        # Verify the hand was parsed correctly
        self.assertIsNotNone(result)
        self.assertEqual(result['tournament_id'], '206881959')
        self.assertTrue(result['reached_final_table'])
        
        # Verify KO was counted
        self.assertEqual(len(result['final_table_hands_data']), 1)
        hand_data = result['final_table_hands_data'][0]
        
        # Print debug information
        print(f"\nTest: {self._testMethodName}")
        print(f"Victim stack: 5401")
        print(f"Victim contribution: ante 80 + SB 200 + raise 5121 = 5401")
        print(f"Hero won pot: Yes")
        print(f"Hero KO count: {hand_data['hero_ko_this_hand']}")
        
        self.assertEqual(hand_data['hero_ko_this_hand'], 1, 
                         "Hero should have 1 KO when covering Victim's all-in")
    
    def test_ko_with_call_allin(self):
        """Test knockout when villain calls all-in"""
        hand_text = """Poker Hand #GG1234567891: Tournament #206881959, 10 Hold'em No Limit - Level10(200/400) - 2025/01/01 16:40:00
Table '206881959' 9-max Seat #1 is the button
Seat 1: Hero (20000 in chips)
Seat 2: Villain1 (3000 in chips)
Hero: posts ante 80
Villain1: posts ante 80
Hero: posts big blind 400
Villain1: posts small blind 200
*** HOLE CARDS ***
Dealt to Hero [As Ad]
Villain1: raises 2,720 to 2,920 and is all-in
Hero: calls 2520
*** FLOP *** [2c 5d 8s]
*** TURN *** [2c 5d 8s] [9c]
*** RIVER *** [2c 5d 8s 9c] [3h]
*** SHOWDOWN ***
Villain1: shows [Kh Qh]
Hero: shows [As Ad]
Hero collected 6000 from pot
*** SUMMARY ***
Total pot 6000
"""
        
        result = self.parser.parse(hand_text)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['final_table_hands_data']), 1)
        hand_data = result['final_table_hands_data'][0]
        
        print(f"\nTest: {self._testMethodName}")
        print(f"Villain1 stack: 3000")
        print(f"Villain1 all-in: Yes")
        print(f"Hero covered: Yes (20000 > 3000)")
        print(f"Hero won pot: Yes")
        print(f"Hero KO count: {hand_data['hero_ko_this_hand']}")
        
        self.assertEqual(hand_data['hero_ko_this_hand'], 1)
    
    def test_ko_multiway_pot(self):
        """Test knockout in multiway pot with side pot"""
        hand_text = """Poker Hand #GG1234567892: Tournament #206881959, 10 Hold'em No Limit - Level10(200/400) - 2025/01/01 16:42:00
Table '206881959' 9-max Seat #1 is the button
Seat 1: Hero (25000 in chips)
Seat 2: ShortStack (1500 in chips)
Seat 3: BigStack (30000 in chips)
Hero: posts ante 80
ShortStack: posts ante 80
BigStack: posts ante 80
ShortStack: posts small blind 200
BigStack: posts big blind 400
*** HOLE CARDS ***
Dealt to Hero [Qc Qd]
Hero: raises 800 to 1200
ShortStack: raises 220 to 1,420 and is all-in
BigStack: calls 1020
Hero: calls 220
*** FLOP *** [7h 2d 9s]
BigStack: checks
Hero: bets 2000
BigStack: folds
Uncalled bet (2000) returned to Hero
*** TURN *** [7h 2d 9s] [4c]
*** RIVER *** [7h 2d 9s 4c] [6h]
*** SHOWDOWN ***
ShortStack: shows [Jc Td]
Hero: shows [Qc Qd]
Hero collected 4500 from pot
*** SUMMARY ***
Total pot 4500
"""
        
        result = self.parser.parse(hand_text)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['final_table_hands_data']), 1)
        hand_data = result['final_table_hands_data'][0]
        
        print(f"\nTest: {self._testMethodName}")
        print(f"ShortStack stack: 1500")
        print(f"ShortStack all-in: Yes")
        print(f"Hero covered: Yes (25000 > 1500)")
        print(f"Hero won main pot: Yes")
        print(f"Hero KO count: {hand_data['hero_ko_this_hand']}")
        
        self.assertEqual(hand_data['hero_ko_this_hand'], 1)
    
    def test_no_ko_when_hero_loses(self):
        """Test that no knockout is counted when Hero loses the hand"""
        hand_text = """Poker Hand #GG1234567893: Tournament #206881959, 10 Hold'em No Limit - Level10(200/400) - 2025/01/01 16:45:00
Table '206881959' 9-max Seat #1 is the button
Seat 1: Hero (5000 in chips)
Seat 2: Villain (15000 in chips)
Hero: posts ante 80
Villain: posts ante 80
Hero: posts small blind 200
Villain: posts big blind 400
*** HOLE CARDS ***
Dealt to Hero [Ac Kc]
Hero: raises 4,320 to 4,920 and is all-in
Villain: calls 4520
*** FLOP *** [2h 5d 8s]
*** TURN *** [2h 5d 8s] [9c]
*** RIVER *** [2h 5d 8s 9c] [3h]
*** SHOWDOWN ***
Hero: shows [Ac Kc]
Villain: shows [Ad Ah]
Villain collected 10000 from pot
*** SUMMARY ***
Total pot 10000
"""
        
        result = self.parser.parse(hand_text)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['final_table_hands_data']), 1)
        hand_data = result['final_table_hands_data'][0]
        
        print(f"\nTest: {self._testMethodName}")
        print(f"Hero all-in: Yes")
        print(f"Hero won pot: No")
        print(f"Hero KO count: {hand_data['hero_ko_this_hand']}")
        
        self.assertEqual(hand_data['hero_ko_this_hand'], 0)
    
    def test_no_ko_when_not_covering(self):
        """Test that no knockout when Hero doesn't cover villain's stack"""
        hand_text = """Poker Hand #GG1234567894: Tournament #206881959, 10 Hold'em No Limit - Level10(200/400) - 2025/01/01 16:50:00
Table '206881959' 9-max Seat #1 is the button
Seat 1: Hero (3000 in chips)
Seat 2: BigStack (15000 in chips)
Hero: posts ante 80
BigStack: posts ante 80
Hero: posts small blind 200
BigStack: posts big blind 400
*** HOLE CARDS ***
Dealt to Hero [As Ks]
Hero: raises 2,320 to 2,920 and is all-in
BigStack: calls 2520
*** FLOP *** [Ah 7d 2c]
*** TURN *** [Ah 7d 2c] [Kd]
*** RIVER *** [Ah 7d 2c Kd] [9h]
*** SHOWDOWN ***
Hero: shows [As Ks]
BigStack: shows [Qc Jc]
Hero collected 6000 from pot
*** SUMMARY ***
Total pot 6000
"""
        
        result = self.parser.parse(hand_text)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['final_table_hands_data']), 1)
        hand_data = result['final_table_hands_data'][0]
        
        print(f"\nTest: {self._testMethodName}")
        print(f"Hero stack: 3000")
        print(f"BigStack stack: 15000")
        print(f"Hero covers BigStack: No (3000 < 15000)")
        print(f"Hero won pot: Yes")
        print(f"Hero KO count: {hand_data['hero_ko_this_hand']}")
        
        self.assertEqual(hand_data['hero_ko_this_hand'], 0, 
                         "No KO when Hero doesn't cover opponent's stack")

if __name__ == '__main__':
    unittest.main(verbose=2)