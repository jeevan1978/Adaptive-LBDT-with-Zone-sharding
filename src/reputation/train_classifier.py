import os
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score, roc_curve, confusion_matrix

def generate_synthetic_telemetry(n_samples=10400, mal_ratio=0.2):
    """
    Generates synthetic node telemetry dataset matching SUMO/Veins entity distribution 
    if an empirical simulation dataset has not been exported yet.
    """
    np.random.seed(42)
    n_mal = int(n_samples * mal_ratio)
    n_honest = n_samples - n_mal
    
    # Honest nodes: high trades, zero packet drops, high BFT responses
    honest_trades = np.random.poisson(lam=15, size=n_honest)
    cheated_trades = np.random.binomial(n=1, p=0.005, size=n_honest)
    norm_drop_rate = np.random.exponential(scale=0.001, size=n_honest)
    bft_responses = np.random.poisson(lam=20, size=n_honest)
    y_honest = np.ones(n_honest, dtype=int)
    
    # Malicious nodes: lower honest trades or elevated cheated trades or elevated packet drop rate
    mal_honest_trades = np.random.poisson(lam=8, size=n_mal)
    mal_cheated_trades = np.random.poisson(lam=2, size=n_mal)
    mal_norm_drop_rate = np.random.uniform(low=0.15, high=0.80, size=n_mal)
    mal_bft_responses = np.random.poisson(lam=5, size=n_mal)
    y_mal = np.zeros(n_mal, dtype=int)
    
    X = np.column_stack([
        np.concatenate([honest_trades, mal_honest_trades]),
        np.concatenate([cheated_trades, mal_cheated_trades]),
        np.concatenate([norm_drop_rate, mal_norm_drop_rate]),
        np.concatenate([bft_responses, mal_bft_responses])
    ])
    y = np.concatenate([y_honest, y_mal])
    
    df = pd.DataFrame(X, columns=['honest_trades', 'cheated_trades', 'norm_drop_rate', 'bft_responses'])
    df['is_honest'] = y
    return df

def train_and_export_classifier(dataset_path="data/telemetry_dataset.csv", model_output_path="data/honesty_classifier.pkl"):
    print("=" * 60)
    print("   LBDT Logistic Regression Classifier Training Pipeline   ")
    print("=" * 60)
    
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    
    if os.path.exists(dataset_path):
        print(f"Loading empirical dataset from: {dataset_path}")
        df = pd.read_csv(dataset_path)
    else:
        print("Empirical dataset not found. Generating synthetic telemetry dataset for baseline initialization...")
        df = generate_synthetic_telemetry()
        df.to_csv(dataset_path, index=False)
        print(f"Saved synthetic dataset to {dataset_path}")

    feature_cols = ['honest_trades', 'cheated_trades', 'norm_drop_rate', 'bft_responses']
    X = df[feature_cols]
    y = df['is_honest']
    
    print(f"Dataset Shape: {X.shape} (Honest: {sum(y==1)}, Malicious: {sum(y==0)})")
    
    # Train / Test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    
    # Instantiate and fit scikit-learn Logistic Regression
    clf = LogisticRegression(max_iter=1000, random_state=42, solver='lbfgs')
    clf.fit(X_train, y_train)
    
    # Predictions & probabilities
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    
    # Evaluation Metrics
    auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)
    
    print("\n--- Classification Performance Report ---")
    print(classification_report(y_test, y_pred, target_names=['Malicious (0)', 'Honest (1)']))
    print(f"ROC-AUC Score: {auc:.4f}")
    print(f"Confusion Matrix:\n{cm}")
    
    print("\n--- Learned Statistical Model Parameters ---")
    print(f"Intercept (b): {clf.intercept_[0]:.4f}")
    for col, coef in zip(feature_cols, clf.coef_[0]):
        print(f"Weight w_{col}: {coef:.4f}")
        
    # Save trained model pipeline
    model_payload = {
        'classifier': clf,
        'feature_cols': feature_cols,
        'intercept': clf.intercept_[0],
        'coefficients': dict(zip(feature_cols, clf.coef_[0])),
        'auc_score': auc
    }
    joblib.dump(model_payload, model_output_path)
    print(f"\nTrained model successfully saved to: {model_output_path}")
    
    # Plot ROC Curve
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    plt.figure(figsize=(7, 5))
    plt.plot(fpr, tpr, color='#6366f1', lw=2, label=f'Logistic Regression (AUC = {auc:.3f})')
    plt.plot([0, 1], [0, 1], color='gray', linestyle='--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve - LBDT Node Honesty Classifier')
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)
    
    roc_plot_path = "data/roc_curve.png"
    plt.savefig(roc_plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved ROC Curve plot to: {roc_plot_path}")
    print("=" * 60)

if __name__ == "__main__":
    train_and_export_classifier()
