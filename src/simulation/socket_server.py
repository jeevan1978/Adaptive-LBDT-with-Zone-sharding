import socket
import json
import threading
import hashlib
import random
from ecdsa import SigningKey, SECP256k1

# Import core modules
from src.reputation.model import ReputationManager
from src.auction.auction import DoubleAuction
from src.blockchain.ledger import Transaction, Microblock, Keyblock
from src.blockchain.consensus import ConsensusEngine

def generate_keypair(node_id):
    priv_seed = hashlib.sha256(f"seed_{node_id}".encode('utf-8')).hexdigest()
    sk = SigningKey.from_string(bytes.fromhex(priv_seed), curve=SECP256k1)
    vk = sk.get_verifying_key()
    return priv_seed, vk.to_string().hex()

class LBDTSocketServer:
    def __init__(self, host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        
        # Initialize Core Engines
        self.reputation_manager = ReputationManager()
        self.consensus_engine = ConsensusEngine(self.reputation_manager)
        self.double_auction = DoubleAuction(reputation_manager=self.reputation_manager)
        
        # Entities & blockchain state
        self.vehicles = {}
        self.rsus = {}
        self.current_committee = []
        self.pending_transactions = []
        self.keychain = []
        self.microchain = []
        
        # Metrics logs
        self.latency_log = []
        self.bft_msg_log = 0
        self.committee_safety_log = []
        
        self._initialize_entities()

    def _initialize_entities(self):
        print("[Python Server] Initializing vehicles and RSUs...")
        # 1. Initialize 10000 Vehicles
        for i in range(10000):
            veh_id = f"veh_{i}"
            is_mal = (i % 5 == 0)  # 20% malicious ratio
            priv, pub = generate_keypair(veh_id)
            self.vehicles[veh_id] = {
                'keys': (priv, pub),
                'is_malicious': is_mal
            }
            self.consensus_engine.register_node(veh_id, priv, pub)
            self.reputation_manager.get_reputation(veh_id)
            
        # 2. Initialize 400 RSUs on a 20x20 grid
        rsu_count = 0
        for x_idx in range(20):
            for y_idx in range(20):
                rsu_id = f"rsu_{rsu_count}"
                is_mal = (rsu_count % 7 == 0)  # ~14% malicious ratio
                priv, pub = generate_keypair(rsu_id)
                self.rsus[rsu_id] = {
                    'x': x_idx * 500 + 250,
                    'y': y_idx * 500 + 250,
                    'keys': (priv, pub),
                    'is_malicious': is_mal
                }
                self.consensus_engine.register_node(rsu_id, priv, pub)
                self.reputation_manager.get_reputation(rsu_id)
                rsu_count += 1
                
        # 3. Choose initial committee
        self.current_committee = self.consensus_engine.select_committee(list(self.rsus.keys()))
        print(f"[Python Server] Initial committee selected: {len(self.current_committee)} members.")

    def handle_client(self, conn, addr):
        buffer = ""
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                
                # Check if we have received a complete JSON message (terminated by newline)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    try:
                        request = json.loads(line)
                        response = self.process_request(request)
                        conn.sendall((json.dumps(response) + "\n").encode('utf-8'))
                    except json.JSONDecodeError:
                        print(f"[Python Server] JSON decode error from {addr}")
                        conn.sendall(json.dumps({"status": "error", "message": "Invalid JSON format"}).encode('utf-8'))
        except Exception as e:
            print(f"[Python Server] Error handling client {addr}: {e}")
        finally:
            conn.close()

    def process_request(self, req):
        cmd = req.get("cmd")
        print(f"[Python Server] Received command: {cmd}")
        
        if cmd == "GET_COMMITTEE":
            return {"status": "ok", "committee": self.current_committee}
            
        elif cmd == "SUBMIT_TRADE_REQUEST":
            # Vehicle submit a bid or offer
            veh_id = req.get("veh_id")
            trade_type = req.get("type")  # "offer" or "bid"
            price = float(req.get("price"))
            quantity = float(req.get("quantity"))
            zone = int(req.get("zone"))
            step = float(req.get("step"))
            
            # Formulate transaction structure for Double Auction input
            trade_data = {
                'seller_id' if trade_type == 'offer' else 'buyer_id': veh_id,
                'type': trade_type,
                'zone': zone,
                'price': price,
                'quantity': quantity,
                'time': step
            }
            return {"status": "ok", "trade_data": trade_data}
            
        elif cmd == "RUN_AUCTION":
            # Run the auction matcher for a specific zone
            offers = req.get("offers", [])
            bids = req.get("bids", [])
            step = float(req.get("step"))
            
            trades, win_buyers, win_sellers = self.double_auction.run_auction(offers, bids, step)
            
            # Generate and queue transactions for successful matches
            for trade in trades:
                seller = trade['seller_id']
                buyer = trade['buyer_id']
                
                seller_cheated = self.vehicles.get(seller, {}).get('is_malicious', False) and random.random() < 0.8
                buyer_cheated = self.vehicles.get(buyer, {}).get('is_malicious', False) and random.random() < 0.8
                
                # Seller interaction feedback transaction
                tx_seller = Transaction(
                    tx_type='reputation',
                    timestamp=step,
                    info={'target': seller, 'feedback': not seller_cheated}
                )
                tx_seller.sign(self.vehicles[buyer]['keys'][0])
                self.pending_transactions.append(tx_seller)
                
                # Buyer interaction feedback transaction
                tx_buyer = Transaction(
                    tx_type='reputation',
                    timestamp=step,
                    info={'target': buyer, 'feedback': not buyer_cheated}
                )
                tx_buyer.sign(self.vehicles[seller]['keys'][0])
                self.pending_transactions.append(tx_buyer)
                
                # Payment transaction
                tx_pay = Transaction(
                    tx_type='payment',
                    timestamp=step,
                    info={'seller': seller, 'buyer': buyer, 'amount': trade['price'] * trade['quantity']}
                )
                tx_pay.sign(self.vehicles[buyer]['keys'][0])
                self.pending_transactions.append(tx_pay)
                
            return {
                "status": "ok",
                "trades": trades,
                "win_buyers": list(win_buyers),
                "win_sellers": list(win_sellers)
            }
            
        elif cmd == "COMMIT_MICROBLOCK":
            # Pack pending transactions and execute BFT consensus
            step = float(req.get("step"))
            last_microblock_hash = req.get("last_microblock_hash", "0" * 64)
            last_keyblock_hash = req.get("last_keyblock_hash", "0" * 64)
            
            if not self.pending_transactions:
                return {"status": "skipped", "message": "No pending transactions"}
                
            seed = f"{last_keyblock_hash}:{step}"
            leader, vrf_val, proof = self.consensus_engine.elect_leader(self.current_committee, seed)
            
            if not leader:
                return {"status": "failed", "message": "Leader election failed"}
                
            mb = Microblock(
                prev_hash=last_microblock_hash,
                keyblock_ref=last_keyblock_hash,
                transactions=self.pending_transactions.copy(),
                leader_id=leader
            )
            
            # Execute BFT Consensus Protocol
            success, msgs = self.consensus_engine.run_gosig_bft(mb, self.current_committee, leader)
            if success:
                self.microchain.append(mb)
                self.bft_msg_log += msgs
                
                # Log transaction latencies (delay is step - timestamp)
                for tx in mb.transactions:
                    self.latency_log.append(step - tx.timestamp)
                
                self.pending_transactions.clear()
                return {
                    "status": "success",
                    "hash": mb.hash,
                    "leader": leader,
                    "messages": msgs
                }
            else:
                return {"status": "failed", "message": "BFT Consensus failed"}
                
        elif cmd == "EPOCH_BOUNDARY":
            # Epoch reached: run Keyblock mining and update reputation values
            step = float(req.get("step"))
            last_microblock_hash = req.get("last_microblock_hash", "0" * 64)
            last_keyblock_hash = req.get("last_keyblock_hash", "0" * 64)
            
            # Calculate interactions feedback
            epoch_feedback = {}
            # Check last 10 microblocks
            start_idx = max(0, len(self.microchain) - 10)
            for mb in self.microchain[start_idx:]:
                for tx in mb.transactions:
                    if tx.tx_type == 'reputation':
                        target = tx.info['target']
                        fb = tx.info['feedback']
                        if target not in epoch_feedback:
                            epoch_feedback[target] = []
                        epoch_feedback[target].append(fb)
                        
            rep_changes = {}
            for target, feedbacks in epoch_feedback.items():
                for fb in feedbacks:
                    self.reputation_manager.add_interaction(target, fb)
                rep_changes[target] = self.reputation_manager.get_reputation(target)
                
            # Reward committee members for maintaining network
            for rsu_id in self.current_committee:
                self.reputation_manager.add_interaction(rsu_id, True)
                rep_changes[rsu_id] = self.reputation_manager.get_reputation(rsu_id)
                
            # Mine Keyblock
            miner = random.choice(self.current_committee)
            kb = Keyblock(
                prev_hash=last_keyblock_hash,
                prev_mb_hash=last_microblock_hash,
                rep_changes=rep_changes,
                miner_id=miner
            )
            kb.mine(difficulty=2)
            
            success, msgs = self.consensus_engine.run_gosig_bft(kb, self.current_committee, miner)
            if success:
                self.keychain.append(kb)
                self.bft_msg_log += msgs
                
                # Re-select BFT consensus committee
                rsu_ids = list(self.rsus.keys())
                self.current_committee = self.consensus_engine.select_committee(rsu_ids)
                
                # Monitor committee safety
                committee_reps = [self.reputation_manager.get_reputation(r) for r in self.current_committee]
                mal_reps = [
                    self.reputation_manager.get_reputation(r)
                    for r in self.current_committee if self.rsus[r]['is_malicious']
                ]
                comm_rep_sum = sum(committee_reps)
                mal_rep_sum = sum(mal_reps)
                mal_ratio = mal_rep_sum / comm_rep_sum if comm_rep_sum > 0 else 0
                
                self.committee_safety_log.append({
                    'step': step,
                    'committee_size': len(self.current_committee),
                    'total_reputation': comm_rep_sum,
                    'malicious_reputation': mal_rep_sum,
                    'malicious_ratio': mal_ratio
                })
                
                return {
                    "status": "success",
                    "hash": kb.hash,
                    "miner": miner,
                    "new_committee": self.current_committee,
                    "malicious_ratio": mal_ratio
                }
            else:
                return {"status": "failed", "message": "BFT Consensus failed for Keyblock"}
                
        elif cmd == "SAVE_LOGS":
            # Save final logs to disk
            self.save_metrics()
            return {"status": "ok", "message": "Simulation metrics successfully written."}
            
        return {"status": "error", "message": f"Unknown command '{cmd}'"}

    def save_metrics(self):
        avg_latency = sum(self.latency_log) / len(self.latency_log) if self.latency_log else 0.0
        max_latency = max(self.latency_log) if self.latency_log else 0.0
        
        normal_reps = [
            self.reputation_manager.get_reputation(v)
            for v, d in self.vehicles.items() if not d['is_malicious']
        ]
        mal_reps = [
            self.reputation_manager.get_reputation(v)
            for v, d in self.vehicles.items() if d['is_malicious']
        ]
        
        avg_normal = sum(normal_reps) / len(normal_reps) if normal_reps else 0.0
        avg_mal = sum(mal_reps) / len(mal_reps) if mal_reps else 0.0
        
        metrics = {
            'avg_latency': avg_latency,
            'max_latency': max_latency,
            'bft_msg_count': self.bft_msg_log,
            'committee_safety': self.committee_safety_log,
            'avg_normal_reputation': avg_normal,
            'avg_malicious_reputation': avg_mal,
            'blockchain_keyblocks': len(self.keychain),
            'blockchain_microblocks': len(self.microchain)
        }
        
        with open('data/simulation_log.json', 'w') as f:
            json.dump(metrics, f, indent=4)
            
        with open('data/simulation_log.js', 'w') as f:
            f.write(f"const simulationMetrics = {json.dumps(metrics, indent=4)};")
            
        print("[Python Server] Saved metrics logs to data/simulation_log.json and data/simulation_log.js")

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen()
        print(f"[Python Server] LBDT listening on {self.host}:{self.port}...")
        
        try:
            while True:
                conn, addr = server.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("[Python Server] Shutting down...")
        finally:
            server.close()

if __name__ == "__main__":
    server = LBDTSocketServer()
    server.start()
