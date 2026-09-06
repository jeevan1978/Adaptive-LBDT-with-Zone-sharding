import hashlib
import json
import numpy as np
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from src.blockchain.ledger import Transaction, Microblock, Keyblock

class ConsensusEngine:
    def __init__(self, reputation_manager):
        self.reputation_manager = reputation_manager
        # Node keys dictionary: {node_id: {'private_key': hex_str, 'public_key': hex_str}}
        self.node_keys = {}

    def register_node(self, node_id, private_key_hex, public_key_hex):
        self.node_keys[node_id] = {
            'private_key': private_key_hex,
            'public_key': public_key_hex
        }

    def select_committee(self, rsu_ids, target_ratio=0.67, max_size=11):
        """
        Selects committee members according to their reputation ranking
        until the cumulative reputation reaches target_ratio of overall reputation
        or committee size reaches max_size (to prevent excessive computation).
        """
        rsu_reps = {rsu_id: self.reputation_manager.get_reputation(rsu_id) for rsu_id in rsu_ids}
        sorted_rsus = sorted(rsu_reps.items(), key=lambda x: x[1], reverse=True)
        total_rep = sum(rsu_reps.values())
        
        committee = []
        current_rep = 0.0
        for rsu_id, rep in sorted_rsus:
            committee.append(rsu_id)
            current_rep += rep
            if len(committee) >= max_size:
                break
            if total_rep > 0 and (current_rep / total_rep) >= target_ratio:
                break
        return committee

    def generate_vrf(self, node_id, seed_str, mock=True):
        """
        Generates a Verifiable Random Value and proof (signature).
        """
        keys = self.node_keys.get(node_id)
        if not keys:
            raise ValueError(f"Keys for node {node_id} not registered.")
        
        if mock:
            # Fast pseudo-VRF
            proof = hashlib.sha256((keys['private_key'] + seed_str).encode('utf-8')).hexdigest()
            vrf_hash = hashlib.sha256(proof.encode('utf-8')).hexdigest()
            vrf_val = int(vrf_hash, 16)
            return vrf_val, proof
        else:
            sk = SigningKey.from_string(bytes.fromhex(keys['private_key']), curve=SECP256k1)
            proof = sk.sign(seed_str.encode('utf-8')).hex()
            vrf_hash = hashlib.sha256(proof.encode('utf-8')).hexdigest()
            vrf_val = int(vrf_hash, 16)
            return vrf_val, proof

    def verify_vrf(self, node_id, seed_str, vrf_val, proof_hex, mock=True):
        """
        Verifies the VRF random value and proof.
        """
        keys = self.node_keys.get(node_id)
        if not keys:
            return False
            
        if mock:
            expected_proof = hashlib.sha256((keys['private_key'] + seed_str).encode('utf-8')).hexdigest()
            if proof_hex != expected_proof:
                return False
            expected_hash = hashlib.sha256(proof_hex.encode('utf-8')).hexdigest()
            return vrf_val == int(expected_hash, 16)
        else:
            vk = VerifyingKey.from_string(bytes.fromhex(keys['public_key']), curve=SECP256k1)
            try:
                if not vk.verify(bytes.fromhex(proof_hex), seed_str.encode('utf-8')):
                    return False
                expected_hash = hashlib.sha256(proof_hex.encode('utf-8')).hexdigest()
                return vrf_val == int(expected_hash, 16)
            except Exception:
                return False

    def elect_leader(self, committee, seed_str, mock=True):
        """
        Elects the leader from the committee with the smallest VRF value.
        """
        if not committee:
            return None, None, None
            
        best_leader = None
        min_vrf = float('inf')
        best_proof = None
        
        for node_id in committee:
            try:
                vrf_val, proof = self.generate_vrf(node_id, seed_str, mock=mock)
                if vrf_val < min_vrf:
                    min_vrf = vrf_val
                    best_leader = node_id
                    best_proof = proof
            except ValueError:
                continue
        return best_leader, min_vrf, best_proof

    def run_gosig_bft(self, block, committee, leader_id, mock=True):
        """
        Simulates the Gosig BFT consensus protocol on a block.
        """
        total_comm_rep = sum([self.reputation_manager.get_reputation(node_id) for node_id in committee])
        if total_comm_rep == 0:
            return False, 0
            
        # Count communication messages (proposals, prepares, TCs, commits)
        msg_overhead = 0
        
        # 1. Proposal Phase: Leader broadcasts block proposal to all committee nodes (N - 1 messages)
        leader_keys = self.node_keys.get(leader_id)
        if not leader_keys:
            return False, 0
            
        if isinstance(block, Microblock):
            block.sign_leader(leader_keys['private_key'], mock=mock)
        elif isinstance(block, Keyblock):
            block.sign_miner(leader_keys['private_key'], mock=mock)
            
        msg_overhead += len(committee) - 1
        
        # 2. Prepare Phase: Committee nodes verify block and reply with prepare signatures
        prepare_votes_rep = 0.0
        prepare_nodes_count = 0
        for node_id in committee:
            if isinstance(block, Microblock):
                # Verify leader signature
                if mock:
                    block_hash = block.compute_hash()
                    expected_sig = hashlib.sha256((leader_keys['private_key'] + block_hash).encode()).hexdigest()
                    # If mock matches, simulate verification
                    if block.leader_sig != expected_sig:
                        continue
                else:
                    try:
                        vk = VerifyingKey.from_string(bytes.fromhex(leader_keys['public_key']), curve=SECP256k1)
                        block_hash = block.compute_hash()
                        if not vk.verify(bytes.fromhex(block.leader_sig), block_hash.encode('utf-8')):
                            continue
                    except Exception:
                        continue
            
            # Node signs prepare message and sends to leader
            node_keys = self.node_keys.get(node_id)
            if node_keys:
                block.add_validator_signature(node_id, node_keys['private_key'], mock=mock)
                prepare_votes_rep += self.reputation_manager.get_reputation(node_id)
                prepare_nodes_count += 1
                msg_overhead += 1
                
        # Check Legal Threshold for Prepare phase (cumulative reputation >= 2/3)
        if (prepare_votes_rep / total_comm_rep) < 0.66:
            return False, msg_overhead
            
        # 3. Tentative Commitment Phase: Leader broadcasts Cert_P(B) (N - 1 messages)
        msg_overhead += len(committee) - 1
        
        # Nodes verify Cert_P(B) and send TC(B) back
        tc_votes_rep = 0.0
        for node_id in committee:
            node_keys = self.node_keys.get(node_id)
            if node_keys:
                tc_votes_rep += self.reputation_manager.get_reputation(node_id)
                msg_overhead += 1
                
        # 4. Commit Phase: Leader checks threshold for TC(B) and broadcasts commit Cert_TC(B)
        if (tc_votes_rep / total_comm_rep) < 0.66:
            return False, msg_overhead
            
        msg_overhead += len(committee) - 1
        return True, msg_overhead
