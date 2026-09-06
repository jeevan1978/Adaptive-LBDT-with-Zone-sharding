#pragma once

#include <string>
#include <vector>
#include <map>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>

#include "veins/modules/application/ieee80211p/DemoBaseApplLayer.h"
#include "veins/modules/utility/Consts80211p.h"
#include "veins/modules/application/traci/TraCIDemo11pMessage_m.h"

namespace veins_sim {

class LBDTApp : public veins::DemoBaseApplLayer {
protected:
    bool isRSU;
    int zoneId;
    
    // Timers
    cMessage* stepTimer;
    cMessage* roundTimer;
    cMessage* epochTimer;
    
    // Transactions queues for RSU double auction matching
    std::vector<std::string> pendingOffersJson;
    std::vector<std::string> pendingBidsJson;
    
    // Hash records
    std::string lastMicroblockHash;
    std::string lastKeyblockHash;

    // Helper to send TCP command to the Python Socket Server
    std::string sendSocketCommand(const std::string& jsonCommand);

public:
    LBDTApp();
    virtual ~LBDTApp();

    virtual void initialize(int stage) override;
    virtual void finish() override;

protected:
    virtual void handleSelfMsg(cMessage* msg) override;
    virtual void handleLowerMsg(cMessage* msg) override;
    virtual void handleLowerControl(cMessage* msg) override;
};

} // namespace veins_sim
