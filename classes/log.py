#!/usr/bin/env python3.7

""" 
Prompt class is part of a dissertation work about WSNs 
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

import os, struct, sys, traceback, time

class Log:

    def __init__(self, node, tag, role, board_type, topology, protocol):
        self.simdir = str(time.localtime().tm_year) + "_" + str(time.localtime().tm_mon) + "_" + str(time.localtime().tm_mday) + "_" + str(time.localtime().tm_hour) + "_" + str(time.localtime().tm_min)
        try:
            os.mkdir("reports/" + self.simdir)
            os.mkdir("reports/" + self.simdir + "/message_dumps")
            os.mkdir("reports/" + self.simdir + "/finished")
        except FileExistsError:
            print("Report folder already created.")
        except:
            traceback.print_exc()
        self.logfile = open("reports/" + self.simdir + "/" + "sim_report_"+tag+"_"+role+"_"+str(node.sleep_s)+"_"+board_type+"_" + topology + "_" + protocol + "_" + time.asctime(time.localtime())+".csv","w") #
        self.msgfile = open("reports/" + self.simdir + "/" + "message_dumps/message_dump_"+tag+"_"+role+"_"+str(node.sleep_s)+"_"+time.asctime(time.localtime())+".csv","w") #
        if node.role != "sink":
            self.nodefile = open("reports/" + self.simdir + "/" + "message_dumps/node_dump_"+tag+"_"+str(node.sleep_s)+"_"+time.asctime(time.localtime())+".csv","w") #
        self.logfile.write('Simul. Seconds;Battery %; Average Energy; Mode; Neighbours; Tmax; Tnext; Created; Forwarded; Delivered; Discarded; Comp Energy; Comm Energy; Sleep Energy; Sensor Energy; X; Y; Buffer; Message Log; Traffic\n')
        self.logfile.flush()

    def print_error(self,text):
        'Print error message with special format'
        print()
        print("\033[1;31;40m"+text+"  \n")
        print("\033[0;37;40m")

    def print_alert(self,text):
        'Print alert message with special format'
        print()
        print("\033[1;32;40m"+text+"  \n")
        print("\033[0;37;40m")

    def printxy(self,x, y, text):
        sys.stdout.write("\x1b7\x1b[%d;%df%s\x1b8" % (x, y, text))
        sys.stdout.flush()

    def datalog(self, node):
        'Dataloger writes current data to node log'
        jobs = 0
        try:
            jobs = len(node.scheduler.get_jobs())
        except:
            pass
        self.logfile.write(str(node.simulation_seconds)+";"
                    +"{0:5.2f}".format(node.Battery.battery_percent)+";"
                    +"{0:5.2f}".format(node.Network.average)+";"
                    +node.Network.mode+";"
                    +str(len(node.Network.visible))+";"
                    +str(node.Network.tmax/node.multiplier)+";"
                    +str(node.Network.tnext/node.multiplier)+";"
                    +str(node.Network.protocol_stats[0])+";"
                    +str(node.Network.protocol_stats[1])+";"
                    +str(node.Network.protocol_stats[2])+";"
                    +str(node.Network.protocol_stats[3])+";"
                    +str(node.Battery.computational_energy)+";"
                    +str(node.Battery.communication_energy)+";"
                    +str(node.Battery.sleeping_energy)+";"
                    +str(node.Battery.sensor_reading_energy)+";"
                    +str(node.x)+";"
                    +str(node.y)+";"
                    +str(jobs)+";"
                    +str(len(node.Network.messages))+";"
                    +str(node.Network.traffic)+";"
                    +"\n")
        self.logfile.flush()

    def log_messages(self, node):
        'Dumps all shared messages to file'
        if node.role == "sink":
            self.msgfile.write('Msg ID;Sender;Created at;Delivered at;Counter;Max Hops;Min Hops\n')
            for item in range(len(node.Network.messages_delivered)):
                self.msgfile.write(str(node.Network.messages_delivered[item][0])+";"
                            +node.Network.messages_delivered[item][1]+";"
                            +str(node.Network.messages_delivered[item][2])+";"
                            +str(node.Network.messages_delivered[item][3])+";"
                            +str(node.Network.messages_delivered[item][4])+";"
                            +str(node.Network.messages_delivered[item][5])+";"
                            +str(node.Network.messages_delivered[item][6])+"\n")
                self.msgfile.flush()
        else:
            self.msgfile.write('Msg ID;Created at\n')
            for item in range(len(node.Network.messages_created)):
                self.msgfile.write(str(node.Network.messages_created[item][0])+";"
                            +str(node.Network.messages_created[item][1])+"\n")
                self.msgfile.flush()
            self.nodefile.write('Msg ID;Sender;Created at;Delivered at;Counter;Max Hops;Min Hops\n')
            for item in range(len(node.Network.messages)):
                self.nodefile.write(str(node.Network.messages[item][0])+";"
                            +node.Network.messages[item][1]+";"
                            +str(node.Network.messages[item][2])+";"
                            +str(node.Network.messages[item][3])+";"
                            +str(node.Network.messages[item][4])+";"
                            +str(node.Network.messages[item][5])+";"
                            +str(node.Network.messages[item][6])+"\n")
                self.nodefile.flush()

    def clean_nodedumps(self, node):
        'Clean node dumps before new simulation'
        if node.role == "sink":
            print('Removing old node dumps')
            path ="./node_dumps" 
            files = []
            for (dirpath, dirnames, filenames) in os.walk(path):
                files.extend(filenames)
                break
            for dump in files:
                os.remove(path+'/'+dump)
            path ="./message_dumps" 
            files = []
            for (dirpath, dirnames, filenames) in os.walk(path):
                files.extend(filenames)
                break
            for dump in files:
                os.remove(path+'/'+dump)
