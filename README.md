# Python Implementation of the EAGP protocol

## Routing protocol developed as part of a paper of same name

### Usage to run one node only:

Usually not usefull when simulating. See below how to run several nodes via the simulator script.

./main [node_name] [role: mote or sink] [time multiplier] [energy_model] [TMAX] [Topology used] [x_coord] [y_coord] [protocol] [ipv4 or ipv6] [battery level] [simulation max time]

* nome_name - Just a node identifier
* role - Indicate if the node will be a regular mote or a sink
* time multiplier - When set to 1, the simulation runs at normal speed. The a value such as 0.1 is passed, all timers in the simulation will be multiplied by 0.1, meaning that everything will run 10 times faster. 
* energy_model - This needs to be one of the models available in the energy_models.json files. It is possible to add new models and use if needed.
* TMAX - This is the TMAX paramenter of the EAGP protocol. Ignored by other protocols
* Topology used - Just the name of the current topology being run. This is used only for the reports
* x_coord - Position of the node. This is used only for the reports
* y_coord - Position of the node. This is used only for the reports
* protocol - Which protocol to use: gossip, gossipfo, eagp, eagpd, mcfa
* ipv4 or ipv6 - Write adhoc here since IPV6 was not working well with CORE
* battery level - This is the initial battery level of the node from 0 to 100 (the total battery size can be changed in settings.json)
* simulation max time - This is the maximum time the simulation is allowed to run

### Interface commands available in the prompt: 

* info      - Diplay general information about the sensor
* network   - Display information about the routing protocol
* buffer    - Display the message buffer when available
* battery   - Display information about energy and battery levels
* visible   - Display the list of visible neighbours (only when available)
* msg       - Display the list of handled messages
* monitor   - Enable monitor mode
* clear     - Clear the display
* help      - Diplay this help message
* quit      - Exit the agent


## Info:

Currently configured to use CORE (https://github.com/coreemu/core/releases) as simulation space and IPv4 AD-HOC broadcast beacons for advertising and routing.
This was tested with release 5.3.1 and instructions on how to install can be found here: https://coreemu.github.io/core/install.html

### Running the full simulation by calling a CORE simulation script

The simulation scenarios are configured directly inside the simulations scripts locate inside the core_topologies files.
For example, to run the symmetrical simulation, run directly the script:

```bash
./core_topologies/symmetrical.py TMAX PROTOCOL MULTIPLIER MAXTIME
```

The following needs to be added to: /usr/lib/python3/dist-packages/core/nodes/client.py

```python
def term_cmd(self, sh="/bin/sh", cmd="", arguments=[]):
    args = ("xterm", "-ut", "-title", self.name, "-e", constants.VCMD_BIN, "-c", self.ctrlchnlname, "--", sh, cmd, arguments[0])
    if "SUDO_USER" in os.environ:
        args = ("su", "-s", "/bin/sh", "-c",
                "exec " + " ".join(map(lambda x: "'%s'" % x, args)),
                os.environ["SUDO_USER"])
    return os.spawnvp(os.P_NOWAIT, args[0], args)
```

## Configuration files

The following configuration files need to be adjusted according to the desired simulation. Other parameters can be set inside the code.

### settings.json

{
    "node_battery_mAh" : 500,
    "sink_battery_mAh" : 15000,
    "battery_voltage"  : 3.7,
    "base_sleep_time_s": 60,
    "tx_time_ms"       : 30,
    "rx_time_ms"       : 40,
    "ttl"              : 11,
    "fan_out_max"      : 3,
    "sink_starvation"  : 500
}

* node_battery_mAh - Battery size of a mote
* sink_battery_mAh - Battery size of a sink - Usually much larger since it has to work more
* battery_voltage - Voltage of the battery
* base_sleep_time_s - Sleep time of nodes. It is a base since for simulation a random amount of seconds is added to garantee heterogeneity
* tx_time_ms - Average duration of radio transmition
* rx_time_ms - Average duration of radio reception
* ttl - Time to live of each packet
* fan_out_max - Maximum fanout
* sink_starvation - How long a sink can wait for new packets. If after this time the sink doesn't receive anything, it  means that the network is dead and the simulation is stopped.

### energy_models.json

This is a list of json models. Each one corresponds to one sensor board.

{
    "board" : "esp8266",
    "deepSleep_current" : 0.000010,
    "modemSleep_current" : 0.0150,
    "awake_current" : 0.0810,
    "tx_current" : 0.170,
    "rx_current" : 0.056,
    "sensor_energy" : 0.000000887,
    "multiplier" : 250,
    "comment" : "Everything current is A and energy is J"
}
