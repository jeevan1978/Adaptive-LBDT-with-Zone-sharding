import numpy as np
from src.reputation.model import ReputationManager

class DoubleAuction:
    def __init__(self, reputation_manager=None, alpha_1=0.5, alpha_2=0.5, beta_1=1.0, beta_2=1.0):
        # Allow sharing the same reputation manager instance
        self.reputation_model = reputation_manager if reputation_manager is not None else ReputationManager()
        self.alpha_1 = alpha_1
        self.alpha_2 = alpha_2
        self.beta_1 = beta_1
        self.beta_2 = beta_2

    def run_auction(self, offers, bids, t_now):
        """
        Runs the reputation-based double auction for all zones.
        
        Input: 
            offers: list of dicts, e.g., [{'seller_id': 'V1', 'zone': 1, 'price': 10.0, 'quantity': 5.0, 'time': 120.0}]
            bids: list of dicts, e.g., [{'buyer_id': 'V2', 'zone': 1, 'price': 12.0, 'quantity': 3.0}]
            t_now: current simulation time
            
        Output:
            successful_trades: list of dicts containing transaction results
            winning_buyers: set of buyer IDs who won
            winning_sellers: set of seller IDs who won
        """
        successful_trades = []
        winning_buyers = set()
        winning_sellers = set()
        
        # Group offers and bids by zone
        # We need to know all zones present in the data
        zones = set([o['zone'] for o in offers]) | set([b['zone'] for b in bids])
        
        for k in zones:
            # Obtain the sets SO_k and BB_k for zone Z_k
            SO_k = [dict(o) for o in offers if o['zone'] == k and o['price'] > 0]
            BB_k = [dict(b) for b in bids if b['zone'] == k and b['price'] > 0]
            
            if not SO_k or not BB_k:
                continue
                
            # Step 1: Adjust offers based on reputation and time (loss function)
            self._apply_loss_function(SO_k, t_now)
            
            # Step 2: Search for Market Clearing Point
            # Sort offers ascending by adjusted price
            SO_k.sort(key=lambda x: x['adjusted_price'])
            # Sort bids descending by price
            BB_k.sort(key=lambda x: x['price'], reverse=True)
            
            # Find largest l and m that satisfy SP'_l <= BP_m
            # Since we match index-by-index in sorted curves:
            l = 0
            m = 0
            min_len = min(len(SO_k), len(BB_k))
            for i in range(min_len):
                if SO_k[i]['adjusted_price'] <= BB_k[i]['price']:
                    l = i + 1
                    m = i + 1
                else:
                    break
                    
            if l == 0:
                continue  # No matches in this zone
                
            # Calculate final trading price in zone: p_win = min(BP_m, SP'_{l+1})
            bp_m = BB_k[m - 1]['price']
            sp_lp1 = SO_k[l]['adjusted_price'] if l < len(SO_k) else float('inf')
            p_win = min(bp_m, sp_lp1)
            
            # Filter and keep only the winning sellers and buyers
            SO_k = SO_k[:l]
            BB_k = BB_k[:m]
            
            # Sort both winning sets in descending order of reputation
            for offer in SO_k:
                offer['reputation'] = self.reputation_model.get_reputation(offer['seller_id'])
            for bid in BB_k:
                bid['reputation'] = self.reputation_model.get_reputation(bid['buyer_id'])
                
            SO_k.sort(key=lambda x: x['reputation'], reverse=True)
            BB_k.sort(key=lambda x: x['reputation'], reverse=True)
            
            # Step 3: Match buyers and sellers (two-pointer allocation based on quantity)
            x = 0
            y = 0
            while x < len(SO_k) and y < len(BB_k):
                offer = SO_k[x]
                bid = BB_k[y]
                
                sq = offer['quantity']
                bq = bid['quantity']
                
                if sq <= 0:
                    x += 1
                    continue
                if bq <= 0:
                    y += 1
                    continue
                    
                if bq < sq:
                    q_ij = bq
                    offer['quantity'] -= bq
                    bid['quantity'] = 0.0
                    y += 1
                elif bq > sq:
                    q_ij = sq
                    bid['quantity'] -= sq
                    offer['quantity'] = 0.0
                    x += 1
                else:
                    q_ij = sq
                    offer['quantity'] = 0.0
                    bid['quantity'] = 0.0
                    x += 1
                    y += 1
                    
                trade = {
                    'seller_id': offer['seller_id'],
                    'buyer_id': bid['buyer_id'],
                    'zone': k,
                    'price': p_win,
                    'quantity': q_ij
                }
                successful_trades.append(trade)
                winning_sellers.add(offer['seller_id'])
                winning_buyers.add(bid['buyer_id'])
                
        return successful_trades, winning_buyers, winning_sellers

    def _apply_loss_function(self, offers, t_now):
        """
        SP'_i = SP_i + loss(t_i^k, Rep_i)
        loss = alpha_1 * (t_now - t_i^k)^beta_1 + alpha_2 * (1 - Rep_i)^beta_2
        """
        for offer in offers:
            seller_id = offer['seller_id']
            rep = self.reputation_model.get_reputation(seller_id)
            delta_t = max(0.0, t_now - offer['time'])
            delta_rep = max(0.0, 1.0 - rep)
            
            loss = self.reputation_model.calculate_loss(
                delta_t=delta_t,
                delta_rep=delta_rep,
                alpha_1=self.alpha_1,
                alpha_2=self.alpha_2,
                beta_1=self.beta_1,
                beta_2=self.beta_2
            )
            offer['adjusted_price'] = offer['price'] + loss