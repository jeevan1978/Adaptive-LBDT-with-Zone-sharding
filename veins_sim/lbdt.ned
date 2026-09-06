package veins_sim;

import org.car2x.veins.nodes.RSU;
import org.car2x.veins.nodes.Scenario;

network LBDTScenario extends Scenario
{
    submodules:
        rsu[400]: RSU {
            @display("p=250,250;i=device/antennatower");
        }
}
