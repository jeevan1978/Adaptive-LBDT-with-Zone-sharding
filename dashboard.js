// LBDT Reputation Simulation logic
document.addEventListener("DOMContentLoaded", () => {
    // Load simulation log metrics dynamically
    loadSimulationMetrics();

    function injectMetrics(data) {
        // Inject values into DOM
        const elemLatency = document.getElementById('metric-latency');
        const elemKeyblocks = document.getElementById('metric-keyblocks');
        const elemMicroblocks = document.getElementById('metric-microblocks');
        const elemBft = document.getElementById('metric-bft');
        const elemSafety = document.getElementById('metric-safety');
        
        if (elemLatency && data.avg_latency !== undefined) {
            elemLatency.textContent = `${data.avg_latency.toFixed(2)}s`;
        }
        if (elemKeyblocks && data.blockchain_keyblocks !== undefined) {
            elemKeyblocks.textContent = data.blockchain_keyblocks;
        }
        if (elemMicroblocks && data.blockchain_microblocks !== undefined) {
            elemMicroblocks.textContent = data.blockchain_microblocks;
        }
        if (elemBft && data.bft_msg_count !== undefined) {
            elemBft.textContent = data.bft_msg_count.toLocaleString();
        }
        if (elemSafety && data.committee_safety !== undefined) {
            let allSafe = true;
            data.committee_safety.forEach(log => {
                if (log.malicious_ratio >= 0.3333) {
                    allSafe = false;
                }
            });
            elemSafety.textContent = allSafe ? 'Verified' : 'Unsafe';
            if (!allSafe) {
                elemSafety.className = 'metric-value error-text';
            }
        }
    }

    async function loadSimulationMetrics() {
        try {
            // First check if the global variable is preloaded (CORS bypass for local file:// URL)
            if (typeof simulationMetrics !== 'undefined') {
                console.log('Loading metrics from preloaded script variable (CORS bypass).');
                injectMetrics(simulationMetrics);
                return;
            }

            const response = await fetch('data/simulation_log.json');
            if (!response.ok) {
                console.warn('Simulation log file not found or failed to load. Using placeholders.');
                return;
            }
            const data = await response.json();
            injectMetrics(data);
        } catch (e) {
            console.error('Error loading simulation metrics:', e);
        }
    }

    // Sliders
    const sliderGamma = document.getElementById("param-gamma");
    const sliderC = document.getElementById("param-c");
    const sliderB = document.getElementById("param-b");
    const sliderPeers = document.getElementById("param-peers");
    const sliderPos = document.getElementById("param-pos");
    const sliderNeg = document.getElementById("param-neg");

    // Value Labels
    const valGamma = document.getElementById("val-gamma");
    const valC = document.getElementById("val-c");
    const valB = document.getElementById("val-b");
    const valPeers = document.getElementById("val-peers");
    const valPos = document.getElementById("val-pos");
    const valNeg = document.getElementById("val-neg");

    // Initialize Chart
    const ctx = document.getElementById("reputationSimChart").getContext("2d");
    let chart;

    function clip(val, minVal, maxVal) {
        return Math.max(minVal, Math.min(maxVal, val));
    }

    // Function to calculate LBDT reputation array
    function calculateReputations(gamma, c, b, peers, deltaPos, deltaNeg) {
        const reps = [];
        const history = [];
        const lnPeers = Math.log(Math.max(2, peers));

        for (let step = 0; step <= 60; step++) {
            // Determine behavior
            if (step <= 30) {
                history.push(deltaPos);
            } else if (step <= 40) {
                history.push(deltaNeg);
            } else {
                history.push(deltaPos);
            }

            // Calculate aged sum
            let agedSum = 0;
            for (let i = 0; i <= step; i++) {
                agedSum += Math.pow(gamma, step - i) * history[i];
            }

            const r_n = agedSum * lnPeers;
            const score = clip(r_n, -50.0, 50.0);
            
            // Gompertz function: Rep_i(r_n) = a * exp(-b * exp(-c * r_n)) where a=1.0
            const rep = 1.0 * Math.exp(-b * Math.exp(-c * score));
            reps.push(rep);
        }
        return reps;
    }

    // Static comparative curves
    function getMWSLCurve() {
        const reps = [];
        let curr = 0.5;
        for (let step = 0; step <= 60; step++) {
            if (step <= 30) {
                curr = Math.min(0.95, curr + 0.008);
            } else if (step <= 40) {
                curr = Math.max(0.2, curr - 0.04);
            } else {
                curr = Math.min(0.95, curr + 0.008);
            }
            reps.push(curr);
        }
        return reps;
    }

    function getTIBIoVCurve() {
        const reps = [];
        let curr = 0.5;
        for (let step = 0; step <= 60; step++) {
            if (step <= 30) {
                curr = 0.5 + 0.45 * (2.0 / Math.PI) * Math.atan(0.1 * step);
            } else if (step <= 40) {
                curr = Math.max(0.1, curr - 0.05);
            } else {
                let recovered = step - 40;
                curr = Math.min(0.95, curr + 0.015 * (2.0 / Math.PI) * Math.atan(0.2 * recovered));
            }
            reps.push(curr);
        }
        return reps;
    }

    function updateChart() {
        const gamma = parseFloat(sliderGamma.value);
        const c = parseFloat(sliderC.value);
        const b = parseFloat(sliderB.value);
        const peers = parseInt(sliderPeers.value);
        const deltaPos = parseFloat(sliderPos.value);
        const deltaNeg = parseFloat(sliderNeg.value);

        // Update display text
        valGamma.textContent = gamma.toFixed(2);
        valC.textContent = c.toFixed(2);
        valB.textContent = b.toFixed(2);
        valPeers.textContent = peers;
        valPos.textContent = deltaPos.toFixed(2);
        valNeg.textContent = deltaNeg.toFixed(1);

        const lbdtData = calculateReputations(gamma, c, b, peers, deltaPos, deltaNeg);

        chart.data.datasets[0].data = lbdtData;
        chart.update();
    }

    // Chart Configuration
    const labels = Array.from({length: 61}, (_, i) => i);
    const initialLBDT = calculateReputations(0.95, 0.5, 0.7, 100, 0.1, -2.0);
    const initialMWSL = getMWSLCurve();
    const initialTIBIoV = getTIBIoVCurve();

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'LBDT (Simulated / Interactive)',
                    data: initialLBDT,
                    borderColor: '#0f82ff',
                    backgroundColor: 'rgba(15, 130, 255, 0.05)',
                    borderWidth: 2.5,
                    pointRadius: 0,
                    tension: 0.15,
                    fill: true
                },
                {
                    label: 'MWSL (Reference)',
                    data: initialMWSL,
                    borderColor: '#ff9f00',
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    tension: 0.1,
                    fill: false
                },
                {
                    label: 'TI-BIoV (Reference)',
                    data: initialTIBIoV,
                    borderColor: '#10b981',
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    tension: 0.15,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#F3F4F6',
                        font: {
                            family: 'Inter',
                            size: 11
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Number of Interactions',
                        color: '#9CA3AF',
                        font: {
                            family: 'Inter',
                            size: 11
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#9CA3AF'
                    }
                },
                y: {
                    min: 0,
                    max: 1.05,
                    title: {
                        display: true,
                        text: 'Reputation Value',
                        color: '#9CA3AF',
                        font: {
                            family: 'Inter',
                            size: 11
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#9CA3AF'
                    }
                }
            }
        }
    });

    // Add slider listeners
    [sliderGamma, sliderC, sliderB, sliderPeers, sliderPos, sliderNeg].forEach(slider => {
        slider.addEventListener("input", updateChart);
    });
});
