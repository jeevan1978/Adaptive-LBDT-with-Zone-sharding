import unittest
import numpy as np
from src.reputation.model import ReputationManager
from src.auction.auction import DoubleAuction

class TestReputationManager(unittest.TestCase):
    def setUp(self):
        self.rm = ReputationManager(a=1.0, b=0.7, c=0.5, gamma=0.95, delta_pos=0.1, delta_neg=-2.0)

    def test_initial_reputation(self):
        rep = self.rm.get_reputation("V1")
        # For r_n = 0, exp(-0.7) is approx 0.4966
        self.assertAlmostEqual(rep, 0.4966, places=4)

    def test_reputation_growth(self):
        # Apply 3 positive interactions
        rep = self.rm.get_reputation("V2")
        for _ in range(3):
            rep = self.rm.add_interaction("V2", is_positive=True, n_peers=100)
        
        # Reputation should increase from initial ~0.5
        self.assertTrue(rep > 0.5)

    def test_reputation_penalty(self):
        # Apply a negative interaction
        rep_before = self.rm.get_reputation("V3")
        rep_after = self.rm.add_interaction("V3", is_positive=False, n_peers=100)
        
        # Reputation should decrease drastically
        self.assertTrue(rep_after < rep_before)
        self.assertTrue(rep_after < 0.2)

    def test_adaptive_reputation_and_classifier(self):
        # 1. Cold start honesty should be 1.0
        p_honest = self.rm.get_honesty_probability("V_test")
        self.assertEqual(p_honest, 1.0)
        
        # 2. Add negative behavior (simulating cheating)
        self.rm.update_features("V_test", "active_steps", 10)
        self.rm.update_features("V_test", "cheated_trades", 1)
        p_honest_after_cheat = self.rm.get_honesty_probability("V_test")
        self.assertTrue(p_honest_after_cheat < 0.5)
        
        # 3. Verify adaptive reputation
        rep = self.rm.add_interaction("V_test", is_positive=False)
        self.assertTrue(rep < 0.1)

class TestDoubleAuction(unittest.TestCase):
    def setUp(self):
        self.rm = ReputationManager()
        self.da = DoubleAuction(reputation_manager=self.rm)

    def test_loss_function_adjustment(self):
        # Setup an offer
        offers = [{'seller_id': 'V1', 'zone': 1, 'price': 10.0, 'quantity': 5.0, 'time': 10.0}]
        # At time 10, no time difference (t_now = 10.0)
        # Default rep for V1 is ~0.5. Delta rep = 1 - 0.5 = 0.5
        # loss = 0.5 * (0.0)^1 + 0.5 * (0.5)^1 = 0.25
        # Expected adjusted price = 10.0 + 0.25 = 10.25
        self.da._apply_loss_function(offers, t_now=10.0)
        self.assertAlmostEqual(offers[0]['adjusted_price'], 10.2517, places=4)

    def test_double_auction_matching(self):
        # 2 sellers in zone 1
        offers = [
            {'seller_id': 'S1', 'zone': 1, 'price': 10.0, 'quantity': 5.0, 'time': 100.0},
            {'seller_id': 'S2', 'zone': 1, 'price': 12.0, 'quantity': 10.0, 'time': 100.0}
        ]
        # 2 buyers in zone 1
        bids = [
            {'buyer_id': 'B1', 'zone': 1, 'price': 15.0, 'quantity': 6.0},
            {'buyer_id': 'B2', 'zone': 1, 'price': 8.0, 'quantity': 5.0}
        ]
        
        # Set reputation for participants to ensure deterministic sorting
        # S1 reputation higher than S2
        self.rm.reputations['S1'] = 0.8
        self.rm.reputations['S2'] = 0.6
        # B1 reputation higher than B2
        self.rm.reputations['B1'] = 0.7
        self.rm.reputations['B2'] = 0.5
        
        # Run auction at t_now = 100.0 (no time delay loss)
        # Loss adjustment:
        # S1 loss = 0.5 * (1 - 0.8) = 0.1 => adjusted price = 10.1
        # S2 loss = 0.5 * (1 - 0.6) = 0.2 => adjusted price = 12.2
        #
        # Sorted Adjusted Offers: S1 (10.1), S2 (12.2)
        # Sorted Bids: B1 (15.0), B2 (8.0)
        #
        # Crossing point search:
        # i=0: S1 (10.1) <= B1 (15.0) -> l=1, m=1
        # i=1: S2 (12.2) > B2 (8.0) -> break
        # Winners: S1 (quantity 5) and B1 (quantity 6)
        # Clearing Price: p_win = min(B1 price, S2 adjusted price) = min(15.0, 12.2) = 12.2
        
        trades, winning_buyers, winning_sellers = self.da.run_auction(offers, bids, t_now=100.0)
        
        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(trade['seller_id'], 'S1')
        self.assertEqual(trade['buyer_id'], 'B1')
        self.assertEqual(trade['price'], 12.2)
        self.assertEqual(trade['quantity'], 5.0)  # Min of S1 supply (5) and B1 demand (6)
        self.assertIn('B1', winning_buyers)
        self.assertIn('S1', winning_sellers)

if __name__ == '__main__':
    unittest.main()
