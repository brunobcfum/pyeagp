import sys, json, os

class Dump():
    def __init__(self, node):
        if not os.path.exists("node_dumps"):
            try:
                os.makedirs("node_dumps")
            except:
                pass
        dumpfile = open("node_dumps/" + node.tag + ".json","w")
        self.node_info(dumpfile, node)
    
    def node_info(self, dumpfile, node):
        data = json.dumps({'nodename':node.tag,
                            'node mode':node.Network.mode,
                            'current value':node.value,
                            'battery energy':node.Battery.battery_energy,
                            'battery percent':node.Battery.battery_percent,
                            'average level':node.Network.average,
                            'sleep virtual time':node.sleeptime/node.multiplier,
                            'sleep time':node.sleeptime,
                            'node tmax':node.Network.tmax/node.multiplier,
                            'node tnext':node.Network.tnext/node.multiplier,
                            'bcast address':node.Network.bcast_group,
                            'role':node.role,
                            'msgs created':node.Network.protocol_stats[0],
                            'msgs forwarded':node.Network.protocol_stats[1],
                            'msgs discarded':node.Network.protocol_stats[3],
                            'msgs delivered':node.Network.protocol_stats[2],
                            'energy in comp':node.Battery.computational_energy,
                            'energy in comm':node.Battery.communication_energy,
                            'elapsed virtual time':node.simulation_seconds,
                            'elapsed time':node.simulation_tick_seconds})
        dumpfile.write(data)
        dumpfile.flush()
        return

class Neighbours():
    def __init__(self, node):
        if not os.path.exists("neighbours"):
            try:
                os.makedirs("neighbours")
            except:
                pass
        dumpfile = open("neighbours/" + node.tag + ".json","w")
        self.dump(dumpfile, node)
    
    def dump(self, dumpfile, node):
        for member in range(len(node.Network.visible)):
            data = json.dumps({'nodename':node.Network.visible[member][0],
                                'ip':node.Network.visible[member][0],
                                'last seen':node.Network.visible[member][1],
                                'battery':node.Network.visible[member][2]})
            dumpfile.write(data+";")
        dumpfile.flush()
        return