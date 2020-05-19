#!/usr/bin/env python3.7

""" 
Main simulation runner is part of a dissertation work about WSNs 
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

import  threading, sys, traceback, time, random, json, os, shutil, socket
from classes import prompt, log, node, nodedump
from apscheduler.schedulers.background import BackgroundScheduler

fwd_old = 0
inc=0
packet_counter = 0
anim = ['\\','|','/','-']

def main(tag):
        '''This is a simple scheduler that changes the state of the node based on time
        * Check it can changed to use the processor timers for each task instead of counters'''
        #this function controls all the tasks

        try:
            random.seed("this_is_wsn "+Node.tag); #Seed for random
            t1 = threading.Thread(target=prompt.prompt, args=(Node,))
            t1.start() #starts prompt
            
            # finally a scheduler that actually works
            scheduler = BackgroundScheduler()
            scheduler.add_job(task1, 'interval', seconds=(Node.sleeptime  /1000), id='awake')
            scheduler.add_job(task2, 'interval', seconds=Node.second/1000, id='sim_sec')
            scheduler.add_job(task3, 'interval', seconds=1, id='real_sec')
            scheduler.add_job(task5, 'interval', seconds=30*Node.second/1000, id='datalogger')
            scheduler.add_job(task7, 'interval', seconds=5, id='node_info')
            scheduler.add_job(task8, 'interval', seconds=8, id='node_neighbours')
            scheduler.start()
            while Node.stop != True:
                time.sleep(0.5)
            scheduler.remove_job('awake')
            scheduler.remove_job('sim_sec')
            scheduler.remove_job('real_sec')
            scheduler.remove_job('datalogger')
            scheduler.remove_job('node_info')
            scheduler.remove_job('node_neighbours')
            scheduler.shutdown()
            t1.join(timeout=1)
            os._exit(1)
        except KeyboardInterrupt:
            logger.print_error("Interrupted by ctrl+c")
            os._exit(1)
        except:
            logger.print_error("Scheduling error!")
            traceback.print_exc()

def task1(): #sleep/awake
    Node.awake() #this task is run when node is awake
    Node.sleep() #node goes back to sleep
    if Node.stop==False:
        if Node.Battery.battery_percent <= 1 or Node.lock == False:
            logger.print_alert("Simulation ended.")
            Node.lock=False
            prompt.lock=False
            Node.stop = True
            logger.print_alert('Logging')
            logger.datalog(Node)
            logger.log_messages(Node)
            try:
                shutil.move("./node_dumps", "reports/" + logger.simdir + "/")
                shutil.move("./neighbours", "reports/" + logger.simdir + "/")
            except:
                pass
            endfile = open("reports/" + logger.simdir + "/finished/"+tag+".csv","w") #
            endfile.write('done\n')
            endfile.close()
            try:
                Node.shutdown()
            except:
                pass
            return

def task2(): #1 tick per sim second
    if Node.lock==False:
        return
    Node.simulation_seconds += 1
    Node.Network.tSinkCurrent += 1 #create a scheduler on network and mode this there
    if Node.simulation_seconds > simulation_limit:
        Node.lock = False

def task3(): #1 tick per real second
    if Node.lock==False:
        return
    Node.simulation_tick_seconds += 1 
    fwd_new = Node.Network.protocol_stats[1]
    global inc, fwd_old, packet_counter
    if packet_counter > 5:
        Node.Network.traffic = Node.Network.packets / 5 
        Node.Network.packets = 0
        packet_counter = 0
    else:
        packet_counter += 1
    if fwd_new > fwd_old:
        fwd_old= fwd_new
        inc+=1
        if inc == 4:
            inc = 0
    logger.printxy(1,79,anim[inc])
    logger.printxy(2,70,Node.Network.traffic)
    logger.printxy(2,77,'pps')
    
def task5(): #datalogger
    if Node.lock==False:
        return
    logger.datalog(Node) #this task is run to log data to file

def task7(): #update node info for rest every 5 real seconds
    if Node.lock==False:
        return
    nodedump.Dump(Node)

def task8(): #update node neighbours for rest every 8 real seconds
    if Node.lock==False:
        return
    nodedump.Neighbours(Node)

def printhelp():
    'Prints help message'
    print()
    print("Routing agent - ")
    print()
    print("Usage:")
    print("./main [node_name] [role: mote or sink] [time multiplier] [energy_model] [TMAX] [Topology used] [x_coord] [y_coord] [protocol] [battery level] [simulation max time] ")
    print()

def startup():
    #this section is a synchronizer so that all nodes can start at the same time
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        os.remove("/tmp/ouroboros.sock."+tag)
    except OSError:
        #traceback.print_exc()
        pass
    s.bind("/tmp/ouroboros.sock."+tag)
    s.listen(1)
    conn, addr = s.accept()
    data = conn.recv(1024)
    #print(float(data)) 
    #receives the global time when they should start. Same for all and in this simulation the clock is universal since all nodes run in the same computer
    conn.close()
    return data

if __name__ == '__main__':  #for main run the main function. This is only run when this main python file is called, not when imported as a class
    try:
        print("This is a testing agent of a low power routing protocol node")
        print()
        try: #this should be made better
            tag = sys.argv[1]
            role = sys.argv[2]
            time_multi = float(sys.argv[3])
            board_type = sys.argv[4]
            tmax = int(sys.argv[5])
            topology = sys.argv[6]
            x = int(sys.argv[7])
            y = int(sys.argv[8])
            protocol = sys.argv[9].upper()
            net_trans = sys.argv[10].upper()
            batlim = int(sys.argv[11])
            simulation_limit = int(sys.argv[12])
        except:
            print("Problem parsing options")
            printhelp()
            os._exit(1)
        energy_model_file = open("energy_models.json","r").read()
        energy_model = json.loads(energy_model_file)
        for board in energy_model:
            if board['board'] == board_type:
                energy_model = board
                break
        print('Using energy model: ' + energy_model['board'] + ' with: ' + str(time_multi) + ' time multiplier')

        Node = node.Node(energy_model, tag, role, time_multi, x, y, batlim, net_trans, protocol,tmax) #create node object
        prompt = prompt.Prompt(Node)
        logger = log.Log(Node, tag, role, board_type, topology, protocol)
        logger.clean_nodedumps(Node)
        start=startup()

        while float(start) > time.time():
            pass

        #############################################################################
        main(tag); #call scheduler function
    except KeyboardInterrupt:
        logger.print_error("Interrupted by ctrl+c")
        logger.logfile.close()