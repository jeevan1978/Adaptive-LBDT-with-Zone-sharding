import os
import numpy as np
import matplotlib.pyplot as plt
from src.reputation.model import ReputationManager

def run_reputation_comparison(n_steps=20, n_nodes=100, mal_ratio=0.2):
    print("=" * 70)
    print("  LBDT Baseline Comparative Evaluation Suite: Stealth Attack Scenario  ")
    print("=" * 70)
    
    modes = ['original', 'heuristic', 'ml']
    results = {}
    
    for mode in modes:
        print(f"\n[Evaluating Mode: {mode.upper()}]")
        rm = ReputationManager(mode=mode)
        
        honest_history = []
        malicious_history = []
        
        np.random.seed(42)
        node_ids = [f"node_{i}" for i in range(n_nodes)]
        mal_nodes = set(node_ids[:int(n_nodes * mal_ratio)])
        
        for step in range(n_steps):
            for node_id in node_ids:
                is_mal = node_id in mal_nodes
                
                if not is_mal:
                    # Honest node: 95% positive trades, 0 packet drops
                    is_pos = (np.random.random() < 0.95)
                    rm.update_features(node_id, 'packet_drops', 0)
                else:
                    # Stealth Malicious Node: 90% POSITIVE TRADES (disguised as honest trader),
                    # BUT drops 40% of routing packets in network layer!
                    is_pos = (np.random.random() < 0.90) 
                    rm.update_features(node_id, 'packet_drops', np.random.randint(4, 8)) # Stealth packet drop attack
                    
                rm.add_interaction(node_id, is_pos, n_peers=n_nodes)
                
            h_reps = [rm.get_reputation(n) for n in node_ids if n not in mal_nodes]
            m_reps = [rm.get_reputation(n) for n in node_ids if n in mal_nodes]
            
            honest_history.append(np.mean(h_reps))
            malicious_history.append(np.mean(m_reps))
            
        avg_h = honest_history[-1]
        avg_m = malicious_history[-1]
        rep_gap = avg_h - avg_m
        
        results[mode] = {
            'honest': honest_history,
            'malicious': malicious_history,
            'final_honest': avg_h,
            'final_malicious': avg_m,
            'reputation_gap': rep_gap
        }
        
        print(f"  -> Final Honest Node Rep: {avg_h:.4f}")
        print(f"  -> Final Stealth Malicious Node Rep: {avg_m:.4f}")
        print(f"  -> Honest-Malicious Separation Gap: {rep_gap:.4f}")
        
    # Plot Comparative Graph
    plt.figure(figsize=(10, 6))
    steps_arr = np.arange(1, n_steps + 1)
    
    colors = {'original': '#ef4444', 'heuristic': '#f59e0b', 'ml': '#10b981'}
    labels = {'original': 'Original LBDT (Fixed Gompertz)', 'heuristic': 'Heuristic Sigmoid', 'ml': 'Proposed ML (Logistic Regression)'}
    
    for mode in modes:
        plt.plot(steps_arr, results[mode]['honest'], color=colors[mode], linestyle='-', linewidth=2.5, label=f"{labels[mode]} - Honest")
        plt.plot(steps_arr, results[mode]['malicious'], color=colors[mode], linestyle='--', linewidth=2.5, label=f"{labels[mode]} - Stealth Attacker")
        
    plt.title('Stealth Attack Resilience: ML vs. Original LBDT Paper', fontsize=13, fontweight='bold')
    plt.xlabel('Interaction Epoch / Steps', fontsize=12)
    plt.ylabel('Gompertz Reputation Score (Rep)', fontsize=12)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=10)
    plt.grid(True, linestyle=':', alpha=0.6)
    
    os.makedirs('data', exist_ok=True)
    comp_plot_path = 'data/model_comparison.png'
    plt.savefig(comp_plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print("\n" + "=" * 70)
    print("  EMPIRICAL STEALTH ATTACK COMPARISON SUMMARY  ")
    print("=" * 70)
    print(f"{'Model Variant':<35} | {'Honest Rep':<10} | {'Stealth Mal Rep':<15} | {'Separation Gap':<14}")
    print("-" * 81)
    for mode in modes:
        m_name = labels[mode]
        print(f"{m_name:<35} | {results[mode]['final_honest']:<10.4f} | {results[mode]['final_malicious']:<15.4f} | {results[mode]['reputation_gap']:<14.4f}")
    print("=" * 70)
    print(f"Comparative graph exported to: {comp_plot_path}")

if __name__ == "__main__":
    run_reputation_comparison()
