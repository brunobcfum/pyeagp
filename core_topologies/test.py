#!/usr/bin/python3
#
# run iperf to measure the effective throughput between two nodes when
# n nodes are connected to a virtual wlan; run test for testsec
# and repeat for minnodes <= n <= maxnodes with a step size of
# nodestep

import datetime
from builtins import range

import parser
from core import load_logging_config
from core.emulator.coreemu import CoreEmu
from core.emulator.emudata import IpPrefixes, NodeOptions
from core.emulator.enumerations import NodeTypes, EventTypes
from core.location.mobility import BasicRangeModel
from core import constants

load_logging_config()


def example(options):
    # ip generator for example
    prefixes = IpPrefixes("10.0.0.0/24")

    # create emulator instance for creating sessions and utility methods
    coreemu = CoreEmu()
    session = coreemu.create_session()

    # must be in configuration state for nodes to start, when using "node_add" below
    session.set_state(EventTypes.CONFIGURATION_STATE)

    # create wlan network node
    wlan = session.add_node(_type=NodeTypes.WIRELESS_LAN)
    session.mobility.set_model(wlan, BasicRangeModel,config={'range':175, 'bandwidth': 54000000, 'jitter':0, 'delay': 5000, 'error': 0})
    session.mobility.get_models(wlan)

    # create nodes, must set a position for wlan basic range model
    node_options = NodeOptions()
    node_options.set_position(0, 0)

    """n1 = session.addobj(cls = pycore.nodes.class, name="n1")
    n1.setposition(x=209.0,y=243.0)
    wlan6 = session.addobj(cls = pycore.nodes.class, name="wlan6")
    wlan6.setposition(x=527.0,y=235.0)
    n2 = session.addobj(cls = pycore.nodes.class, name="n2")
    n2.setposition(x=273.0,y=297.0)
    n3 = session.addobj(cls = pycore.nodes.class, name="n3")
    n3.setposition(x=461.0,y=424.0)
    n4 = session.addobj(cls = pycore.nodes.class, name="n4")
    n4.setposition(x=550.0,y=460.0)
    n5 = session.addobj(cls = pycore.nodes.class, name="n5")
    n5.setposition(x=676.0,y=492.0)
    n7 = session.addobj(cls = pycore.nodes.class, name="n7")
    n7.setposition(x=354.0,y=354.0)
    n1.newnetif(net=wlan6, addrlist=["10.0.0.11/24"], ifindex=0)
    n2.newnetif(net=wlan6, addrlist=["10.0.0.10/24"], ifindex=0)
    n3.newnetif(net=wlan6, addrlist=["10.0.0.12/24"], ifindex=0)
    n4.newnetif(net=wlan6, addrlist=["10.0.0.13/24"], ifindex=0)
    n5.newnetif(net=wlan6, addrlist=["10.0.0.14/24"], ifindex=0)
    n7.newnetif(net=wlan6, addrlist=["10.0.0.15/24"], ifindex=0)"""


    for _ in range(options.nodes):
        node = session.add_node(node_options=node_options)
        interface = prefixes.create_interface(node)
        session.add_link(node.id, wlan.id, interface_one=interface)

    # instantiate session
    session.instantiate()

    # get nodes for example run
    first_node = session.get_node(2)
    #first_node.setposition(x=354.0,y=354.0)
    last_node = session.get_node(options.nodes + 1)
    #print("starting iperf server on node: %s" % first_node.name)
    #first_node.cmd(["/usr/bin/vcmd","--","xterm", "-hold"])
    #first_node.cmd(["./agent.py", 'mote0','sink','1','esp8266','100','test','11','11','eagp','adhoc','100','20000'],wait=True)
    address = prefixes.ip4_address(first_node)
    #print("node %s connecting to %s" % (last_node.name, address))
    #last_node.client.cmd(["xterm", "-ut", "-title", "self.name", "-e", constants.VCMD_BIN, "-c", last_node.ctrlchnlname, "--", '/home/bcf/Projetos/ouroboros/run.sh'])
    #last_node.client.term('bash')
    first_node.client.term_cmd("bash","/home/bcf/Projetos/ouroboros/run.sh")
    #first_node.cmd(["killall", "-9", "iperf"])
    #last_node.client.term()
    teste=input()
    # shutdown session
    coreemu.shutdown()


def main():
    options = parser.parse_options("test")

    start = datetime.datetime.now()
    print("running wlan example: nodes(%s) time(%s)" % (options.nodes, options.time))
    example(options)
    print("elapsed time: %s" % (datetime.datetime.now() - start))


if __name__ == "__main__":
    main()
