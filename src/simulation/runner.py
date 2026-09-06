import os
import sys
import time
import random
import hashlib
import json
import traci
from ecdsa import SigningKey, SECP256k1

# Import local modules
from src.reputation.model import ReputationManager
from src.auction.auction import DoubleAuction
from src.blockchain.ledger import Transaction, Microblock, Keyblock
from src.blockchain.consensus import ConsensusEngine

def generate_keypair(node_id):
    """
    Generates a deterministic ECDSA key pair quickly for simulation nodes.
    """
    priv_seed = hashlib.sha256(f"seed_{node_id}".encode('utf-8')).hexdigest()
    sk = SigningKey.from_string(bytes.fromhex(priv_seed), curve=SECP256k1)
    vk = sk.get_verifying_key()
    return priv_seed, vk.to_string().hex()

class SimulationRunner:
    def __init__(self, sim_steps=300, keyblock_epoch=60, mal_veh_ratio=0.2, mal_rsu_ratio=0.15):
        self.sim_steps = sim_steps
        self.keyblock_epoch = keyblock_epoch
        self.mal_veh_ratio = mal_veh_ratio
        self.mal_rsu_ratio = mal_rsu_ratio
        
        # Initialize Core Engines
        self.reputation_manager = ReputationManager()
        self.consensus_engine = ConsensusEngine(self.reputation_manager)
        self.double_auction = DoubleAuction(reputation_manager=self.reputation_manager)
        
        # Define simulation entities
        self.vehicles = {}  # ID -> {'keys': (priv, pub), 'is_malicious': bool}
        self.rsus = {}      # ID -> {'x': float, 'y': float, 'keys': (priv, pub), 'is_malicious': bool}
        
        # Committee details
        self.current_committee = []
        
        # Metrics logs
        self.latency_log = []       # lists of (T_confirm - T_gen)
        self.bft_msg_log = 0        # cumulative BFT messages
        self.committee_safety_log = [] # epoch logs of malicious committee reputation
        
        # Blockchain states
        self.keychain = []
        self.microchain = []
        
        # Dynamic Geographic Zones Configuration
        self.zones = {}
        # Initial 16 zones in a 4x4 grid spanning 10 km x 10 km (0 to 10000 on x and y)
        for z_id in range(16):
            xmin = (z_id // 4) * 2500
            xmax = xmin + 2500
            ymin = (z_id % 4) * 2500
            ymax = ymin + 2500
            self.zones[str(z_id)] = {
                'xmin': xmin, 'xmax': xmax,
                'ymin': ymin, 'ymax': ymax,
                'cooldown': 0, # cool-down in epochs
                'last_latency_sum': 0.0,
                'last_latency_count': 0
            }
            
        self.pending_transactions = {z_id: [] for z_id in self.zones.keys()}
        self.zone_committees = {}
        
        self._initialize_entities()

    def _initialize_entities(self):
        print("Initializing vehicles and RSUs...")
        # 1. Initialize 10000 Vehicles
        for i in range(10000):
            veh_id = f"veh_{i}"
            is_mal = random.random() < self.mal_veh_ratio
            priv, pub = generate_keypair(veh_id)
            self.vehicles[veh_id] = {
                'keys': (priv, pub),
                'is_malicious': is_mal
            }
            # Register in consensus engine and initialize reputation
            self.consensus_engine.register_node(veh_id, priv, pub)
            self.reputation_manager.get_reputation(veh_id)
            
        # 2. Initialize 400 RSUs on a 20x20 grid across 10 km x 10 km
        rsu_count = 0
        for x_idx in range(20):
            for y_idx in range(20):
                x = x_idx * 500 + 250
                y = y_idx * 500 + 250
                rsu_id = f"rsu_{rsu_count}"
                is_mal = random.random() < self.mal_rsu_ratio
                priv, pub = generate_keypair(rsu_id)
                self.rsus[rsu_id] = {
                    'x': x,
                    'y': y,
                    'keys': (priv, pub),
                    'is_malicious': is_mal
                }
                # Register in consensus and reputation
                self.consensus_engine.register_node(rsu_id, priv, pub)
                self.reputation_manager.get_reputation(rsu_id)
                rsu_count += 1
                
        # 3. Choose initial BFT committee (globally and per-zone)
        self.update_zone_committees()
        self.current_committee = list(set(rsu for comm in self.zone_committees.values() for rsu in comm))
        print(f"Initial BFT committee selected with {len(self.current_committee)} members.")

    def get_zone_id(self, x, y):
        for z_id, z_data in self.zones.items():
            if z_data['xmin'] <= x < z_data['xmax'] and z_data['ymin'] <= y < z_data['ymax']:
                return z_id
        # Fallback to nearest zone
        min_dist = float('inf')
        best_id = "0"
        for z_id, z_data in self.zones.items():
            cx = (z_data['xmin'] + z_data['xmax']) / 2.0
            cy = (z_data['ymin'] + z_data['ymax']) / 2.0
            dist = ((x - cx)**2 + (y - cy)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                best_id = z_id
        return best_id

    def get_rsus_in_zone(self, zone_id):
        z_data = self.zones[zone_id]
        rsu_in_zone = []
        for rsu_id, rsu_info in self.rsus.items():
            if z_data['xmin'] <= rsu_info['x'] <= z_data['xmax'] and z_data['ymin'] <= rsu_info['y'] <= z_data['ymax']:
                rsu_in_zone.append(rsu_id)
        return rsu_in_zone

    def update_zone_committees(self):
        self.zone_committees = {}
        for z_id in self.zones.keys():
            rsus_in_zone = self.get_rsus_in_zone(z_id)
            if not rsus_in_zone:
                # If no RSU is in bounds, fallback: select the nearest 3 RSUs
                rsu_dists = []
                z_data = self.zones[z_id]
                cx = (z_data['xmin'] + z_data['xmax']) / 2.0
                cy = (z_data['ymin'] + z_data['ymax']) / 2.0
                for r_id, r_info in self.rsus.items():
                    dist = ((r_info['x'] - cx)**2 + (r_info['y'] - cy)**2)**0.5
                    rsu_dists.append((r_id, dist))
                rsu_dists.sort(key=lambda x: x[1])
                nearest_rsus = [x[0] for x in rsu_dists[:3]]
                self.zone_committees[z_id] = self.consensus_engine.select_committee(nearest_rsus)
            else:
                self.zone_committees[z_id] = self.consensus_engine.select_committee(rsus_in_zone)

    def evaluate_sharding(self, step):
        print(f"[Zone Manager] Evaluating dynamic sharding at step {step}...")
        
        # 1. Gather vehicle density and honesty stats per zone
        active_vehs = traci.vehicle.getIDList()
        zone_vehicles = {z_id: [] for z_id in self.zones.keys()}
        for veh_id in active_vehs:
            if veh_id in self.vehicles:
                try:
                    x, y = traci.vehicle.getPosition(veh_id)
                    z_id = self.get_zone_id(x, y)
                    zone_vehicles[z_id].append(veh_id)
                except Exception:
                    continue
                    
        # Trace splits
        zones_to_split = []
        for z_id, z_data in list(self.zones.items()):
            vehs = zone_vehicles.get(z_id, [])
            V_z = len(vehs)
            
            # Compute average wait latency
            if z_data['last_latency_count'] > 0:
                T_wait = z_data['last_latency_sum'] / z_data['last_latency_count']
            else:
                T_wait = 0.0
                
            # Compute average honesty and adversary ratio
            if V_z > 0:
                honesty_probs = [self.reputation_manager.get_honesty_probability(v) for v in vehs]
                adv_count = sum(1 for p in honesty_probs if p < 0.5)
                R_adv = adv_count / V_z
            else:
                R_adv = 0.0
                
            # Calculate Joint Utility Load Score (Uz)
            V_max = 50.0  # Capacity threshold for our simulation scale
            T_limit = 3.0 # Target latency limit
            
            U_z = 0.3 * min(1.0, V_z / V_max) + 0.3 * min(1.0, T_wait / T_limit) + 0.4 * R_adv
            
            print(f"[Zone Manager] Zone {z_id}: Vehs={V_z}, Latency={T_wait:.2f}s, AdvRatio={R_adv:.2f}, LoadScore={U_z:.4f}")
            
            # Reset latency values for the next epoch
            z_data['last_latency_sum'] = 0.0
            z_data['last_latency_count'] = 0
            
            # Decrease cooldown if active
            if z_data['cooldown'] > 0:
                z_data['cooldown'] -= 1
                
            # Split Trigger
            if (U_z > 0.8 or R_adv >= 0.33) and z_data['cooldown'] == 0:
                # Check constraints
                width = z_data['xmax'] - z_data['xmin']
                height = z_data['ymax'] - z_data['ymin']
                if width > 625 and height > 625 and V_z >= 10:
                    zones_to_split.append(z_id)
                    
        # Process splits
        for z_id in zones_to_split:
            z_data = self.zones[z_id]
            width = z_data['xmax'] - z_data['xmin']
            height = z_data['ymax'] - z_data['ymin']
            
            # Determine split direction: split along the larger dimension
            if width >= height:
                # Vertical split
                mid_x = (z_data['xmin'] + z_data['xmax']) / 2.0
                z_A = {
                    'xmin': z_data['xmin'], 'xmax': mid_x,
                    'ymin': z_data['ymin'], 'ymax': z_data['ymax'],
                    'cooldown': 5, 'last_latency_sum': 0.0, 'last_latency_count': 0
                }
                z_B = {
                    'xmin': mid_x, 'xmax': z_data['xmax'],
                    'ymin': z_data['ymin'], 'ymax': z_data['ymax'],
                    'cooldown': 5, 'last_latency_sum': 0.0, 'last_latency_count': 0
                }
            else:
                # Horizontal split
                mid_y = (z_data['ymin'] + z_data['ymax']) / 2.0
                z_A = {
                    'xmin': z_data['xmin'], 'xmax': z_data['xmax'],
                    'ymin': z_data['ymin'], 'ymax': mid_y,
                    'cooldown': 5, 'last_latency_sum': 0.0, 'last_latency_count': 0
                }
                z_B = {
                    'xmin': z_data['xmin'], 'xmax': z_data['xmax'],
                    'ymin': mid_y, 'ymax': z_data['ymax'],
                    'cooldown': 5, 'last_latency_sum': 0.0, 'last_latency_count': 0
                }
                
            # Remove parent, add children
            del self.zones[z_id]
            id_A, id_B = f"{z_id}_0", f"{z_id}_1"
            self.zones[id_A] = z_A
            self.zones[id_B] = z_B
            
            # Distribute pending transactions to the correct sub-zones
            parent_txs = self.pending_transactions.pop(z_id, [])
            self.pending_transactions[id_A] = []
            self.pending_transactions[id_B] = []
            
            for tx in parent_txs:
                buyer = tx.info.get('buyer')
                seller = tx.info.get('seller')
                target = tx.info.get('target')
                node_id = buyer or seller or target
                
                # Check position of the node if active in SUMO, else put in A
                mapped = False
                if node_id and node_id in active_vehs:
                    try:
                        x, y = traci.vehicle.getPosition(node_id)
                        if z_A['xmin'] <= x <= z_A['xmax'] and z_A['ymin'] <= y <= z_A['ymax']:
                            self.pending_transactions[id_A].append(tx)
                            mapped = True
                        elif z_B['xmin'] <= x <= z_B['xmax'] and z_B['ymin'] <= y <= z_B['ymax']:
                            self.pending_transactions[id_B].append(tx)
                            mapped = True
                    except Exception:
                        pass
                if not mapped:
                    if random.random() < 0.5:
                        self.pending_transactions[id_A].append(tx)
                    else:
                        self.pending_transactions[id_B].append(tx)
                        
            print(f"[Zone Manager] Splitted Zone {z_id} -> {id_A} and {id_B}")
            
        # 2. Check for merges
        zones_to_merge = []
        already_merged = set()
        
        zone_keys = list(self.zones.keys())
        for i in range(len(zone_keys)):
            for j in range(i + 1, len(zone_keys)):
                id_A = zone_keys[i]
                id_B = zone_keys[j]
                
                if id_A in already_merged or id_B in already_merged:
                    continue
                    
                z_A = self.zones[id_A]
                z_B = self.zones[id_B]
                
                if z_A['cooldown'] > 0 or z_B['cooldown'] > 0:
                    continue
                    
                # Compute load score and adversary ratio
                V_A = len(zone_vehicles.get(id_A, []))
                V_B = len(zone_vehicles.get(id_B, []))
                
                R_adv_A = sum(1 for v in zone_vehicles.get(id_A, []) if self.reputation_manager.get_honesty_probability(v) < 0.5) / max(1, V_A)
                R_adv_B = sum(1 for v in zone_vehicles.get(id_B, []) if self.reputation_manager.get_honesty_probability(v) < 0.5) / max(1, V_B)
                
                U_A = 0.3 * min(1.0, V_A / 50.0) + 0.4 * R_adv_A
                U_B = 0.3 * min(1.0, V_B / 50.0) + 0.4 * R_adv_B
                
                # Merge condition: Combined load score < 0.3 and low adversary ratio
                if U_A + U_B < 0.3 and R_adv_A < 0.1 and R_adv_B < 0.1:
                    is_adjacent = False
                    # Check horizontal adjacency
                    if z_A['ymin'] == z_B['ymin'] and z_A['ymax'] == z_B['ymax']:
                        if z_A['xmax'] == z_B['xmin'] or z_B['xmax'] == z_A['xmin']:
                            is_adjacent = True
                    # Check vertical adjacency
                    elif z_A['xmin'] == z_B['xmin'] and z_A['xmax'] == z_B['xmax']:
                        if z_A['ymax'] == z_B['ymin'] or z_B['ymax'] == z_A['ymin']:
                            is_adjacent = True
                            
                    if is_adjacent:
                        # Check size constraint: union area <= 25 sq km (25,000,000 m^2)
                        union_xmin = min(z_A['xmin'], z_B['xmin'])
                        union_xmax = max(z_A['xmax'], z_B['xmax'])
                        union_ymin = min(z_A['ymin'], z_B['ymin'])
                        union_ymax = max(z_A['ymax'], z_B['ymax'])
                        
                        area = (union_xmax - union_xmin) * (union_ymax - union_ymin)
                        if area <= 25000000.0:
                            zones_to_merge.append((id_A, id_B, {
                                'xmin': union_xmin, 'xmax': union_xmax,
                                'ymin': union_ymin, 'ymax': union_ymax,
                                'cooldown': 5, 'last_latency_sum': 0.0, 'last_latency_count': 0
                            }))
                            already_merged.add(id_A)
                            already_merged.add(id_B)
                            
        # Process merges
        for id_A, id_B, merged_data in zones_to_merge:
            merged_id = f"{id_A}_{id_B}"
            self.zones[merged_id] = merged_data
            
            # Merge pending transactions
            txs_A = self.pending_transactions.pop(id_A, [])
            txs_B = self.pending_transactions.pop(id_B, [])
            self.pending_transactions[merged_id] = txs_A + txs_B
            
            # Remove parents
            del self.zones[id_A]
            del self.zones[id_B]
            
            print(f"[Zone Manager] Merged Zones {id_A} and {id_B} -> {merged_id}")
            
        # Re-update committees
        self.update_zone_committees()

    def run(self):
        # Start SUMO in GUI mode for visual execution
        print("Starting SUMO GUI...")
        sumo_binary = "sumo-gui"
        traci.start([sumo_binary, "-c", "data/config.sumocfg", "--start", "--no-warnings"])
        
        step = 0
        last_keyblock_hash = "0" * 64
        last_microblock_hash = "0" * 64
        
        try:
            while step < self.sim_steps:
                traci.simulationStep()
                
                # 1. Get vehicle positions and group under covering RSUs
                active_vehs = traci.vehicle.getIDList()
                rsu_offers = {z_id: [] for z_id in self.zones.keys()}
                rsu_bids = {z_id: [] for z_id in self.zones.keys()}
                
                for veh_id in active_vehs:
                    # In SUMO active list might contain new vehicles not pre-registered
                    if veh_id not in self.vehicles:
                        is_mal = random.random() < self.mal_veh_ratio
                        priv, pub = generate_keypair(veh_id)
                        self.vehicles[veh_id] = {
                            'keys': (priv, pub),
                            'is_malicious': is_mal
                        }
                        self.consensus_engine.register_node(veh_id, priv, pub)
                        self.reputation_manager.get_reputation(veh_id)
                        
                    x, y = traci.vehicle.getPosition(veh_id)
                    
                    # Find nearest covering RSU (within 300m range) via grid lookup
                    best_rsu = None
                    x_idx = max(0, min(19, int(round((x - 250) / 500))))
                    y_idx = max(0, min(19, int(round((y - 250) / 500))))
                    rsu_id = f"rsu_{x_idx * 20 + y_idx}"
                    rsu_data = self.rsus[rsu_id]
                    dist = ((x - rsu_data['x'])**2 + (y - rsu_data['y'])**2)**0.5
                    if dist <= 300.0:
                        best_rsu = rsu_id
                            
                    if best_rsu:
                        # Find dynamic zone ID
                        zone_id = self.get_zone_id(x, y)
                        
                        # Simulate packet drops for network noise & feature collection
                        # Malicious nodes drop packets more frequently (e.g. 15% rate)
                        # Honest nodes drop occasionally due to random signal loss (e.g. 2% rate)
                        is_malicious = self.vehicles[veh_id]['is_malicious']
                        drop_prob = 0.15 if is_malicious else 0.02
                        if random.random() < drop_prob:
                            self.reputation_manager.update_features(veh_id, 'packet_drops', 1)
                        
                        # 0.2 probability of trading data in this step
                        if random.random() < 0.2:
                            # Seller or Buyer?
                            if random.random() < 0.5:
                                # Seller Offer
                                offer = {
                                    'seller_id': veh_id,
                                    'zone': zone_id,
                                    'price': random.uniform(5.0, 10.0),
                                    'quantity': random.uniform(1.0, 5.0),
                                    'time': float(step)
                                }
                                rsu_offers[zone_id].append(offer)
                            else:
                                # Buyer Bid
                                bid = {
                                    'buyer_id': veh_id,
                                    'zone': zone_id,
                                    'price': random.uniform(6.0, 12.0),
                                    'quantity': random.uniform(1.0, 5.0)
                                }
                                rsu_bids[zone_id].append(bid)
                
                # 2. Run double auctions at RSU brokers for each zone
                for zone_id in list(self.zones.keys()):
                    offers = rsu_offers[zone_id]
                    bids = rsu_bids[zone_id]
                    if offers and bids:
                        trades, win_buyers, win_sellers = self.double_auction.run_auction(offers, bids, float(step))
                        
                        # Process trades and create transactions
                        for trade in trades:
                            seller = trade['seller_id']
                            buyer = trade['buyer_id']
                            
                            # Determine behavior and feed feedback transaction
                            seller_cheated = self.vehicles[seller]['is_malicious'] and random.random() < 0.8
                            buyer_cheated = self.vehicles[buyer]['is_malicious'] and random.random() < 0.8
                            
                            # Seller interaction feedback
                            feedback_seller = not seller_cheated
                            tx_rep_seller = Transaction(
                                tx_type='reputation',
                                timestamp=float(step),
                                info={'target': seller, 'feedback': feedback_seller, 'zone_id': zone_id}
                            )
                            tx_rep_seller.sign(self.vehicles[buyer]['keys'][0])
                            self.pending_transactions[zone_id].append(tx_rep_seller)
                            
                            # Buyer interaction feedback
                            feedback_buyer = not buyer_cheated
                            tx_rep_buyer = Transaction(
                                tx_type='reputation',
                                timestamp=float(step),
                                info={'target': buyer, 'feedback': feedback_buyer, 'zone_id': zone_id}
                            )
                            tx_rep_buyer.sign(self.vehicles[seller]['keys'][0])
                            self.pending_transactions[zone_id].append(tx_rep_buyer)
                            
                            # Also generate payment transaction
                            tx_pay = Transaction(
                                tx_type='payment',
                                timestamp=float(step),
                                info={'seller': seller, 'buyer': buyer, 'amount': trade['price'] * trade['quantity'], 'zone_id': zone_id}
                            )
                            tx_pay.sign(self.vehicles[buyer]['keys'][0])
                            self.pending_transactions[zone_id].append(tx_pay)
                            
                # 3. Commit Microblocks every round (6 seconds) for each active zone (shard)
                if step > 0 and step % 6 == 0:
                    for zone_id in list(self.zones.keys()):
                        zone_txs = self.pending_transactions.get(zone_id, [])
                        if zone_txs:
                            committee = self.zone_committees.get(zone_id, [])
                            if not committee:
                                rsus_in_zone = self.get_rsus_in_zone(zone_id)
                                committee = self.consensus_engine.select_committee(rsus_in_zone)
                                self.zone_committees[zone_id] = committee
                                
                            if committee:
                                seed = f"{last_keyblock_hash}:{step}:{zone_id}"
                                leader, vrf_val, proof = self.consensus_engine.elect_leader(committee, seed)
                                if leader:
                                    mb = Microblock(
                                        prev_hash=last_microblock_hash,
                                        keyblock_ref=last_keyblock_hash,
                                        transactions=zone_txs.copy(),
                                        leader_id=leader
                                    )
                                    success, msgs = self.consensus_engine.run_gosig_bft(mb, committee, leader)
                                    if success:
                                        self.microchain.append(mb)
                                        last_microblock_hash = mb.hash
                                        self.bft_msg_log += msgs
                                        
                                        # Log latencies for transactions inside this microblock
                                        for tx in mb.transactions:
                                            latency = step - tx.timestamp
                                            self.latency_log.append(latency)
                                            self.zones[zone_id]['last_latency_sum'] += latency
                                            self.zones[zone_id]['last_latency_count'] += 1
                                            
                                        # Clear pending pool
                                        self.pending_transactions[zone_id].clear()
                            
                # 4. Generate Keyblock every epoch (60 seconds)
                if step > 0 and step % self.keyblock_epoch == 0:
                    print(f"Epoch boundary reached at step {step}. Generating Keyblock...")
                    # Calculate reputation changes from the microblocks of the last epoch
                    epoch_feedback = {}
                    
                    # Iterate through microblocks added in this epoch
                    start_idx = max(0, len(self.microchain) - self.keyblock_epoch)
                    for mb in self.microchain[start_idx:]:
                        for tx in mb.transactions:
                            if tx.tx_type == 'reputation':
                                target = tx.info['target']
                                fb = tx.info['feedback']
                                if target not in epoch_feedback:
                                    epoch_feedback[target] = []
                                epoch_feedback[target].append(fb)
                                
                    # Update reputation in memory and construct the Keyblock representation
                    rep_changes = {}
                    for target, feedbacks in epoch_feedback.items():
                        for fb in feedbacks:
                            self.reputation_manager.add_interaction(target, fb)
                        rep_changes[target] = self.reputation_manager.get_reputation(target)
                        
                    # Reward committee members for maintaining network
                    rewarded_rsus = set()
                    for committee in self.zone_committees.values():
                        rewarded_rsus.update(committee)
                    for rsu_id in rewarded_rsus:
                        self.reputation_manager.add_interaction(rsu_id, True)
                        rep_changes[rsu_id] = self.reputation_manager.get_reputation(rsu_id)
                        
                    # Mine Keyblock
                    all_committee_members = []
                    for comm in self.zone_committees.values():
                        all_committee_members.extend(comm)
                    if not all_committee_members:
                        all_committee_members = list(self.rsus.keys())
                    miner = random.choice(all_committee_members)
                    
                    kb = Keyblock(
                        prev_hash=last_keyblock_hash,
                        prev_mb_hash=last_microblock_hash,
                        rep_changes=rep_changes,
                        miner_id=miner
                    )
                    kb.mine(difficulty=2)
                    
                    # Run BFT consensus to verify and commit keyblock
                    success, msgs = self.consensus_engine.run_gosig_bft(kb, self.current_committee, miner)
                    if success:
                        self.keychain.append(kb)
                        last_keyblock_hash = kb.hash
                        self.bft_msg_log += msgs
                        print(f"Keyblock committed successfully. Hash: {kb.hash[:16]}")
                        
                        # Evaluate dynamic sharding rules (splits and merges)
                        self.evaluate_sharding(step)
                        
                        # Re-select BFT committee based on updated reputations
                        self.current_committee = list(set(rsu for comm in self.zone_committees.values() for rsu in comm))
                        
                        # Monitor and log Committee Safety
                        committee_reps = [self.reputation_manager.get_reputation(r) for r in self.current_committee]
                        mal_committee_reps = [
                            self.reputation_manager.get_reputation(r) 
                            for r in self.current_committee if self.rsus[r]['is_malicious']
                        ]
                        
                        comm_rep_sum = sum(committee_reps)
                        mal_rep_sum = sum(mal_committee_reps)
                        mal_ratio = mal_rep_sum / comm_rep_sum if comm_rep_sum > 0 else 0
                        
                        self.committee_safety_log.append({
                            'step': step,
                            'committee_size': len(self.current_committee),
                            'total_reputation': comm_rep_sum,
                            'malicious_reputation': mal_rep_sum,
                            'malicious_ratio': mal_ratio
                        })
                        print(f"BFT Committee Safety: Malicious Reputation Ratio = {mal_ratio:.4f} (Threshold < 0.3333)")
                        
                step += 1
                
        finally:
            traci.close()
            print("SUMO closed.")
            
        self.save_metrics()

    def save_metrics(self):
        # Calculate statistics
        avg_latency = sum(self.latency_log) / len(self.latency_log) if self.latency_log else 0.0
        max_latency = max(self.latency_log) if self.latency_log else 0.0
        
        # Calculate average reputation of normal vs malicious vehicles
        normal_veh_reps = [
            self.reputation_manager.get_reputation(v) 
            for v, data in self.vehicles.items() if not data['is_malicious']
        ]
        mal_veh_reps = [
            self.reputation_manager.get_reputation(v) 
            for v, data in self.vehicles.items() if data['is_malicious']
        ]
        
        avg_normal_rep = sum(normal_veh_reps) / len(normal_veh_reps) if normal_veh_reps else 0.0
        avg_mal_rep = sum(mal_veh_reps) / len(mal_veh_reps) if mal_veh_reps else 0.0
        
        metrics = {
            'avg_latency': avg_latency,
            'max_latency': max_latency,
            'bft_msg_count': self.bft_msg_log,
            'committee_safety': self.committee_safety_log,
            'avg_normal_reputation': avg_normal_rep,
            'avg_malicious_reputation': avg_mal_rep,
            'blockchain_keyblocks': len(self.keychain),
            'blockchain_microblocks': len(self.microchain)
        }
        
        with open('data/simulation_log.json', 'w') as f:
            json.dump(metrics, f, indent=4)
            
        with open('data/simulation_log.js', 'w') as f:
            f.write(f"const simulationMetrics = {json.dumps(metrics, indent=4)};")
            
        print("\n--- Simulation Metrics Summary ---")
        print(f"Keyblocks committed: {len(self.keychain)}")
        print(f"Microblocks committed: {len(self.microchain)}")
        print(f"Average Transaction Latency: {avg_latency:.4f} seconds")
        print(f"Total BFT Messages Exchanged: {self.bft_msg_log}")
        print(f"Average Normal Node Reputation: {avg_normal_rep:.4f}")
        print(f"Average Malicious Node Reputation: {avg_mal_rep:.4f}")
        
        # Verify committee safety threshold
        all_safe = True
        for log in self.committee_safety_log:
            if log['malicious_ratio'] >= 0.3333:
                all_safe = False
                
        print(f"Safety Threshold Verified (< 1/3 malicious rep in committee): {all_safe}")
        self.export_telemetry_dataset()

    def export_telemetry_dataset(self, filepath="data/telemetry_dataset.csv"):
        import csv
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        print(f"Exporting telemetry dataset for ML training to {filepath}...")
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'node_id', 'honest_trades', 'cheated_trades', 
                'packet_drops', 'active_steps', 'bft_responses', 
                'drop_rate', 'norm_drop_rate', 'is_honest'
            ])
            
            for node_id, feat in self.reputation_manager.features.items():
                active_steps = max(1, feat.get('active_steps', 1))
                packet_drops = feat.get('packet_drops', 0)
                drop_rate = packet_drops / active_steps
                
                is_malicious = False
                if node_id in self.vehicles:
                    is_malicious = self.vehicles[node_id]['is_malicious']
                elif node_id in self.rsus:
                    is_malicious = self.rsus[node_id]['is_malicious']
                    
                is_honest = 0 if is_malicious else 1
                
                writer.writerow([
                    node_id,
                    feat.get('honest_trades', 0),
                    feat.get('cheated_trades', 0),
                    packet_drops,
                    active_steps,
                    feat.get('bft_responses', 0),
                    round(drop_rate, 6),
                    round(drop_rate, 6), # norm_drop_rate
                    is_honest
                ])
        print(f"Exported {len(self.reputation_manager.features)} node telemetry records.")

if __name__ == "__main__":
    runner = SimulationRunner(sim_steps=1000, keyblock_epoch=60)
    runner.run()