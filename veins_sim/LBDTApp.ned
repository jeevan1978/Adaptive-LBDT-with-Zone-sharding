package veins_sim;

import org.car2x.veins.modules.application.ieee80211p.DemoBaseApplLayer;

simple LBDTApp extends DemoBaseApplLayer
{
    parameters:
        @class(veins_sim::LBDTApp);
        @display("i=block/app2");
        bool isRSU;
}
