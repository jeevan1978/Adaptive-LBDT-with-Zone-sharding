import hashlib
import json
import time
from ecdsa import SigningKey, VerifyingKey, SECP256k1

class Transaction:
    def __init__(self, tx_type, timestamp, info, signature=None):
        self.tx_type = tx_type
        self.timestamp = timestamp
        self.info = info
        self.signature = signature

    def to_dict(self):
        return {
            'tx_type': self.tx_type,
            'timestamp': self.timestamp,
            'info': self.info,
            'signature': self.signature
        }

    def compute_hash(self):
        info_str = json.dumps(self.info, sort_keys=True)
        data_str = f"{self.tx_type}:{self.timestamp}:{info_str}"
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    def sign(self, private_key_hex, mock=True):
        tx_hash = self.compute_hash()
        if mock:
            # Fast pseudo-signature for simulation speed
            self.signature = hashlib.sha256((private_key_hex + tx_hash).encode()).hexdigest()
        else:
            sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
            self.signature = sk.sign(tx_hash.encode('utf-8')).hex()

    def verify(self, public_key_hex, mock=True):
        if not self.signature:
            return False
        tx_hash = self.compute_hash()
        if mock:
            expected = hashlib.sha256((public_key_hex + tx_hash).encode()).hexdigest()
            return self.signature == expected
        else:
            try:
                vk = VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=SECP256k1)
                return vk.verify(bytes.fromhex(self.signature), tx_hash.encode('utf-8'))
            except Exception:
                return False

class Microblock:
    def __init__(self, prev_hash, keyblock_ref, transactions, leader_id, leader_sig=None, collective_sig=None):
        self.prev_hash = prev_hash
        self.keyblock_ref = keyblock_ref
        self.transactions = transactions
        self.leader_id = leader_id
        self.leader_sig = leader_sig
        self.collective_sig = collective_sig if collective_sig is not None else {}
        self.hash = self.compute_hash()

    def compute_hash(self):
        tx_hashes = [tx.compute_hash() for tx in self.transactions]
        data = {
            'prev_hash': self.prev_hash,
            'keyblock_ref': self.keyblock_ref,
            'tx_hashes': tx_hashes,
            'leader_id': self.leader_id
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    def sign_leader(self, private_key_hex, mock=True):
        block_hash = self.compute_hash()
        if mock:
            self.leader_sig = hashlib.sha256((private_key_hex + block_hash).encode()).hexdigest()
        else:
            sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
            self.leader_sig = sk.sign(block_hash.encode('utf-8')).hex()

    def add_validator_signature(self, validator_id, private_key_hex, mock=True):
        block_hash = self.compute_hash()
        if mock:
            self.collective_sig[validator_id] = hashlib.sha256((private_key_hex + block_hash).encode()).hexdigest()
        else:
            sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
            self.collective_sig[validator_id] = sk.sign(block_hash.encode('utf-8')).hex()

class Keyblock:
    def __init__(self, prev_hash, prev_mb_hash, rep_changes, miner_id, nonce=0, miner_sig=None, collective_sig=None):
        self.prev_hash = prev_hash
        self.prev_mb_hash = prev_mb_hash
        self.rep_changes = rep_changes
        self.miner_id = miner_id
        self.nonce = nonce
        self.collective_sig = collective_sig if collective_sig is not None else {}
        self.hash = self.compute_hash()

    def compute_hash(self):
        data = {
            'prev_hash': self.prev_hash,
            'prev_mb_hash': self.prev_mb_hash,
            'rep_changes': self.rep_changes,
            'miner_id': self.miner_id,
            'nonce': self.nonce
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    def mine(self, difficulty=2):
        target = '0' * difficulty
        self.hash = self.compute_hash()
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()
        return self.hash

    def sign_miner(self, private_key_hex, mock=True):
        block_hash = self.compute_hash()
        if mock:
            self.miner_sig = hashlib.sha256((private_key_hex + block_hash).encode()).hexdigest()
        else:
            sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
            self.miner_sig = sk.sign(block_hash.encode('utf-8')).hex()

    def add_validator_signature(self, validator_id, private_key_hex, mock=True):
        block_hash = self.compute_hash()
        if mock:
            self.collective_sig[validator_id] = hashlib.sha256((private_key_hex + block_hash).encode()).hexdigest()
        else:
            sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
            self.collective_sig[validator_id] = sk.sign(block_hash.encode('utf-8')).hex()
