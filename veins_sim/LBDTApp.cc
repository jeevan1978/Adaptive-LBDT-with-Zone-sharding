#include "LBDTApp.h"
#include <iostream>
#include <sstream>
#include <cstdlib>
#include <ctime>

Define_Module(veins_sim::LBDTApp);

namespace veins_sim {

// Helper to extract basic fields from JSON response strings
std::string extractJsonField(const std::string& json, const std::string& field) {
    size_t pos = json.find("\"" + field + "\"");
    if (pos == std::string::npos) return "";
    size_t start = json.find(":", pos);
    if (start == std::string::npos) return "";
    start = json.find_first_not_of(" \t\r\n\"", start + 1);
    if (start == std::string::npos) return "";
    
    if (json[start] == '{' || json[start] == '[') {
        char openChar = json[start];
        char closeChar = (openChar == '{') ? '}' : ']';
        int count = 1;
        size_t end = start + 1;
        while (end < json.length() && count > 0) {
            if (json[end] == openChar) count++;
            else if (json[end] == closeChar) count--;
            end++;
        }
        return json.substr(start, end - start);
    }
    
    size_t end = json.find_first_of(" \t\r\n,\"}[]", start);
    if (end == std::string::npos) return json.substr(start);
    return json.substr(start, end - start);
}

LBDTApp::LBDTApp() {
    stepTimer = nullptr;
    roundTimer = nullptr;
    epochTimer = nullptr;
    lastMicroblockHash = std::string(64, '0');
    lastKeyblockHash = std::string(64, '0');
    isRSU = false;
    zoneId = 0;
}

LBDTApp::~LBDTApp() {
    cancelAndDelete(stepTimer);
    cancelAndDelete(roundTimer);
    cancelAndDelete(epochTimer);
}

void LBDTApp::initialize(int stage) {
    veins::DemoBaseApplLayer::initialize(stage);
    
    if (stage == 0) {
        isRSU = par("isRSU").boolValue();
        
        // Calculate zone ID based on physical coordinates (10 km x 10 km grid split into 4x4 zones of 2.5km x 2.5km)
        double x = curPosition.x;
        double y = curPosition.y;
        int zone_x = (int)(x / 2500.0);
        int zone_y = (int)(y / 2500.0);
        zoneId = zone_x * 4 + zone_y;
        if (zoneId < 0) zoneId = 0;
        if (zoneId > 15) zoneId = 15;
        
        // Set up execution timers
        if (!isRSU) {
            // Vehicles check coordinates and trade at every step (1s)
            stepTimer = new cMessage("StepTimer");
            scheduleAt(simTime() + 1.0 + uniform(0, 0.5), stepTimer);
        } else if (getParentModule()->getIndex() == 0) {
            // Designate RSU 0 as the blockchain consensus coordinator
            roundTimer = new cMessage("RoundTimer");
            epochTimer = new cMessage("EpochTimer");
            scheduleAt(simTime() + 6.0, roundTimer);
            scheduleAt(simTime() + 60.0, epochTimer);
        }
    }
}

void LBDTApp::handleSelfMsg(cMessage* msg) {
    if (msg == stepTimer) {
        scheduleAt(simTime() + 1.0, stepTimer);
        
        // 20% probability of initiating a transaction inside this second
        if (dblrand() < 0.2) {
            bool isSeller = dblrand() < 0.5;
            double price = isSeller ? (5.0 + uniform(0, 5)) : (6.0 + uniform(0, 6));
            double qty = 1.0 + uniform(0, 4);
            
            // Dynamically calculate zone ID based on current coordinates
            double x = curPosition.x;
            double y = curPosition.y;
            int currentZoneId = (int)(x / 2500.0) * 4 + (int)(y / 2500.0);
            if (currentZoneId < 0) currentZoneId = 0;
            if (currentZoneId > 15) currentZoneId = 15;

            // Build the transaction JSON command payload
            std::stringstream ss;
            ss << "{\"cmd\":\"SUBMIT_TRADE_REQUEST\","
               << "\"veh_id\":\"veh_" << getParentModule()->getIndex() << "\","
               << "\"type\":\"" << (isSeller ? "offer" : "bid") << "\","
               << "\"price\":" << price << ","
               << "\"quantity\":" << qty << ","
               << "\"zone\":" << currentZoneId << ","
               << "\"step\":" << simTime().dbl() << "}";
               
            // Send to Python server to format trade correctly
            std::string response = sendSocketCommand(ss.str());
            std::string trade_data = extractJsonField(response, "trade_data");
            
            std::string status = extractJsonField(response, "status");
            if (!trade_data.empty() && status == "ok") {
                // Broadcast transaction data over IEEE 802.11p wireless network using TraCIDemo11pMessage
                veins::TraCIDemo11pMessage* wsm = new veins::TraCIDemo11pMessage("TradeRequest");
                populateWSM(wsm);
                wsm->setRecipientAddress(-1);
                wsm->setDemoData(response.c_str());
                sendDown(wsm);
            }
        }
    } else if (msg == roundTimer) {
        scheduleAt(simTime() + 6.0, roundTimer);
        
        // Trigger BFT Consensus validation for microblock every 6 seconds on Python server
        std::stringstream ss;
        ss << "{\"cmd\":\"COMMIT_MICROBLOCK\",\"step\":" << simTime().dbl()
           << ",\"last_microblock_hash\":\"" << lastMicroblockHash << "\""
           << ",\"last_keyblock_hash\":\"" << lastKeyblockHash << "\"}";
           
        std::string response = sendSocketCommand(ss.str());
        std::string status = extractJsonField(response, "status");
        if (status == "success") {
            lastMicroblockHash = extractJsonField(response, "hash");
            std::cout << "[Veins] Microblock committed. Hash: " << lastMicroblockHash.substr(0, 16) << std::endl;
        }
    } else if (msg == epochTimer) {
        scheduleAt(simTime() + 60.0, epochTimer);
        
        // Trigger Keyblock mining and committee election every 60 seconds on Python server
        std::stringstream ss;
        ss << "{\"cmd\":\"EPOCH_BOUNDARY\",\"step\":" << simTime().dbl()
           << ",\"last_microblock_hash\":\"" << lastMicroblockHash << "\""
           << ",\"last_keyblock_hash\":\"" << lastKeyblockHash << "\"}";
           
        std::string response = sendSocketCommand(ss.str());
        std::string status = extractJsonField(response, "status");
        if (status == "success") {
            lastKeyblockHash = extractJsonField(response, "hash");
            std::cout << "[Veins] Keyblock committed. Hash: " << lastKeyblockHash.substr(0, 16) << std::endl;
        }
    } else {
        veins::DemoBaseApplLayer::handleSelfMsg(msg);
    }
}

void LBDTApp::handleLowerMsg(cMessage* msg) {
    veins::BaseFrame1609_4* frame = check_and_cast<veins::BaseFrame1609_4*>(msg);
    veins::TraCIDemo11pMessage* wsm = dynamic_cast<veins::TraCIDemo11pMessage*>(frame);
    if (isRSU && wsm != nullptr) {
        // RSU extracts transaction requests and executes double auction
        std::string payload = wsm->getDemoData();
        std::cout << "[Veins RSU] Received WSM on RSU index " << getParentModule()->getIndex() << ". Payload: " << payload << std::endl;
        std::string status = extractJsonField(payload, "status");
        
        if (status == "ok") {
            std::string trade_data = extractJsonField(payload, "trade_data");
            std::string type = extractJsonField(trade_data, "type");
            
            if (type == "offer") {
                pendingOffersJson.push_back(trade_data);
            } else if (type == "bid") {
                pendingBidsJson.push_back(trade_data);
            }
            
            // Execute the double auction matching engine
            if (!pendingOffersJson.empty() && !pendingBidsJson.empty()) {
                std::stringstream ss;
                ss << "{\"cmd\":\"RUN_AUCTION\",\"step\":" << simTime().dbl() << ",\"offers\":[";
                for (size_t i = 0; i < pendingOffersJson.size(); ++i) {
                    ss << pendingOffersJson[i] << (i + 1 < pendingOffersJson.size() ? "," : "");
                }
                ss << "],\"bids\":[";
                for (size_t i = 0; i < pendingBidsJson.size(); ++i) {
                    ss << pendingBidsJson[i] << (i + 1 < pendingBidsJson.size() ? "," : "");
                }
                ss << "]}";
                
                std::cout << "[Veins RSU] Executing double auction matching on RSU index " << getParentModule()->getIndex() << std::endl;
                std::string response = sendSocketCommand(ss.str());
                std::cout << "[Veins RSU] Double auction response: " << response << std::endl;
                std::string status = extractJsonField(response, "status");
                if (status == "ok") {
                    pendingOffersJson.clear();
                    pendingBidsJson.clear();
                }
            }
        }
    }
    
    delete wsm;
}

void LBDTApp::handleLowerControl(cMessage* msg) {
    veins::DemoBaseApplLayer::handleLowerControl(msg);
}

std::string LBDTApp::sendSocketCommand(const std::string& jsonCommand) {
    int sock = 0;
    struct sockaddr_in serv_addr;
    char buffer[4096] = {0};
    
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        return "{\"status\":\"error\",\"message\":\"Socket creation error\"}";
    }
    
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(8000);
    
    if (inet_pton(AF_INET, "127.0.0.1", &serv_addr.sin_addr) <= 0) {
        close(sock);
        return "{\"status\":\"error\",\"message\":\"Invalid address\"}";
    }
    
    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        close(sock);
        return "{\"status\":\"error\",\"message\":\"Connection failed\"}";
    }
    
    std::string cmd = jsonCommand + "\n";
    ::send(sock, cmd.c_str(), cmd.length(), 0);
    
    std::string response = "";
    int valread = 0;
    while ((valread = ::read(sock, buffer, 4096)) > 0) {
        response.append(buffer, valread);
        if (response.find("\n") != std::string::npos) {
            break;
        }
    }
    ::close(sock);
    return response;
}

void LBDTApp::finish() {
    veins::DemoBaseApplLayer::finish();
    if (isRSU && getParentModule()->getIndex() == 0) {
        // Tell Python server to write finalized logs and statistics
        sendSocketCommand("{\"cmd\":\"SAVE_LOGS\"}");
    }
}

} // namespace veins_sim
