#!/usr/bin/env python3 

""" 
Report class is part of a dissertation work about WSNs 
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

# TODO #
# Remove / from the end of indir


import os, math, struct, sys, json, traceback, time, argparse, statistics
import matplotlib.pyplot as plt
import numpy as np


class Report ():

    def __init__ (self,folder=''):
        print("Preparing report on folder: " + folder)
        self.folder = folder
        self.t = 30 # time between messages
        self.tmax = 0
        self.qos_collapse = 50 #% of loss messages when we consider that the qos collapsed
        try:
            self.node_averages()
            pass
        except:
            traceback.print_exc()
            sys.exit()
        try:
            self.net_long()
            pass
        except:
            traceback.print_exc()
        try:
            self.sink_stats()
            pass
        except:
            traceback.print_exc()
        try:
            self.nodes_plot()
            pass
        except:
            traceback.print_exc()
        try:
            self.net_long_plot()
            pass
        except:
            traceback.print_exc()
        try:
            self.final()
            pass
        except:
            traceback.print_exc()        
        try:
            self.node_stats()
            pass
        except:
            traceback.print_exc()
        
    def node_averages(self):
        nodes_reports = []
        nodes_data = []
        battery_data = []
        node_report_file = open(self.folder+"/nodes_report"+".csv","w")
        config_report_file = open(self.folder+"/nodes_config"+".txt","w")
        print("Preparing node averages report on folder: " + self.folder)
        for (dirpath, dirnames, filenames) in os.walk(self.folder):
            nodes_reports.extend(filenames)
            break
        for node in nodes_reports:
            node_data=node.split("_")
            if node_data[0] == "sim":
                nodes_data.append(node_data)
        #print(nodes_data[0])
        #print(len(nodes_data))
        self.topo = nodes_data[0][6]
        #self.t = int(nodes_data[0][4])
        config_report_file.write("Number of nodes"+":"+str(len(nodes_data))+"\n")
        config_report_file.write("Topology used"+":"+nodes_data[0][6]+"\n")
        config_report_file.write("Sleep time"+":"+str(nodes_data[0][4])+"\n")
        config_report_file.write("Energy model"+":"+nodes_data[0][5]+"\n")
        config_report_file.write("Protocol"+":"+nodes_data[0][7]+"\n")
        config_report_file.write("Simulation date"+":"+nodes_data[0][8].split(".")[0]+"\n")
        config_report_file.close()
        logfiles = []
        logfile = []
        for node in nodes_reports:
            node_data=node.split("_")
            if node_data[0] == "sim":
                print("Reading " + node)
                logfile = open(self.folder + "/"+ node).readlines()
                logfiles.append(logfile)
                logfiles[len(logfiles)-1][1] = node_data[2]
        #node_report_file.write("\n")
        node_report_file.write("Node"+";"+"Comutations"+";"+logfile[0])
        for log in logfiles:
            node_battery = {}
            node_battery[log[1]] = []
            old_mode = ""
            new_mode = ""
            mode_counter = 0
            for i in range(2,len(log)):
                line_split=log[i].split(";")
                #print(line_split)
                new_mode = line_split[3]
                if (new_mode != old_mode):
                    #print ("aqui: "+new_mode+" "+old_mode  )
                    mode_counter+=1
                    old_mode = new_mode
                node_battery[log[1]].append([line_split[0], line_split[1]])
            node_report_file.write(log[1] + ";" + str(mode_counter) +";" + log[len(log)-1])
            #print((log[len(log)-1].split(";")[5]))
            battery_data.append(node_battery)
            try:
                self.tmax = float(log[len(log)-1].split(";")[5])
            except:
                self.tmax = 60
        node_report_file.close()
        print("TMAX= "+str(self.tmax))
        battery_data_lines = []
        time_line = ['Time']
        for node in battery_data:
            node_line = []
            for node_name, energy in node.items():
                if node_name == 'mote0':
                    for data in energy:
                        time_line.append(data[0])
                node_line.append(node_name)
                for data in energy:
                    node_line.append(data[1])
            battery_data_lines.append(node_line)
        for node in battery_data_lines:
            pass
            #print(len(node))
        battery_data_lines.append(time_line)
        transposta = [[battery_data_lines[j][i] for j in range(len(battery_data_lines))] for i in range(len(battery_data_lines[0]))] 
        battery_report_file = open(self.folder+"/battery_report"+".csv","w")
        for line in transposta:
            for item in line:
                battery_report_file.write(item+";")
            battery_report_file.write("\n")
        battery_report_file.close()

        plt.style.use('ggplot')
        plt.title('Battery Level Decay')
        plt.ylabel('Battery Level (%)')
        plt.xlabel('Time(s)')

        battery_data_lines[len(battery_data_lines)-1].pop(0)
        time = list(map (int, battery_data_lines[len(battery_data_lines)-1]))
        #print (time)
        for i in range(0,len(battery_data_lines)-1):
            if i != len(battery_data_lines)-1:
                battery_data_lines[i].pop(0)
            results = list(map(float, battery_data_lines[i]))
            #print(battery_data_lines[len(battery_data_lines)-1])
            plt.plot(time,results, label = 'Received')


        plt.tight_layout()
        #plt.legend()
        plt.savefig(self.folder+'/nodes_battery.png')
        plt.close()
        

    def sink_stats(self):
        mess_reports = []
        motes = {}
        sinks = {}
        repeated = []
        max_hops = []
        min_hops = []
        latency = []
        final_report = []
        sink_messages = []
        sink_report_file = open(self.folder+"/sink_report"+".csv","w")
        print("Preparing node stats report on folder: " + self.folder)
        for (dirpath, dirnames, filenames) in os.walk(self.folder+"/message_dumps"):
            mess_reports.extend(filenames)
            break
        for node in mess_reports:
            node_data=node.split("_")
            if (node_data[3]=="sink"):
                sinks[node_data[2]]=node
        #print(sinks)
        print("Reading delivered messages from " + str(len(sinks)) + " sinks")
        for sink, sink_report in sinks.items():
            sinkfile = open(self.folder+"/message_dumps/"+sink_report).readlines()
            for sink_mess in sinkfile:
                #print(sink_mess[0])
                sink_messages.append(sink_mess.split(";"))
        print (str(len(sink_messages)) + " Messages were delivered")
        for i in range(1,len(sink_messages)):
            repeated.append(int(sink_messages[i][4])-1)
            max_hops.append(int(sink_messages[i][5]))
            min_hops.append(int(sink_messages[i][6]))
            latency.append(int(sink_messages[i][3])-int(sink_messages[i][2]))
            if len(final_report) > 0: 
                for element in range(len(final_report)): #check if it's a new node
                    #print(final_report[element][0])
                    if final_report[element][0] == sink_messages[i][1]: #we already have that one
                        if int(sink_messages[i][5]) > final_report[element][1]:
                            final_report[element][1] = int(sink_messages[i][5])
                        elif int(sink_messages[i][6]) < final_report[element][2]:
                            final_report[element][2] = int(sink_messages[i][6])
                        not_there = False
                        final_report[element][3] += 1
                        break
                    else:
                        #final_report.append([sink_messages[i][2],int(sink_messages[i][5]),int(sink_messages[i][6])])
                        not_there = True
            else:
                not_there = True
                #final_report.append([sink_messages[i][2],int(sink_messages[i][5]),int(sink_messages[i][6])])
            if not_there:
                final_report.append([sink_messages[i][1],int(sink_messages[i][5]),int(sink_messages[i][6]),0])
        sink_report_file.write("Value"+";"+"Median"+";"+"Mean"+";"+"Std dev"+";"+"\n")
        sink_report_file.write("Repeated messages"+";"+str(statistics.median(repeated))+";"+str(statistics.mean(repeated))+";"+str(statistics.stdev(repeated))+"\n")
        sink_report_file.write("Max hops"+";"+str(statistics.median(max_hops))+";"+str(statistics.mean(max_hops))+";"+str(statistics.stdev(max_hops))+"\n")
        sink_report_file.write("Min hops"+";"+str(statistics.median(min_hops))+";"+str(statistics.mean(min_hops))+";"+str(statistics.stdev(min_hops))+"\n")
        sink_report_file.write("Latency"+";"+str(statistics.median(latency))+";"+str(statistics.mean(latency))+";"+str(statistics.stdev(latency))+"\n")
        sink_report_file.write("Eficiency"+";"+str(self.eficiency * 100)+"\n")
        sink_report_file.write("Total created"+";"+str(self.total_sent)+"\n")
        sink_report_file.write("Total delivered"+";"+str(self.total_sink)+"\n")  
        print("Median repeated: " + str(statistics.median(repeated)) +  " Std dev: " + str(statistics.stdev(repeated)))
        print("Median max_hops: " + str(statistics.median(max_hops)) +  " Std dev: " + str(statistics.stdev(max_hops)))
        print("Median min_hops: " + str(statistics.median(min_hops)) +  " Std dev: " + str(statistics.stdev(min_hops)))
        #print(final_report)
        sink_report_file.write("\n")
        sink_report_file.write("Node"+";"+"Max_Hops"+";"+"Min_hops"+"\n")
        for i in range(len(final_report)): #check if it's a new node
            sink_report_file.write(final_report[i][0]+";"+str(final_report[i][1])+";"+str(final_report[i][2])+";"+str(final_report[i][3])+"\n")
        sink_report_file.close()

    def node_stats(self):
        mess_reports = []
        got = False
        motes = {}
        motes_sender = {}
        sinks = {}
        node_final_report = {}
        final_report = []
        node_messages_sent = []
        node_messages_received = []
        total_received_mess = {}
        print("Preparing node stats report on folder: " + self.folder)
        for (dirpath, dirnames, filenames) in os.walk(self.folder+"/message_dumps"):
            mess_reports.extend(filenames)
            break
        for node in mess_reports:
            node_data=node.split("_")
            if (node_data[0]=="node"):
                motes[node_data[3]]=node
            if (node_data[3]=="mote"):
                motes_sender[node_data[2]]=node
            elif (node_data[3]=="sink"):
                sinks[node_data[2]]=node
        #print(motes_sender)
        print("Reading delivered messages at " + str(len(motes)) + " nodes")
        for node_receiver, node_dump_report in motes.items():
            node_report = open(self.folder+"/message_dumps/"+node_dump_report).readlines()
            total_received_mess[node_receiver] = node_report
        #loop all senders
        for node_sender, node_sender_report in motes_sender.items():
            node_sent = open(self.folder+"/message_dumps/"+node_sender_report).readlines()
            #record all sent messages for that sender
            for message_sent in node_sent:
                node_messages_sent.append(message_sent.split(";"))
            #loop all receivers
            for node_receiver, messages_received in total_received_mess.items():
                #record all received for that receiver
                for message_received in messages_received:
                    node_messages_received.append(message_received.split(";"))
                #for the current sender, loop all sent messages
                for i in range(1,len(node_messages_sent)):
                    #print(node_messages_sent[i])
                    #for current receiver loop received messsages
                    for j in range(1,len(node_messages_received)):
                        #has the current receiver got the sent message?
                        if (node_messages_sent[i][0] == node_messages_received[j][0]):
                            got = True
                    if got == True:
                        if (len(node_messages_sent[i])==3):
                            node_messages_sent[i][2] += 1
                        else:
                            node_messages_sent[i].append(1)
                    got = False
                #print(node_messages_sent)
                node_messages_received = []
            for msg in node_messages_sent:
                #print(msg)
                try:
                    final_report.append(msg[2])
                except:
                    final_report.append(0)
            delivery = statistics.mean(final_report)
            node_final_report[node_sender] = delivery
            final_report = []
            node_messages_sent = []
        node_report_file = open(self.folder+"/nodes_delivery_report"+".csv","w")
        for node, distribution in node_final_report.items():
            node_report_file.write(node+";"+str(distribution)+ ";" + str( (distribution/(len(motes)-1)) * 100) +"\n")  
            #print(node_final_report)
        node_report_file.close()

    def net_long(self):
        mess_reports = []
        motes = {}
        sinks = {}
        total_sent = 0
        print("Preparing net longevity report on folder: " + self.folder)
        for (dirpath, dirnames, filenames) in os.walk(self.folder+"/message_dumps"):
            mess_reports.extend(filenames)
            break
        #print(mess_reports)
        for node in mess_reports:
            node_data=node.split("_")
            #print(node_data)
            if (node_data[3]=="mote"):
                motes[node_data[2]]=node
            elif (node_data[3]=="sink"):
                sinks[node_data[2]]=node
        #print(sinks)
        final_report = []
        sink_messages = []
        print("Reading delivered messages from " + str(len(sinks)) + " sinks")
        for sink, sink_report in sinks.items():
            sinkfile = open(self.folder+"/message_dumps/"+sink_report).readlines()
            for sink_mess in sinkfile:
                sink_messages.append(sink_mess.split(";")[0])
                #sink_messages.append(sink_mess[0])
        print (str(len(sink_messages)) + " Messages were delivered")
        #sys.exit() 
        for mote, report in motes.items():
            print("Reading " + report)
            logfile = open(self.folder+"/message_dumps/"+report).readlines()
            messages_sent = []
            for i in range(1,len(logfile)):
                messages_sent.append(logfile[i].split(";"))
                #print(len(messages_sent))
            total_sent += len(messages_sent)
            print("Read " + str(len(messages_sent)) + " messages")
            print("First pass....counting messages sent at each timestamp")
            #print(messages_sent[0])
            #break
            #first pass
            for item in range(0,len(messages_sent)):
                if len(final_report) > 0:
                    for element in range(0,len(final_report)): #check if it's a new timestamp
                        try:
                            if final_report[element][0] == math.floor(int(messages_sent[item][1])/self.t)*self.t: #we already this timestamp
                                #print("Aqui!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                                final_report[element][1] += 1 #increment counter
                                not_added = False
                                break
                            else: #new message
                                not_added = True
                        except:
                            print(messages_sent[item])
                else: #fresh list, add directly
                    not_added = True
                if not_added:
                    #print(item)
                    #print(int(messages_sent[item][1]))
                    final_report.append([math.floor(int(messages_sent[item][1])/self.t)*self.t,1,0])
            #second pass
            print("Second pass....counting messages received at each timestamp")
            for item in range(0,len(messages_sent)): #loop sent messages
                for delv_mess in range(0,len(sink_messages)): #loop delivered messages
                    if messages_sent[item][0] == sink_messages[delv_mess]: #if message was delivered
                        for j in range(0,len(final_report)): #loop final report
                            if final_report[j][0] == math.floor(int(messages_sent[item][1])/self.t)*self.t: #find time self.t to increment
                                final_report[j][2] += 1
                        #print(final_report.index(int(messages_sent[item][1])))
                        #sys.exit()
        self.eficiency = len(sink_messages) / total_sent
        self.total_sent = total_sent
        self.total_sink = len(sink_messages)
        final_report_file = open(self.folder+"/net_longevity_report"+".csv","w")
        for line in final_report:
            final_report_file.write(str(line[0])+";"+str(line[1])+";"+str(line[2])+"\n")
        final_report_file.close()
        #sys.exit()

    def nodes_plot(self):
        input_file_nodes = open(self.folder+"/nodes_report.csv","r").readlines()
        nodes = []
        simul_total_time = []
        commutations = []
        comm_energy = []
        comp_energy = []
        sensor_energy = []
        sleep_energy = []

        for line in input_file_nodes:
            line = line.split(";")
            if (line[5] == 'GOSSIP'):
                self.nodemode = line[5]
            elif (line[5] == 'MCFA'):
                self.nodemode = line[5]
            elif (line[5] == 'GOSSIPFO'):
                self.nodemode = line[5]
            else:
                self.nodemode = 'EAGP'
            if (line[0] != 'Node') and (int(line[9]) > 0):
                #print(line[0] + ' ' +line[0][4:])
                nodes.append(int(line[0][4:]))
                simul_total_time.append(int(line[2]))
                commutations.append(int(line[1]))
                comm_energy.append(float(line[13]))
                comp_energy.append(float(line[14]))
                sleep_energy.append(float(line[15]))
                sensor_energy.append(float(line[16]))

        plt.style.use('ggplot')
        if self.nodemode == 'EAGP':
            plt.title('Nodes Longevity\nTopology='+self.topo+' t='+str(self.t)+'s'+' TMAX= '+str(self.tmax/1000) + 's')
        else:
            plt.title('Nodes Longevity\nTopology='+self.topo+' t='+str(self.t)+'s')
        plt.xlabel('Node id')
        plt.ylabel('Time(s)')

        plt.bar(nodes, simul_total_time, 0.35,  label = 'Simulation time')

        plt.tight_layout()
        plt.savefig(self.folder+'/nodes_longevity.png')
        plt.close()

        plt.style.use('ggplot')
        if self.nodemode == 'EAGP':
            plt.title('Nodes Energy\nTopology='+self.topo+' t='+str(self.t)+'s'+' TMAX= '+str(self.tmax/1000) + 's')
        else:
            plt.title('Nodes Energy\nTopology='+self.topo+' t='+str(self.t)+'s')
        plt.xlabel('Node id')
        plt.ylabel('Energy (J)')

        plt.bar(nodes, comm_energy, 0.35, label = 'Comp. Energy')
        plt.bar(nodes, comp_energy, 0.35, bottom=comm_energy, label = 'Comm. Energy')
        #plt.bar(nodes, sensor_energy, 0.35, bottom=comm_energy, label = 'Sensor Energy')
        #plt.bar(nodes, sleep_energy, 0.35, bottom=sensor_energy, label = 'Sleep Energy')

        #ax2 = plt.twinx()
        #color = 'tab:blue'
        #ax2.set_ylabel('sin', color=color)
        #ax2.scatter(nodes, simul_total_time, color=color)
        #ax2.tick_params(axis='y', labelcolor=color)

        plt.tight_layout()
        plt.legend()
        plt.xticks(np.arange(0, len(nodes)+1, 2))
        plt.savefig(self.folder+'/nodes_energy.png')
        plt.close()

    def final(self):
        final_report = []
        sink_report = []
        energy = 0.0
        sink_report_file = open(self.folder+"/sink_report"+".csv").readlines()
        node_report_file = open(self.folder+"/nodes_report"+".csv").readlines()
        final_report_file = open(self.folder+"/final_report"+".csv","w")
        for line in sink_report_file:
            data = line.split(";")
            sink_report.append(data)
        for node in range(1,len(node_report_file)):
            data = node_report_file[node].split(";")
            if int(data[9]) > 0:
                energy += float(data[13]) + float(data[14])
        final_report.append(["COMM/COMP (J)",energy,"\n"])
        final_report.append(["# of repeated packets",sink_report[1][2],"\n"])
        final_report.append(["Avg. Max hops",sink_report[2][2],"\n"])
        final_report.append(["Avg. Min hops",sink_report[3][2],"\n"])
        final_report.append(["Latency (s)",sink_report[4][2],"\n"])
        final_report.append(["Delivery Efficiency %",sink_report[5][1],""])
        final_report.append(["Total packet created",sink_report[6][1],""])
        final_report.append(["Total packet delivered",sink_report[7][1],""])
        #print(final_report)
        for line in final_report:
            final_report_file.write(str(line[0]) + ";" + str(line[1])+ str(line[2]))
        final_report_file.close()

    def movingaverage(self,interval, window_size):
        window = np.ones(int(window_size))/float(window_size)
        return np.convolve(interval, window, 'same')

    def net_long_plot(self):
        time = []
        sent = []
        received = []
        death_time = 0

        input_file = open(self.folder+"/net_longevity_report.csv","r").readlines()

        for line in input_file:
            line = line.split(";")
            time.append(int(line[0]))
            sent.append(int(line[1]))
            received.append(int(line[2]))

        time, sent, received = (list(t) for t in zip(*sorted(zip(time, sent, received))))

        for i in range(int(len(received)/2), len(received)): #skip first half os simulation
            qos = (received[i] / sent [i])*100
            if qos < self.qos_collapse:
                death_time = i
                break

        death_time = len(received)
        cx = time[death_time-1]
        cy = received[death_time-1]
        print('The last received message was created at:' + str(cx))

        #print("Time: " + str(time[i]) + " got: " + str(received[i]))
        #print(plt.style.available)
        #plt.style.use('seaborn-deep')
        plt.style.use('ggplot')
        if self.nodemode == 'EAGP':
            plt.title('Network Longevity\nTopology='+self.topo+' TMAX= '+str(self.tmax/1000) + 's')
        else:
            plt.title('Network Longevity\nTopology='+self.topo)
        plt.xlabel('Time(s)')
        plt.ylabel('Number of Messages')

        #trend = np.polyfit(time, sent, 4)
        ma_sent= self.movingaverage(sent,4)
        ma_recv= self.movingaverage(received,4)
        #p = np.poly1d(trend)

        plt.scatter(time,sent, s=1)
        plt.scatter(time,received, s=1.5)
        plt.plot(time,ma_sent, label = 'Sent')
        plt.plot(time,ma_recv, label = 'Received')

        #plt.annotate('Collapsed in \nt= ' + str(time[death_time-1]) + ' s', xy = (cx,cy), ha="right", xytext=(cx-10000, max(received)/2), arrowprops=dict(facecolor='black', shrink=0.05),bbox=dict(boxstyle="round4", fc="w"))

        #plt.xticks(np.arange(min(time), max(time)+1, max(time)/10))
        #plt.xticks(np.arange(0, 7000, 500))
        plt.xticks(np.arange(0, 11000, 1000))
        plt.legend()

        plt.tight_layout()
        plt.savefig(self.folder+'/net_longevity.png')
        plt.close()

        #plt.plot(time,sent, '^b-' ,linewidth = 1 ,label = 'Sent')
        #plt.plot(time,received, color='#5a7d9a', linestyle='-', marker='.', linewidth = 3 ,label = 'Received')
        #plt.grid(True)
        #print(time)
        #plt.imshow(a, cmap='hot', interpolation='nearest')
        #plt.show()

if __name__ == '__main__':  #for main run the main function. This is only run when this main python file is called, not when imported as a class
    print("Ourocrunch - Report generator for Ouroboros")
    print()
    folders = []
    sorted_folders = []
    parser = argparse.ArgumentParser(description='Options as below')
    parser.add_argument('indir', type=str, help='Input dir where reports are located')
    parser.add_argument('-t','--type', type=str, help='type of report', default="long", choices=['long', 'implosion'])
    parser.add_argument('-a','--all', help='process all report folders', dest='all', action='store_true')
    parser.add_argument('-l','--last', help='process last report folder', dest='last', action='store_true')
    parser.add_argument('-d','--date', help='date/time to be processed', dest='date', type=str, default=False)
    arguments = parser.parse_args()

    for (dirpath, dirnames, filenames) in os.walk(arguments.indir):
        folders.extend(dirnames)
        break

    for folder in folders:
        if folder!='EAGP' and folder!='GOSSIP' and folder!='MCFA':
            sorted_folders.append(folder)
    sorted_folders = sorted(sorted_folders)

    if (arguments.last == True):
        folder = arguments.indir+'/'+sorted_folders[len(sorted_folders)-1]
        report = Report(folder)
        #print(path+'/'+folders[len(folders)-1])
    elif (arguments.all == True):
        for simulation in sorted_folders:
            folder = arguments.indir+'/'+simulation
            #print(folder)
            if simulation!='EAGP' or simulation!='GOSSIP' or simulation!='MCFA':
                report = Report(folder)
                pass
    elif (arguments.date != False):
        for simulation in sorted_folders:
            if (simulation == arguments.date):
                folder = arguments.indir+'/'+simulation
                #print(path+'/'+simulation)
                report = Report(folder)
    sys.exit()
