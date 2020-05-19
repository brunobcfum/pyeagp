#!/usr/bin/env python3.7

""" 
Node class is part of a dissertation work about WSNs 
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.9"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

import socket, os, math, random, struct, sys, json, traceback, zlib, fcntl, time
#My classes
from classes import networkEAGPD, networkGossip, networkMCFA, networkGossipFanout, battery

class Node:

    def __init__(self, energy_model, tag='node', role='mote', multiplier = 1, x=0, y=0, batlim=100, net_trans='ADHOC', protocol='EAGP', tmax=100):
        'Initializes the properties of the Node object'
        random.seed(tag)
        ##################### DEFAULT SETTINGS ###########################################################
        self.lock  = True # when this is false the simulation stops
        self.stop = False
        self.prompt_str = tag + "#>"
        #### Simulation specific ##################################################################
        self.multiplier = multiplier #time multiplier for the simulator
        self.second = 1000 * self.multiplier #duration of a second in ms // this is the simulation second
        #### SENSOR ###############################################################################
        self.role = role #are we a mote or a sink?
        self.tag = tag #the name of the sensor
        self.value = 0 # this is the sensor read value
        self.sleep_s = 15 + (random.random()*35) #seconds
        self.status = "AWAKE" #current status sleep/awake
        self.sleeptime = self.sleep_s * self.second #time between sensor reads in ms
        self.x = x
        self.y = y
        #### UTILITIES ############################################################################
        self.simulation_seconds = 0 # this is the total time spent in the simulation time
        self.simulation_tick_seconds = 0 # this is the total time spent in real world time
        ##################### END OF DEFAULT SETTINGS ###########################################################
        self.setup() #Try to get settings from file
        self.Battery = battery.Battery(batlim, role, energy_model) #create battery object
        if protocol == 'EAGP':
            self.Network = networkEAGPD.Network(self, self.Battery, 56123, tmax, net_trans) #create network object        
        elif protocol == 'GOSSIP':
            self.Network = networkGossip.Network(self, self.Battery, 56123, tmax, net_trans) #create network object
        elif protocol == 'GOSSIPFO':
            self.Network = networkGossipFanout.Network(self, self.Battery, 56123, tmax, net_trans) #create network object
        elif protocol == 'MCFA':
            self.Network = networkMCFA.Network(self, self.Battery, 56123, tmax, net_trans) #create network object
        else:
            print("invalid protocol...quitting")
            os._exit(1)

    def sensor_read(self):
        #simulate reading sensor
        start = time.monotonic_ns()/1000000
        self.value = random.random()*100
        #self.computational_energy += self.battery_drainer(self.modemSleep_current, start, self.sensor_energy)
        self.Battery.sensor_reading_energy += self.Battery.battery_drainer(self.Battery.modemSleep_current, start, self.Battery.sensor_energy)
        self.Network.dispatch(self.value)
        self.Network.protocol_stats[0] += 1

    def awake(self):
        #do my work
        self.status = "AWAKE"
        self.Network.awake_callback()#tells Network that I'awake. In real hardware that would be an interrupt
        if (self.role!="sink"):
            self.sensor_read() #read new sensor value
          
    def sleep(self):
        #sleep
        self.status = "SLEEP" 
        self.Battery.sleeping_energy += self.Battery.battery_drainer(0, 0 , self.Battery.modemSleep_current * (self.sleep_s / 3600)) #using sleep = awake energy for now

    def printinfo(self):
        'Prints general information about the node'
        print()
        print("Simulated node")
        print("nodename:\t\t"+self.tag)
        print("node role:\t\t"+self.role)
        #print("current value: \t\t{0:5.2f}".format(self.value))
        print("vsleep time: \t\t{0:5.2f}".format(self.sleeptime/self.multiplier)+ " ms in virtual time")
        #print("rsleep time: \t\t{0:5.2f}".format(self.sleeptime)+ " ms in real time")
        print("elapsed time: \t\t" + str(self.simulation_seconds)+ " s in virtual time")
        print("elapsed time: \t\t" + str(self.simulation_tick_seconds)+ " s in real time")
        print("position: \t\t" + str(self.x) + ',' + str(self.y))
        print()

    def setup(self):
        settings_file = open("settings.json","r").read()
        settings = json.loads(settings_file)
        self.sleep_s = settings['base_sleep_time_s'] + (random.random()*35) 

    def shutdown(self):
        self.Network.shutdown()
        self.Battery.shutdown()
