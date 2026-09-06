import os
import numpy as np
import matplotlib.pyplot as plt

# Ensure output directory exists
os.makedirs("data/plots", exist_ok=True)

# Set global matplotlib parameters for clean, premium styling
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Inter', 'Outfit', 'Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#EAEAEA'
plt.rcParams['grid.linewidth'] = 0.6
plt.rcParams['xtick.color'] = '#555555'
plt.rcParams['ytick.color'] = '#555555'
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 8
plt.rcParams['legend.frameon'] = True
plt.rcParams['legend.facecolor'] = '#FFFFFF'
plt.rcParams['legend.edgecolor'] = '#EEEEEE'

# Colors to match the paper
COLORS = {
    'LBDT': '#0f82ff',       # Blue
    'MWSL': '#ef4444',       # Red
    'TI-BIoV': '#10b981',    # Green
    'PoW': '#333333'         # Black/Dark Gray
}

def plot_fig8_reputation():
    """
    Figure 8. Reputation in both normal and malicious scenarios (single plot).
    """
    timeslots = np.arange(0, 25)
    
    # Normal Nodes
    mwsl_normal = np.array([0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    lbdt_normal = np.array([0.5, 0.63, 0.75, 0.82, 0.87, 0.9, 0.92, 0.93, 0.94, 0.94, 0.94, 0.94, 0.94, 0.94, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.96, 0.96, 0.96])
    tibiov_normal = np.array([0.5, 0.71, 0.76, 0.79, 0.81, 0.82, 0.82, 0.83, 0.83, 0.84, 0.84, 0.84, 0.85, 0.85, 0.85, 0.86, 0.86, 0.86, 0.86, 0.86, 0.86, 0.87, 0.87, 0.87, 0.87])
    
    # Malicious Nodes
    mwsl_malicious = np.array([0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.85, 0.51, 0.46, 0.51, 0.6, 0.66, 0.7, 0.76, 0.52, 0.5, 0.47, 0.58, 0.63, 0.67, 0.72, 0.77, 0.53, 0.51, 0.51])
    lbdt_malicious = np.array([0.5, 0.63, 0.75, 0.82, 0.02, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.11, 0.29, 0.47, 0.68, 0.74, 0.78, 0.02, 0.0])
    tibiov_malicious = np.array([0.5, 0.71, 0.76, 0.79, 0.81, 0.82, 0.2, 0.28, 0.35, 0.4, 0.44, 0.47, 0.5, 0.52, 0.54, 0.56, 0.58, 0.6, 0.61, 0.62, 0.63, 0.64, 0.64, -0.25, -0.23])
    
    plt.figure(figsize=(7, 5))
    
    # Plotting
    plt.plot(timeslots, mwsl_normal, label='Normal Node in MWSL Scheme', color=COLORS['MWSL'], marker='s', markersize=5, linewidth=1.2)
    plt.plot(timeslots, mwsl_malicious, label='Malicious Node in MWSL Scheme', color=COLORS['MWSL'], marker='x', markersize=5, linewidth=1.2)
    plt.plot(timeslots, lbdt_normal, label='Normal Node in LBDT', color=COLORS['LBDT'], marker='v', markersize=5, linewidth=1.2)
    plt.plot(timeslots, lbdt_malicious, label='Malicious Node in LBDT', color=COLORS['LBDT'], marker='v', markerfacecolor='none', markeredgecolor=COLORS['LBDT'], markersize=5, linewidth=1.2)
    plt.plot(timeslots, tibiov_normal, label='Normal Node in TI-BIoV', color=COLORS['TI-BIoV'], marker='o', markersize=5, linewidth=1.2)
    plt.plot(timeslots, tibiov_malicious, label='Malicious Node in TI-BIoV', color=COLORS['TI-BIoV'], marker='o', markerfacecolor='none', markeredgecolor=COLORS['TI-BIoV'], markersize=5, linewidth=1.2)
    
    plt.xlabel("Timeslot", fontsize=10)
    plt.ylabel("Reputation Value", fontsize=10)
    
    plt.xlim(-2, 27)
    plt.xticks(np.arange(0, 26, 10))
    plt.ylim(-0.3, 1.3)
    plt.yticks(np.arange(-0.2, 1.21, 0.2))
    plt.grid(True, linestyle='--')
    plt.legend(loc='upper left', fontsize=8)
    plt.tight_layout()
    plt.savefig("data/plots/fig_8_reputation.png", dpi=300)
    plt.close()
    print("Saved fig_8_reputation.png")

def plot_fig9_attacks():
    """
    Figure 9. Number of successful attacks launched by different adversaries (broken Y-axis).
    """
    adv_power = np.array([20, 25, 30, 35, 40, 45, 50, 55, 60, 65])
    
    # For pow_1k, use duplicate x=50 to create a vertical step jump aligning the broken axis
    pow_x = np.array([20, 25, 30, 35, 40, 45, 50, 50, 55, 60, 65])
    pow_1k = np.array([0, 0, 0, 0, 0, 0, 0, 4320, 4320, 4320, 4320])
    
    # 1,000 vehicles data
    mwsl_1k = np.array([0, 0, 0, 350, 380, 380, 390, 400, 410, 410])
    tibiov_1k = np.array([100, 130, 170, 400, 410, 410, 420, 430, 440, 440])
    lbdt_1k = np.array([0, 0, 0, 100, 120, 120, 130, 140, 140, 140])
    
    # 10,000 vehicles data
    pow_10k = np.array([4320, 4320, 4320, 4320, 4320, 4320, 4320, 4320, 4320, 4320])
    mwsl_10k = np.array([0, 0, 0, 370, 390, 390, 400, 410, 420, 420])
    tibiov_10k = np.array([110, 140, 180, 410, 420, 420, 430, 440, 450, 450])
    lbdt_10k = np.array([0, 0, 0, 110, 130, 130, 140, 150, 150, 150])
    
    # Create subplots for broken axis
    fig, (ax_top, ax_bottom) = plt.subplots(2, 1, sharex=True, figsize=(7, 5.5), gridspec_kw={'height_ratios': [1, 2.5]})
    fig.subplots_adjust(hspace=0.08)
    
    # Plot same lines on both axes
    for ax in [ax_top, ax_bottom]:
        # 1k vehicles (square markers, hollow)
        ax.plot(pow_x, pow_1k, label="1,000 vehicles, Chen's scheme based on PoW", color=COLORS['PoW'], marker='s', markerfacecolor='none', markeredgecolor=COLORS['PoW'], linewidth=1.2, markersize=5)
        ax.plot(adv_power, mwsl_1k, label="1,000 vehicles, MWSL", color=COLORS['MWSL'], marker='s', markerfacecolor='none', markeredgecolor=COLORS['MWSL'], linewidth=1.2, markersize=5)
        ax.plot(adv_power, tibiov_1k, label="1,000 vehicles, TI-BIoV", color=COLORS['TI-BIoV'], marker='s', markerfacecolor='none', markeredgecolor=COLORS['TI-BIoV'], linewidth=1.2, markersize=5)
        ax.plot(adv_power, lbdt_1k, label="1,000 vehicles, LBDT", color=COLORS['LBDT'], marker='s', markerfacecolor='none', markeredgecolor=COLORS['LBDT'], linewidth=1.2, markersize=5)
        
        # 10k vehicles (down-triangle markers, hollow)
        ax.plot(adv_power, pow_10k, label="10,000 vehicles, Chen's scheme based on PoW", color=COLORS['PoW'], marker='v', markerfacecolor='none', markeredgecolor=COLORS['PoW'], linewidth=1.2, markersize=5)
        ax.plot(adv_power, mwsl_10k, label="10,000 vehicles, MWSL", color=COLORS['MWSL'], marker='v', markerfacecolor='none', markeredgecolor=COLORS['MWSL'], linewidth=1.2, markersize=5)
        ax.plot(adv_power, tibiov_10k, label="10,000 vehicles, TI-BIoV", color=COLORS['TI-BIoV'], marker='v', markerfacecolor='none', markeredgecolor=COLORS['TI-BIoV'], linewidth=1.2, markersize=5)
        ax.plot(adv_power, lbdt_10k, label="10,000 vehicles, LBDT", color=COLORS['LBDT'], marker='v', markerfacecolor='none', markeredgecolor=COLORS['LBDT'], linewidth=1.2, markersize=5)

    # Zoom-in limits
    ax_top.set_ylim(3900, 5100)
    ax_bottom.set_ylim(-15, 450)
    
    # Hide the spines between top and bottom
    ax_top.spines['bottom'].set_visible(False)
    ax_bottom.spines['top'].set_visible(False)
    ax_top.xaxis.tick_top()
    ax_top.tick_params(labeltop=False)  # don't put tick labels at the top
    ax_bottom.xaxis.tick_bottom()
    
    # Add grid lines
    ax_top.grid(True, linestyle='--')
    ax_bottom.grid(True, linestyle='--')
    
    # Draw broken axis cut-out lines (making the vertical axis offset larger to look like steep 45-degree cuts)
    d = .015  # size of diagonal cut lines
    kwargs = dict(transform=ax_top.transAxes, color='black', clip_on=False, linewidth=0.8)
    ax_top.plot((-d, +d), (-2 * d, +2 * d), **kwargs)        # top-left diagonal
    ax_top.plot((1 - d, 1 + d), (-2 * d, +2 * d), **kwargs)  # top-right diagonal
    
    kwargs.update(transform=ax_bottom.transAxes)  # switch to bottom axes
    ax_bottom.plot((-d, +d), (1 - 2 * d, 1 + 2 * d), **kwargs)  # bottom-left diagonal
    ax_bottom.plot((1 - d, 1 + d), (1 - 2 * d, 1 + 2 * d), **kwargs) # bottom-right diagonal

    # Set labels
    ax_bottom.set_xlabel("Adversary computing power (%)", fontsize=10)
    fig.supylabel("Number of successful malicious attacks", fontsize=10)
    
    plt.xlim(15, 70)
    plt.xticks(np.arange(15, 71, 5))
    
    # Place legend on top axes, since there's blank space (offset further to the right to prevent overlap)
    ax_top.legend(loc='upper left', bbox_to_anchor=(0.20, 0.98), ncol=1, framealpha=0.9, fontsize=7)
    
    # Adjust layout to fit supylabel, then apply the hspace constraint
    fig.tight_layout()
    fig.subplots_adjust(hspace=0.08)
    
    plt.savefig("data/plots/fig_9_attacks.png", dpi=300)
    plt.close()
    print("Saved fig_9_attacks.png")

def plot_fig10_latency_blocksize():
    """
    Figure 10. Relationship between the transaction latency and the block size.
    """
    block_sizes = np.array([0.25, 0.5, 1, 2, 4, 8, 16, 32])
    
    pow_latency = np.ones(len(block_sizes)) * 3600
    lbdt_latency = np.array([0.45, 0.46, 0.48, 0.52, 0.62, 0.85, 1.3, 2.5])
    mwsl_latency = np.array([10, 19, 35, 72, 170, 320, 600, 1200])
    tibiov_latency = np.array([68, 100, 180, 320, 600, 1000, 1800, 3100])
    
    plt.figure(figsize=(6, 4.5))
    plt.plot(block_sizes, pow_latency, label="Chen's scheme based on PoW", color=COLORS['PoW'], linewidth=1.5, marker='s', markersize=5)
    plt.plot(block_sizes, lbdt_latency, label='LBDT', color=COLORS['LBDT'], linewidth=1.5, marker='v', markersize=5)
    plt.plot(block_sizes, mwsl_latency, label='MWSL', color=COLORS['MWSL'], linewidth=1.5, marker='o', markersize=5)
    plt.plot(block_sizes, tibiov_latency, label='TI-BIoV', color=COLORS['TI-BIoV'], linewidth=1.5, marker='o', markerfacecolor='none', markeredgecolor=COLORS['TI-BIoV'], markersize=5)
    
    plt.xlabel("Block size (MB)", fontsize=10)
    plt.ylabel("Transaction latency (s)", fontsize=10)
    
    plt.xlim(0.15, 45)
    plt.xscale('log', base=2)
    plt.xticks(block_sizes, [str(b) for b in block_sizes])
    plt.ylim(0.2, 10000)
    plt.yscale('log')
    plt.grid(True, which="both", linestyle='--')
    plt.legend(loc='center right', fontsize=8)
    plt.tight_layout()
    plt.savefig("data/plots/fig_10_latency_blocksize.png", dpi=300)
    plt.close()
    print("Saved fig_10_latency_blocksize.png")

def plot_fig11_latency_rsus():
    """
    Figure 11. Relationship between the transaction latency and the number of RSUs.
    """
    rsus = np.array([100, 500, 1000, 2000, 3000, 6500, 13000])
    
    pow_latency = np.ones(len(rsus)) * 3000
    lbdt_latency = np.array([0.5, 0.6, 0.7, 0.9, 1.0, 1.7, 4.5])
    mwsl_latency = np.array([40, 70, 85, 150, 250, 550, 1200])
    tibiov_latency = np.array([160, 350, 1100, 3000, 12000, 42000, 42000])
    
    plt.figure(figsize=(6, 4.5))
    plt.plot(rsus, pow_latency, label="Chen's scheme based on PoW", color=COLORS['PoW'], linewidth=1.5, marker='s', markersize=5)
    plt.plot(rsus, lbdt_latency, label='LBDT', color=COLORS['LBDT'], linewidth=1.5, marker='v', markersize=5)
    plt.plot(rsus, mwsl_latency, label='MWSL', color=COLORS['MWSL'], linewidth=1.5, marker='o', markersize=5)
    plt.plot(rsus, tibiov_latency, label='TI-BIoV', color=COLORS['TI-BIoV'], linewidth=1.5, marker='o', markerfacecolor='none', markeredgecolor=COLORS['TI-BIoV'], markersize=5)
    
    plt.xlabel("Number of RSUs", fontsize=10)
    plt.ylabel("Transaction latency (s)", fontsize=10)
    
    plt.xlim(-500, 14000)
    plt.xticks(np.arange(0, 14001, 2000))
    plt.ylim(0.3, 100000)
    plt.yscale('log')
    plt.grid(True, which="both", linestyle='--')
    plt.legend(loc='lower right', bbox_to_anchor=(0.98, 0.38), fontsize=8)
    plt.tight_layout()
    plt.savefig("data/plots/fig_11_latency_rsus.png", dpi=300)
    plt.close()
    print("Saved fig_11_latency_rsus.png")

def plot_fig12_communication():
    """
    Figure 12. Relationship between the communication overhead and the number of vehicles.
    """
    vehicles = np.array([10000, 20000, 50000, 100000, 200000, 400000, 600000, 1000000])
    
    pow_overhead = np.array([2, 4, 8, 12, 18, 25, 30, 40])
    tibiov_overhead = np.array([10, 12, 15, 25, 32, 45, 55, 65])
    lbdt_overhead = np.array([5, 8, 18, 40, 75, 130, 190, 310])
    mwsl_overhead = np.array([60, 100, 170, 450, 700, 1350, 2750, 5500])
    
    plt.figure(figsize=(6, 4.5))
    plt.plot(vehicles, pow_overhead, label="Chen's scheme based on PoW", color=COLORS['PoW'], linewidth=1.5, marker='s', markersize=5)
    plt.plot(vehicles, lbdt_overhead, label='LBDT', color=COLORS['LBDT'], linewidth=1.5, marker='v', markersize=5)
    plt.plot(vehicles, mwsl_overhead, label='MWSL', color=COLORS['MWSL'], linewidth=1.5, marker='o', markersize=5)
    plt.plot(vehicles, tibiov_overhead, label='TI-BIoV', color=COLORS['TI-BIoV'], linewidth=1.5, marker='o', markerfacecolor='none', markeredgecolor=COLORS['TI-BIoV'], markersize=5)
    
    plt.xlabel("Number of vehicles", fontsize=10)
    plt.ylabel("Communication cost of Vehicles (KB/s)", fontsize=10)
    
    plt.xlim(8000, 1200000)
    plt.xscale('log')
    plt.ylim(-200, 6000)
    plt.grid(True, which="both", linestyle='--')
    plt.legend(loc='upper left', fontsize=8)
    plt.tight_layout()
    plt.savefig("data/plots/fig_12_communication.png", dpi=300)
    plt.close()
    print("Saved fig_12_communication.png")

def plot_fig13_storage():
    """
    Figure 13. Relationship between the storage overhead and the simulation time.
    """
    sim_time = np.array([0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000])
    
    pow_storage = sim_time * 2.5
    mwsl_storage = sim_time * 2.53
    lbdt_storage = sim_time * 0.1
    tibiov_storage = sim_time * 0.025
    
    plt.figure(figsize=(6, 4.5))
    plt.plot(sim_time, pow_storage, label="Chen's scheme based on PoW", color=COLORS['PoW'], linewidth=1.5, marker='s', markersize=5)
    plt.plot(sim_time, mwsl_storage, label='MWSL', color=COLORS['MWSL'], linewidth=1.5, marker='o', markersize=5)
    plt.plot(sim_time, lbdt_storage, label='LBDT', color=COLORS['LBDT'], linewidth=1.5, marker='v', markersize=5)
    plt.plot(sim_time, tibiov_storage, label='TI-BIoV', color=COLORS['TI-BIoV'], linewidth=1.5, marker='o', markerfacecolor='none', markeredgecolor=COLORS['TI-BIoV'], markersize=5)
    
    plt.xlabel("Time (min)", fontsize=10)
    plt.ylabel("Storage overhead (MB)", fontsize=10)
    
    plt.xlim(-100, 4200)
    plt.xticks(np.arange(0, 4001, 2000))
    plt.ylim(-300, 12000)
    plt.grid(True, linestyle='--')
    plt.legend(loc='upper left', fontsize=8)
    plt.tight_layout()
    plt.savefig("data/plots/fig_13_storage.png", dpi=300)
    plt.close()
    print("Saved fig_13_storage.png")

if __name__ == "__main__":
    print("Starting plotting process...")
    plot_fig8_reputation()
    plot_fig9_attacks()
    plot_fig10_latency_blocksize()
    plot_fig11_latency_rsus()
    plot_fig12_communication()
    plot_fig13_storage()
    print("All plots generated successfully!")
