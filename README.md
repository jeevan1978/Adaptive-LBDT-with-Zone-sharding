# LBDT: A Lightweight Blockchain-Based Data Trading Scheme in Internet of Vehicles

This repository implements the lightweight blockchain-based data trading scheme (LBDT) for Internet of Vehicles (IoV) networks, using a parallel-chain structure and a Proof-of-Reputation (PoR) consensus mechanism, based on the research paper: *LBDT: A Lightweight Blockchain-Based Data Trading Scheme in Internet of Vehicles Using Proof-of-Reputation* (IEEE Transactions on Mobile Computing, 2025).

---

## Architecture Overview

LBDT decouples block generation and consensus into two parallel chains to optimize performance for resource-constrained vehicles:
1. **Keychain (Keyblocks):** Mined by Road Side Units (RSUs) via PoW every epoch (60 seconds) to record node reputation changes and trigger leader elections.
2. **Microchain (Microblocks):** Serialized by the BFT leader (elected from a committee using VRF) every round (6 seconds) to store transaction data.

### Mathematical Formulation
* **Aged Reputation Score ($r_n$):**
  $$r_n = \left(\sum_{i=1}^{n}\gamma^{n-i}\delta_{i}\right) \ln(N_{peers})$$
  Where $\gamma \in (0, 1)$ is the decay parameter (default 0.95), $\delta_i$ is the interaction evaluation ($\delta_{pos}=0.1$ for honest behavior, $\delta_{neg}=-2.0$ for malicious behavior), and $N_{peers}$ is the number of active nodes.
  
* **Gompertz Growth Function ($Rep_i$):**
  $$Rep_i(r_n) = a \times e^{-b \times e^{-c \times r_n}}$$
  Where $a=1.0$ (asymptote), $b=0.7$ (displacement yielding starting reputation $\approx 0.5$ at $r_n=0$), and $c=0.5$ (growth rate).
  
* **Bid Price Adjustment Loss Function ($loss$):**
  $$loss(t_i^k, Rep_i) = \alpha_1 \times (t_{now} - t_i^k)^{\beta_1} + \alpha_2 \times (1 - Rep_i)^{\beta_2}$$
  Where $\alpha_1=0.5, \alpha_2=0.5, \beta_1=1.0, \beta_2=1.0$. Seller's asking price is adjusted as: $SP'_i = SP_i + loss$.

---

## Directory Structure

* `src/reputation/model.py`: Gompertz reputation management and aging computations.
* `src/auction/auction.py`: Double Auction matching engine (Algorithm 1).
* `src/blockchain/ledger.py`: Data structure of parallel chains (Keyblocks and Microblocks).
* `src/blockchain/consensus.py`: Committee selection, EC-VRF leader election, and Gosig BFT consensus.
* `src/simulation/runner.py`: TraCI simulation runner integrating python engines with SUMO.
* `data/`: SUMO configuration, road network xml, and vehicle route files.
* `tests/`: Unit tests for reputation and auction modules.

---

## Getting Started

### Prerequisites
1. **Python 3.10+**
2. **Eclipse SUMO** installed and added to the path.
3. **Environment Variable `SUMO_HOME`** set to the SUMO installation folder (e.g. `C:\Program Files (x86)\Eclipse\Sumo\`).
4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running Unit Tests
Validate the Reputation and Auction engine mathematically:
```bash
python -m unittest tests/test_lbdt.py
```

### Running the SUMO Simulation
Execute the LBDT simulation coordinating double auctions, blockchain ledger blocks, and consensus:
```bash
python -m src.simulation.runner
```

---

## Empirical Validation Results

Running the validation simulation for **180 steps** on the **10 km x 10 km grid map** with **1,000 vehicles** and **400 RSUs** yielded the following metrics:

| Metric | Empirical Value |
| :--- | :--- |
| **Keyblocks Mined** | 2 blocks (60s epoch) |
| **Microblocks Committed** | 25 blocks (6s round) |
| **Average Transaction Confirmation Latency** | **2.4828 seconds** |
| **Total BFT Messages Exchanged** | 1,404 messages |
| **Average Honest Node Reputation** | **0.5135** (reputation increased) |
| **Average Malicious Node Reputation** | **0.4644** (reputation decayed) |
| **Committee Safety Verified** | **True** (Malicious reputation in committee $< 1/3$) |

*The results verify that LBDT successfully isolates malicious nodes by declining their reputations, preventing them from dominating the BFT consensus committee, and confirms transactions in under 3 seconds.*
