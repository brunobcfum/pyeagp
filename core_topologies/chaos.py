#!/usr/bin/python3
#
# run iperf to measure the effective throughput between two nodes when
# n nodes are connected to a virtual wlan; run test for testsec
# and repeat for minnodes <= n <= maxnodes with a step size of
# nodestep

import threading, sys, time, random, os, traceback, playsound,json
import rest, socket
import parser


import logging
from builtins import range
from core import load_logging_config
from core.emulator.coreemu import CoreEmu
from core.emulator.emudata import IpPrefixes, NodeOptions
from core.emulator.enumerations import NodeTypes, EventTypes
from core.location.mobility import BasicRangeModel
from core import constants

load_logging_config()

nodes_to_send = []

class Auxiliar:

    def __init__(self, path, motes):
        self.motes = motes
        self.path = path
        self.nodesfinished = 0

    def random_walk(self,motes):
        for mote in motes:
            pos = mote.getposition()
            #print(motes[0].getposition())
            mote.setposition(pos[0]+random.randint(-6,6),pos[1]+random.randint(-6,6))
    
    def check_finished(self):
        files = []
        for (dirpath, dirnames, filenames) in os.walk(self.path):
            files.extend(filenames)
            break
        if len(files) >= len(self.motes):
            print('should be finished')
            return False
        if len(files) > self.nodesfinished:
            self.nodesfinished = len(files)
            logging.info(str(self.nodesfinished) + " nodes finished")
        return True
        

def topology(tmax=10,protocol='eagp',time_mul=0.1,simul_max=20000):
    global nodes_to_send
    radius = 154
    topofile = (os.path.basename(__file__)).split('.')[0]
    motes = []
    """   battery = [ 
        '99', '89', '87', '95', '99',
        '78', '87', '94', '96', '78',
        '86', '94', '93', '96', '94',
        '88', '84', '99', '79', '82',
        '99', '69', '89', '96', '92',
        '95', '92', '91', '96', '87'
    ]   """
    
    battery = [ 
    '99', '89', '87', '95', '99',
    '78', '67', '94', '96', '78',
    '86', '94', '93', '57', '94',
    '88', '47', '99', '79', '82',
    '99', '69', '89', '37', '92',
    '95', '27', '91', '96', '87'
    ]
    # ip generator for example
    prefixes = IpPrefixes("10.0.0.0/24")

    # create emulator instance for creating sessions and utility methods
    coreemu = CoreEmu()
    session = coreemu.create_session()

    # must be in configuration state for nodes to start, when using "node_add" below
    session.set_state(EventTypes.CONFIGURATION_STATE)

    # create wlan network node
    wlan = session.add_node(_type=NodeTypes.WIRELESS_LAN)
    session.mobility.set_model(wlan, BasicRangeModel,config={'range':radius, 'bandwidth': 54000000, 'jitter':0, 'delay': 5000, 'error': 0})
    session.mobility.get_models(wlan)


    # create nodes, must set a position for wlan basic range model
    node_options=[]
    for i in range(0,30):
        node_options.append(NodeOptions(name='mote'+str(i)))
    
    node_options[0].set_position(37,363  )
    node_options[1].set_position(180,503 )
    node_options[2].set_position(844,213 )
    node_options[3].set_position(517,460 )
    node_options[4].set_position(371,491 )
    node_options[5].set_position(1070,224)
    node_options[6].set_position(213,277 )
    node_options[7].set_position(83,40   )
    node_options[8].set_position(649,148 )
    node_options[9].set_position(790,311 )
    node_options[10].set_position(359,518 )
    node_options[11].set_position(22,461  )
    node_options[12].set_position(728,397 )
    node_options[13].set_position(966,348 )
    node_options[14].set_position(92,344  )
    node_options[15].set_position(733,352 )
    node_options[16].set_position(979,231 )
    node_options[17].set_position(866,461 )
    node_options[18].set_position(357,269 )
    node_options[19].set_position(863,560 )
    node_options[20].set_position(205,408 )
    node_options[21].set_position(312,404 )
    node_options[22].set_position(94,219  )
    node_options[23].set_position(184,105 )
    node_options[24].set_position(758,85  )
    node_options[25].set_position(720,553 )
    node_options[26].set_position(935,386 )
    node_options[27].set_position(662,243 )
    node_options[28].set_position(20,90   )
    node_options[29].set_position(636,453 )
    #adding the nodes
    for node_opt in node_options:
        motes.append(session.add_node(node_options=node_opt))

    #configuring links
    for mote in motes:
        interface = prefixes.create_interface(mote)
        session.add_link(mote.id, wlan.id, interface_one=interface)

    # instantiate session
    #session.save_xml('teste.xml')
    session.instantiate()
    
    #get simdir
    simdir = str(time.localtime().tm_year) + "_" + str(time.localtime().tm_mon) + "_" + str(time.localtime().tm_mday) + "_" + str(time.localtime().tm_hour) + "_" + str(time.localtime().tm_min)

    #create sink
    sink=session.get_node(29+2)
    motes[29].client.term_cmd("bash","/opt/eagp_sim/run.sh",[str(sink.name) + ' sink ' + str(time_mul) + ' esp8266 ' + str(tmax) + ' ' + topofile + ' ' +  str(node_options[0].x)  + ' ' +  str(node_options[0].y) + ' ' + protocol + ' adhoc '+ battery[0] + ' ' + str(simul_max)])

    #create motes
    for i in range(0,len(motes)-1):
        mote=session.get_node(i+2)
        #motes[i].client.term('bash')
        motes[i].client.term_cmd("bash","/opt/eagp_sim/run.sh",[str(mote.name) + ' mote ' + str(time_mul) + ' esp8266 ' + str(tmax) + ' ' + topofile + ' ' + str(node_options[i].x)  + ' ' +  str(node_options[i].y) + ' ' + protocol + ' adhoc '+ battery[i] + ' ' + str(simul_max)])

    time.sleep(5) #wait for nodes to start and create socket
    time_to_start = time.time()+2
    #firing up the motes
    for i in range(0,len(motes)):
      mote=session.get_node(i+2)
      try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect("/tmp/ouroboros.sock."+str(mote.name))
        s.send(str(time_to_start).encode())
        s.close()
      except:
        #pass
        traceback.print_exc()

    time.sleep(1)
    t1 = threading.Thread(target=send_nodes)
    t1.start() #starts socket
    Rest = rest.Api(motes)
    path ="./reports/" + simdir + "/finished"
    logging.info("Checking for nodes finished in: " + path)
    Aux = Auxiliar(path, motes)
    lock=True
    counter = 0
    while lock==True:
        lock = Aux.check_finished()
        #if counter > 40: Aux.random_walk(motes)
        nodes_to_send = []
        for mote in motes:
            data = mote.data('node')
            nodes_to_send.append(data)
        nodes_to_send.append(radius)
        counter += 1
        time.sleep(1)

    # shutdown session
    Rest.shutdown()
    stop_thread()
    t1.join(timeout=1)
    playsound.playsound('fim.mp3')
    coreemu.shutdown()

def send_nodes():
    global nodes_to_send
    #this section is a synchronizer so that all nodes can start at the same time
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        os.remove("/tmp/ouroboros/nodes.sock")
        os.mkdir("/tmp/ouroboros/")
    except OSError:
        #traceback.print_exc()
        pass
    s.bind("/tmp/ouroboros/nodes.sock")
    s.listen(1)
    while True:
        conn, addr = s.accept()
        data = conn.recv(64)
        if data.decode()=='get':
            conn.send(json.dumps(nodes_to_send).encode())
        elif data.decode()=='quit':
            break
        conn.close()    
    #print(float(data)) 
    #receives the global time when they should start. Same for all and in this simulation the clock is universal since all nodes run in the same computer
    s.close()
    return data

def stop_thread():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect("/tmp/ouroboros/nodes.sock")
    s.send('quit'.encode())
    s.close()


if __name__ == "__main__":
    try:
        tmax = sys.argv[1]
        protocol = sys.argv[2]
        time_mul = float(sys.argv[3])
        simul_max = int(sys.argv[4])
    except:
        tmax = 100
        protocol = 'eagp'
        time_mul = 1
        simul_max = 20000
    topology(tmax,protocol,time_mul,simul_max)
