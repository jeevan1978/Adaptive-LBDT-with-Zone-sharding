#!/bin/bash
set -e

echo "[Entrypoint] Starting Python LBDT socket server..."
python3 -u -m src.simulation.socket_server &
SERVER_PID=$!

echo "[Entrypoint] Starting Veins SUMO launch daemon..."
python3 /opt/veins/bin/veins_launchd -vv -p 9999 -L data/sumo-launchd.log > data/veins_launchd.log 2>&1 &
LAUNCHD_PID=$!

# Wait for background services to bind to ports
sleep 3

echo "[Entrypoint] Running OMNeT++ Veins Simulation (LBDT)..."
cd /app
source /opt/omnetpp/setenv
export LD_LIBRARY_PATH=/opt/veins/src:$LD_LIBRARY_PATH
./veins_sim/veins_sim -u Cmdenv -c General -n .:/opt/veins/src/veins veins_sim/omnetpp.ini

echo "[Entrypoint] Simulation run complete. Shutting down background processes..."
kill $SERVER_PID $LAUNCHD_PID || true
wait $SERVER_PID $LAUNCHD_PID 2>/dev/null || true
echo "[Entrypoint] Done."
