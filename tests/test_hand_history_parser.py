import unittest
from parsers.hand_history import HandHistoryParser, NAME, CHIP  # Assuming HandData is not directly needed for tests
import config # For setting HERO_NAME

# Minimal mock for config if needed, or we can set config.HERO_NAME directly.
# For these tests, we will assume config.HERO_NAME can be set.

# Sample Hand History Snippets will be defined within test methods or as class attributes.

class TestHandHistoryParserHeroIdentification(unittest.TestCase):
    def setUp(self):
        self.original_hero_name = config.HERO_NAME
        # Default config for HeroIdentification tests
        config.HERO_NAME = "Hero" 
        config.FINAL_TABLE_SIZE = 9 # Standard final table
        config.MIN_KO_BLIND_LEVEL_BB = 1 # Min blind level for KO, ensure it's low for tests
        self.parser = HandHistoryParser(hero_name="Hero") # Default for most tests
        # Ensure parser's internal self.hero_name and global config match for consistency in tests
        # Forcing HERO_NAME on config for the duration of the test method if it specificies one like HeroExact
        # This will be overridden in test methods if they set config.HERO_NAME specifically.

    def tearDown(self):
        config.HERO_NAME = self.original_hero_name

    def test_hero_identification_exact_match(self):
        config.HERO_NAME = "HeroExact"
        parser = HandHistoryParser(hero_name="HeroExact")
        hand_text = """
Poker Hand #1: Tournament #1, Level1(10/20) - 2023/10/26 10:00:00
Table '1' 9-max Seat #1 is the button
Seat 1: HeroExact (1500 in chips)
Seat 2: Villain1 (1500 in chips)
*** HOLE CARDS ***
HeroExact: posts small blind 10
Villain1: posts big blind 20
HeroExact: folds
*** SUMMARY ***
Total pot 30 | Rake 0
Board []
Seat 1: HeroExact (small blind) folded on Preflop
Seat 2: Villain1 (big blind) collected 30
        """.strip()
        
        parsed_data = parser.parse(hand_text, "test_tournament_exact.txt")
        self.assertTrue(parsed_data['reached_final_table'], "Should have processed a hand.")
        # _parse_hand_chunk finds hero and sets stack in HandData
        # Accessing HandData directly is tricky as it's processed internally.
        # We check hero_stack on the output.
        self.assertEqual(parsed_data['final_table_initial_stack_chips'], 1500)
        
        # To directly test hero_actual_name_in_hand, we'd need to inspect _hands or _final_table_hands
        # For now, correct stack retrieval implies correct identification.
        # Let's check the first hand data if available.
        if parsed_data['final_table_hands_data']:
            hand_info = parsed_data['final_table_hands_data'][0]
            # The hero_actual_name is not directly in final_table_hands_data
            # but hero_stack being correct is a strong indicator.
            self.assertEqual(hand_info['hero_stack'], 1500) 
        else:
            self.fail("No final table hands data found.")


    def test_hero_identification_partial_match_suffix_in_hh(self):
        config.HERO_NAME = "HeroPartial" # Config name
        parser = HandHistoryParser(hero_name="HeroPartial")
        # HH name is "HeroPartial (SN123)"
        hand_text = """
Poker Hand #1: Tournament #1, Level1(10/20) - 2023/10/26 10:00:00
Table '1' 9-max Seat #1 is the button
Seat 1: HeroPartial (SN123) (1600 in chips) 
Seat 2: Villain1 (1500 in chips)
*** HOLE CARDS ***
HeroPartial (SN123): posts small blind 10
Villain1: posts big blind 20
HeroPartial (SN123): folds
*** SUMMARY ***
Total pot 30 | Rake 0
Board []
Seat 1: HeroPartial (SN123) (small blind) folded on Preflop
Seat 2: Villain1 (big blind) collected 30
        """.strip()
        # Need to ensure RE_SEAT and NAME work as expected.
        # RE_SEAT: r'^Seat \d+: (?P<player_name>[^()]+?) \((?P<stack>[-\d,]+) in chips\)'
        # NAME: lambda s: s.strip()
        # For "HeroPartial (SN123) (1600 in chips)":
        # player_name group will be "HeroPartial (SN123) "
        # NAME("HeroPartial (SN123) ") -> "HeroPartial (SN123)"
        # The _find_hero_actual_name should match "HeroPartial" in "HeroPartial (SN123)"
        
        parsed_data = parser.parse(hand_text, "test_tournament_partial.txt")
        self.assertTrue(parsed_data['reached_final_table'])
        self.assertEqual(parsed_data['final_table_initial_stack_chips'], 1600)
        if parsed_data['final_table_hands_data']:
            hand_info = parsed_data['final_table_hands_data'][0]
            self.assertEqual(hand_info['hero_stack'], 1600)
        else:
            self.fail("No final table hands data found for partial match.")

    def test_hero_identification_partial_match_prefix_in_hh(self):
        config.HERO_NAME = "HeroPrefix" # Config name
        parser = HandHistoryParser(hero_name="HeroPrefix")
        # HH name is "HeroPrefixABC"
        hand_text = """
Poker Hand #1: Tournament #1, Level1(10/20) - 2023/10/26 10:00:00
Table '1' 9-max Seat #1 is the button
Seat 1: HeroPrefixABC (1700 in chips) 
Seat 2: Villain1 (1500 in chips)
*** HOLE CARDS ***
HeroPrefixABC: posts small blind 10
Villain1: posts big blind 20
HeroPrefixABC: folds
*** SUMMARY ***
Total pot 30 | Rake 0
Board []
Seat 1: HeroPrefixABC (small blind) folded on Preflop
Seat 2: Villain1 (big blind) collected 30
        """.strip()
        # For "HeroPrefixABC (1700 in chips)":
        # player_name group will be "HeroPrefixABC "
        # NAME("HeroPrefixABC ") -> "HeroPrefixABC"
        # _find_hero_actual_name should match "HeroPrefix" in "HeroPrefixABC"

        parsed_data = parser.parse(hand_text, "test_tournament_prefix.txt")
        self.assertTrue(parsed_data['reached_final_table'])
        self.assertEqual(parsed_data['final_table_initial_stack_chips'], 1700)
        if parsed_data['final_table_hands_data']:
            hand_info = parsed_data['final_table_hands_data'][0]
            self.assertEqual(hand_info['hero_stack'], 1700)
        else:
            self.fail("No final table hands data found for prefix match.")


    def test_hero_not_participating(self):
        config.HERO_NAME = "NonExistentHero"
        parser = HandHistoryParser(hero_name="NonExistentHero")
        hand_text = """
Poker Hand #1: Tournament #1, Level1(10/20) - 2023/10/26 10:00:00
Table '1' 9-max Seat #1 is the button
Seat 1: PlayerA (1500 in chips)
Seat 2: PlayerB (1500 in chips)
*** HOLE CARDS ***
PlayerA: posts small blind 10
PlayerB: posts big blind 20
PlayerA: folds
*** SUMMARY ***
Total pot 30 | Rake 0
Board []
Seat 1: PlayerA (small blind) folded on Preflop
Seat 2: PlayerB (big blind) collected 30
        """.strip()
        
        parsed_data = parser.parse(hand_text, "test_tournament_no_hero.txt")
        # If hero is not in any hand, reached_final_table might be false or hands_data empty
        self.assertFalse(parsed_data['reached_final_table'])
        self.assertIsNone(parsed_data['final_table_initial_stack_chips'])
        self.assertEqual(len(parsed_data['final_table_hands_data']), 0)


class TestHandHistoryParserKOCounting(unittest.TestCase):
    def setUp(self):
        self.original_hero_name = config.HERO_NAME
        # Default config for KO tests
        config.HERO_NAME = "HeroKO" 
        config.FINAL_TABLE_SIZE = 9 # Standard final table
        config.MIN_KO_BLIND_LEVEL_BB = 1 # Min blind level for KO, ensure it's low for tests
        self.parser = HandHistoryParser(hero_name="HeroKO")

    def tearDown(self):
        config.HERO_NAME = self.original_hero_name

    def _create_hand_text(self, hand_id_num, seat1_name, seat1_stack, seat2_name, seat2_stack, seat1_actions, seat2_actions, summary_collections, board_info="Board []"):
        # Helper to create a 2-player hand text for KO scenarios
        # For KO, we need a "next hand" to show elimination.
        # So we'll typically pass two hand texts to the parser.
        hand_text = f"""
Poker Hand #{hand_id_num}: Tournament #100, Level1(50/100) - 2023/10/26 10:00:00
Table '1' 9-max Seat #1 is the button
Seat 1: {seat1_name} ({seat1_stack} in chips)
Seat 2: {seat2_name} ({seat2_stack} in chips)
*** HOLE CARDS ***
{seat1_name}: posts small blind 50
{seat2_name}: posts big blind 100
{seat1_actions}
{seat2_actions}
*** SUMMARY ***
{summary_collections}
{board_info}
""".strip()
        return hand_text

    def _get_first_final_hand_ko_count(self, parsed_data):
        self.assertTrue(parsed_data['reached_final_table'], "Should be a final table hand.")
        self.assertGreater(len(parsed_data['final_table_hands_data']), 0, "No final table hands found.")
        return parsed_data['final_table_hands_data'][0]['hero_ko_this_hand']

    def test_ko_simple_hero_ko(self):
        # Hand 1: Hero KOs Villain
        # Hero has Villain covered. Hero wins pot. Villain eliminated.
        hero_name = "HeroKO"
        villain_name = "VillainX"
        
        hand1_actions_s1 = f"{hero_name}: raises 1000 to 1000" # Hero raises, Villain all-in for less
        hand1_actions_s2 = f"{villain_name}: all-in 400" # Villain all-in for 400 total (SB 50 + BB 100 + Call X -> total 400)
                                                       # This action line needs care. Let's simplify.
        # Simplified actions:
        # Villain (Seat2) posts BB 100, has 400 total. Hero (Seat1) posts SB 50, has 1000.
        # Hero raises to 400. Villain calls all-in 300 more.
        hand1_actions_s1 = f"{hero_name}: raises 350 to 400" # total 400
        hand1_actions_s2 = f"{villain_name}: calls 300 and is all-in" # total 400
        hand1_summary = f"""
Total pot 800 | Rake 0
{hero_name} collected 800 from pot
Seat 2: {villain_name} (big blind) lost with two pair, Kings and Queens
        """.strip()
        # Removed "Seat 1: " and "(small blind)" from Hero's collected line for consistency
        # Assumes RE_COLLECTED gets "HeroKO" as player name.

        hand1_text = self._create_hand_text("KO_H1", hero_name, 1000, villain_name, 400, hand1_actions_s1, hand1_actions_s2, hand1_summary)

        # Hand 2: VillainX is no longer present
        hand2_text = self._create_hand_text("KO_H2", hero_name, 1400, "NewPlayer", 1500, f"{hero_name}: folds", "", f"Total pot 150\nSeat 2: NewPlayer collected 150")
        
        full_hh_text = hand1_text + "\n\n" + hand2_text # Parser expects hands in reverse chronological, but processes them to be chronological.
                                                       # So, hand1 (KO) should be chronologically first.
                                                       # _split_file_into_hand_chunks keeps file order, then reversed for processing.
                                                       # So, hand2 (later) should be first in string, then hand1 (earlier).
        
        full_hh_text_for_parser = hand2_text + "\n\n" + hand1_text


        parsed_data = self.parser.parse(full_hh_text_for_parser, "test_simple_ko_Tournament_#100.txt") #Ensure filename matches regex
        
        # We are interested in KO count from Hand1 (which is chronologically first, thus first in _final_table_hands)
        # The parser processes chunks in reversed order of how they appear in the file if they are chronological.
        # If file is HH standard (last hand first), then reversed(chunks) makes it chronological.
        # My helper _create_hand_text makes one hand.
        # If I want hand1 to be chronologically first: hand1_text then hand2_text.
        # The parser will split, then reverse. So it parses hand1_text then hand2_text.
        # Eliminated players are identified by comparing hand N with hand N+1.
        # So, VillainX is in hand1, not in hand2 -> eliminated in hand1.
        
        # The list final_table_hands_data is ordered chronologically.
        self.assertEqual(len(parsed_data['final_table_hands_data']), 2)
        ko_count_hand1 = parsed_data['final_table_hands_data'][0]['hero_ko_this_hand']
        self.assertEqual(ko_count_hand1, 1, "Hero should have 1 KO in the first hand.")

    def test_ko_hero_partial_name_match(self):
        config.HERO_NAME = "TestHero" # Base name in config
        parser = HandHistoryParser(hero_name="TestHero") # Initialize parser with base name

        hero_hh_name = "TestHero (SN)" # Name as it appears in HH
        villain_name = "VillainY"

        hand1_actions_s1 = f"{hero_hh_name}: raises 350 to 400"
        hand1_actions_s2 = f"{villain_name}: calls 300 and is all-in"
        hand1_summary = f"""
Total pot 800 | Rake 0
{hero_hh_name} collected 800 from pot
Seat 2: {villain_name} (big blind) lost
        """.strip()
        # Removed "Seat 1: " and "(small blind)"
        hand1_text = self._create_hand_text("KO_PN_H1", hero_hh_name, 1000, villain_name, 400, hand1_actions_s1, hand1_actions_s2, hand1_summary)

        hand2_text = self._create_hand_text("KO_PN_H2", hero_hh_name, 1400, "NewPlayerZ", 1500, f"{hero_hh_name}: folds", "", f"Total pot 150\nSeat 2: NewPlayerZ collected 150")
        
        full_hh_text_for_parser = hand2_text + "\n\n" + hand1_text
        parsed_data = parser.parse(full_hh_text_for_parser, "test_partial_name_ko_Tournament_#100.txt") #Ensure filename matches regex
        
        self.assertEqual(len(parsed_data['final_table_hands_data']), 2)
        ko_count_hand1 = parsed_data['final_table_hands_data'][0]['hero_ko_this_hand']
        self.assertEqual(ko_count_hand1, 1, "Hero with partial name match should have 1 KO.")

    def test_no_hero_ko_other_player_kos(self):
        hero_name = "HeroKO"
        active_villain = "VillainA" # This villain will KO another
        busted_villain = "VillainB" # This villain gets KO'd by VillainA

        # Hand 1: VillainA KOs VillainB. Hero is present but does not win the pot.
        # Stacks: Hero: 2000, VillainA: 1000, VillainB: 300
        # For simplicity, make it a 3-player hand.
        # Need to adjust _create_hand_text or make a new helper.
        
        hand1_text = f"""
Poker Hand #NOKO_H1: Tournament #100, Level1(50/100) - 2023/10/26 10:00:00
Table '1' 9-max Seat #1 is the button
Seat 1: {hero_name} (2000 in chips)
Seat 2: {active_villain} (1000 in chips)
Seat 3: {busted_villain} (300 in chips)
*** HOLE CARDS ***
{hero_name}: posts small blind 50
{active_villain}: posts big blind 100
{busted_villain}: is all-in 300  
{hero_name}: folds
{active_villain}: calls 200 
*** SUMMARY ***
Total pot 650 | Rake 0 
Seat 1: {hero_name} (small blind) folded on Preflop
{active_villain} collected 650 from pot
Seat 3: {busted_villain} lost
        """.strip()
        # Removed "Seat 2: " and "(big blind)" from active_villain's collected line for consistency.
        # Note: this test is for "No Hero KO". Consistency of villain names in summary is also important.

        # Hand 2: Busted_villain is no longer present
        hand2_text = f"""
Poker Hand #NOKO_H2: Tournament #100, Level1(50/100) - 2023/10/26 10:05:00
Table '1' 9-max Seat #1 is the button
Seat 1: {hero_name} (1950 in chips)
Seat 2: {active_villain} (1350 in chips)
*** HOLE CARDS ***
{hero_name}: posts small blind 50
{active_villain}: posts big blind 100
{hero_name}: folds
*** SUMMARY ***
Total pot 150 | Rake 0
Seat 2: {active_villain} collected 150
        """.strip()
        
        full_hh_text_for_parser = hand2_text + "\n\n" + hand1_text
        # Corrected: Ensure the right filename is used for this test case
        parsed_data = self.parser.parse(full_hh_text_for_parser, "test_other_player_ko_Tournament_#100.txt") #Ensure filename matches regex
        
        self.assertEqual(len(parsed_data['final_table_hands_data']), 2)
        ko_count_hand1 = parsed_data['final_table_hands_data'][0]['hero_ko_this_hand']
        self.assertEqual(ko_count_hand1, 0, "Hero should have 0 KOs when another player KOs.")

    def test_hero_is_kod(self):
        hero_name = "HeroKO"
        villain_who_kos_hero = "SuperVillain"

        # Hand 1: SuperVillain KOs HeroKO
        hand1_actions_s1 = f"{hero_name}: raises 350 to 400 and is all-in" # Hero has 400 total
        hand1_actions_s2 = f"{villain_who_kos_hero}: calls 350" # Villain has more, calls Hero's all-in
        hand1_summary = f"""
Total pot 800 | Rake 0
Seat 1: {hero_name} (small blind) lost 
{villain_who_kos_hero} collected 800 from pot
        """.strip()
        # Removed "Seat 2: " and "(big blind)"
        hand1_text = self._create_hand_text("HEROKO_H1", hero_name, 400, villain_who_kos_hero, 2000, hand1_actions_s1, hand1_actions_s2, hand1_summary)

        # Hand 2: HeroKO is no longer present
        # For this, the parser will not find Hero in Hand2.
        # The parser logic: parse() iterates through hand_chunks. If hero not in chunk (via _parse_hand_chunk returning None), it's skipped.
        # _identify_eliminated_players works on self._hands.
        # KO counting is on self._final_table_hands.
        # If Hero is KO'd in H1, H1 is still processed, hero_stack is recorded.
        # H2, Hero is not found by _find_hero_actual_name, so _parse_hand_chunk returns None. H2 is not added to self._hands.
        # This means _identify_eliminated_players might have issues if self._hands ends with Hero's elimination.
        # It compares current_hand.players with next_hand.players. If next_hand doesn't exist for Hero, this is fine.
        # The crucial part is that Hero is marked as eliminated in H1.
        
        # Let's make hand2 have only Villain.
        hand2_text = f"""
Poker Hand #HEROKO_H2: Tournament #100, Level1(50/100) - 2023/10/26 10:05:00
Table '1' 9-max Seat #2 is the button
Seat 2: {villain_who_kos_hero} (2400 in chips)
*** HOLE CARDS ***
{villain_who_kos_hero}: posts big blind 100 (missing small blind)
{villain_who_kos_hero}: collected 0 from pot (no opponent)
*** SUMMARY ***
Total pot 0 | Rake 0
Seat 2: {villain_who_kos_hero} collected 0
        """.strip()

        full_hh_text_for_parser = hand2_text + "\n\n" + hand1_text
        parsed_data = self.parser.parse(full_hh_text_for_parser, "test_hero_is_ko_Tournament_#100.txt") #Ensure filename matches regex
        
        # Hand1 should be present in final_table_hands_data
        self.assertEqual(len(parsed_data['final_table_hands_data']), 1) # Only hand1 is Hero's hand
        ko_count_hand1 = parsed_data['final_table_hands_data'][0]['hero_ko_this_hand']
        self.assertEqual(ko_count_hand1, 0, "Hero should have 0 KOs when Hero is KO'd.")
        # Also check that Hero is correctly identified as eliminated in H1 by the logic.
        # This is implicitly tested by the KO count being 0 (as Hero doesn't KO self).
        # The `eliminated_players` for hand1 should include HeroKO.

    def test_ko_multiple_kos_by_hero_in_one_hand(self):
        # Hero KOs VillainA and VillainB in the same hand.
        # Stacks: Hero: 2000, VillainA: 300, VillainB: 400
        hero_name = "HeroKO"
        villain_a = "VillainA"
        villain_b = "VillainB"

        # Hand 1 Text (3 players: Hero, VillainA, VillainB)
        # For simplicity, assume Hero is SB, VA is BB, VB is UTG-equivalent
        # Order of posting: Hero SB (50), VA BB (100), VB all-in (400), Hero calls/raises, VA calls/folds
        hand1_text = f"""
Poker Hand #MULTI_KO_H1: Tournament #100, Level1(50/100) - 2023/10/26 10:00:00
Table '1' 9-max Seat #1 is the button
Seat 1: {hero_name} (2000 in chips)
Seat 2: {villain_a} (300 in chips)
Seat 3: {villain_b} (400 in chips)
*** HOLE CARDS ***
{hero_name}: posts small blind 50
{villain_a}: posts big blind 100
{villain_b}: raises 300 to 400 and is all-in   
{hero_name}: calls 350                  
{villain_a}: calls 200 and is all-in      
*** SUMMARY ***
Total pot 1100 | Rake 0 
{hero_name} collected 1100 from pot
Seat 2: {villain_a} (big blind) lost 
Seat 3: {villain_b} lost
        """.strip()
        # Removed "Seat 1: " and "(small blind)"
        
        # Hand 2 Text (Only Hero left, or Hero + new players)
        hand2_text = self._create_hand_text("MULTI_KO_H2", hero_name, 3100, "NewPlayerY", 1500, f"{hero_name}: folds", "", f"Total pot 150\nSeat 2: NewPlayerY collected 150")

        full_hh_text_for_parser = hand2_text + "\n\n" + hand1_text
        parsed_data = self.parser.parse(full_hh_text_for_parser, "test_multi_ko_Tournament_#100.txt") #Ensure filename matches regex

        self.assertEqual(len(parsed_data['final_table_hands_data']), 2, "Should have two hands processed for Hero.")
        ko_count_hand1 = parsed_data['final_table_hands_data'][0]['hero_ko_this_hand']
        self.assertEqual(ko_count_hand1, 2, "Hero should have 2 KOs for busting VillainA and VillainB.")


if __name__ == '__main__':
    unittest.main()
