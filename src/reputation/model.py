import os
import numpy as np
import joblib

class ReputationManager:
    def __init__(self, a=1.0, b=0.7, c=0.5, gamma=0.95, delta_pos=0.1, delta_neg=-2.0, mode='ml', model_path="data/honesty_classifier.pkl"):
        # Parameters for Gompertz function
        self.a = a  # Asymptote (maximum reputation)
        self.b = b  # Displacement (controls initial reputation)
        self.c = c  # Growth rate
        self.gamma = gamma  # Aging/decay factor
        self.delta_pos = delta_pos  # Positive interaction score
        self.delta_neg = delta_neg  # Negative interaction score
        self.mode = mode  # 'ml', 'heuristic', or 'original'
        
        # In-memory database of interaction histories and current reputations
        self.histories = {}
        self.reputations = {}
        
        # Behavioral features for Logistic Regression: node_id -> dict of features
        self.features = {}
        
        # Load trained scikit-learn machine learning model if available
        self.ml_model = None
        if self.mode == 'ml' and os.path.exists(model_path):
            try:
                payload = joblib.load(model_path)
                self.ml_model = payload['classifier']
                print(f"[ReputationManager] Successfully loaded trained ML classifier from {model_path} (AUC: {payload.get('auc_score', 0):.4f})")
            except Exception as e:
                print(f"[ReputationManager] Warning: Failed to load ML model ({e}). Falling back to heuristic mode.")

    def update_features(self, node_id, feature_name, value=1):
        if node_id not in self.features:
            self.features[node_id] = {
                'honest_trades': 0,
                'cheated_trades': 0,
                'packet_drops': 0,
                'bft_responses': 0,
                'active_steps': 0
            }
        if feature_name in self.features[node_id]:
            self.features[node_id][feature_name] += value

    def get_honesty_probability(self, node_id, average_zone_packet_drops=0.0):
        # 1. Mode: Original Paper (Fixed parameters, no ML or heuristic penalty)
        if self.mode == 'original':
            return 1.0
            
        if node_id not in self.features:
            return 1.0
            
        feat = self.features[node_id]
        
        # Cold start / Clean history
        if feat['packet_drops'] == 0 and feat['cheated_trades'] == 0:
            return 1.0
            
        # Rates
        if feat['active_steps'] == 0:
            return 1.0
            
        drop_rate = feat['packet_drops'] / feat['active_steps']
        
        # Normalize relative to zone average
        if average_zone_packet_drops > 0.05:
            norm_drop_rate = drop_rate / (average_zone_packet_drops * 10.0)
        else:
            norm_drop_rate = drop_rate
            
        # 2. Mode: Statistically Trained ML Model Inference
        if self.mode == 'ml' and self.ml_model is not None:
            import pandas as pd
            X_df = pd.DataFrame([[
                feat['honest_trades'],
                feat['cheated_trades'],
                norm_drop_rate,
                feat['bft_responses']
            ]], columns=['honest_trades', 'cheated_trades', 'norm_drop_rate', 'bft_responses'])
            p_honest = float(self.ml_model.predict_proba(X_df)[0][1])
            return p_honest

        # 3. Mode: Heuristic Sigmoid Computation
        z = (2.0 
             + 0.5 * feat['honest_trades'] 
             - 8.0 * feat['cheated_trades'] 
             - 15.0 * norm_drop_rate 
             + 0.1 * feat['bft_responses'])
             
        p_honest = 1.0 / (1.0 + np.exp(-np.clip(z, -20.0, 20.0)))
        return p_honest

    def get_reputation(self, node_id):
        if node_id not in self.reputations:
            self.update_features(node_id, 'active_steps', 1)
            self.update_features(node_id, 'honest_trades', 0)
            p_honest = self.get_honesty_probability(node_id)
            self.reputations[node_id] = self.calculate_reputation(0.0, p_honest)
            self.histories[node_id] = []
        return self.reputations[node_id]

    def add_interaction(self, node_id, is_positive, n_peers=10000):
        if node_id not in self.histories:
            self.histories[node_id] = []
            
        score = self.delta_pos if is_positive else self.delta_neg
        self.histories[node_id].append(score)
        
        # Calculate aged score: r_n = (sum_{i=1}^n gamma^{n-i} * delta_i) * ln(N_peers)
        history = self.histories[node_id]
        n = len(history)
        
        aged_sum = 0.0
        for i in range(n):
            aged_sum += (self.gamma ** (n - 1 - i)) * history[i]
            
        # Log factor based on number of peers
        ln_peers = np.log(max(2, n_peers))
        r_n = aged_sum * ln_peers
        
        # Update features
        self.update_features(node_id, 'active_steps', 1)
        if is_positive:
            self.update_features(node_id, 'honest_trades', 1)
            self.update_features(node_id, 'bft_responses', 1)
        else:
            self.update_features(node_id, 'cheated_trades', 1)
            
        # Compute adaptive reputation
        p_honest = self.get_honesty_probability(node_id)
        rep = self.calculate_reputation(r_n, p_honest)
        self.reputations[node_id] = rep
        return rep

    def calculate_reputation(self, interaction_score, p_honest=1.0):
        # Adaptive Ceiling (a): drops if suspicious
        a_adapt = self.a * p_honest
        # Adaptive Displacement (b): higher b delays recovery for suspicious nodes
        b_adapt = self.b + 3.0 * (1.0 - p_honest)
        
        score = np.clip(interaction_score, -50.0, 50.0)
        reputation = a_adapt * np.exp(-b_adapt * np.exp(-self.c * score))
        return reputation

    def calculate_loss(self, delta_t, delta_rep, alpha_1=0.5, alpha_2=0.5, beta_1=1, beta_2=1):
        loss = alpha_1 * (delta_t ** beta_1) + alpha_2 * (delta_rep ** beta_2)
        return loss

# Test the model
if __name__ == "__main__":
    rm = ReputationManager()
    print(f"Initial Reputation (r_n=0): {rm.get_reputation('node1'):.4f}")
    
    # 5 honest interactions
    for _ in range(5):
        rm.add_interaction('node1', True)
    print(f"Reputation after 5 honest interactions: {rm.get_reputation('node1'):.4f}")
    
    # 1 malicious interaction
    rm.add_interaction('node1', False)
    print(f"Reputation after 1 malicious interaction: {rm.get_reputation('node1'):.4f}")