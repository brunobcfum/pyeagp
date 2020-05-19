#!/usr/bin/env python3.7

""" 
Prompt class is part of a dissertation work about WSNs 
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.2"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

import os, struct, sys, traceback, threading, time, readline
from collections import deque

class Prompt:

    def __init__(self, node):
        self.lock=True
        self.history = deque([],10) #logbook of all messages received
        self.history_pos = 0
        pass

    def prompt(self,node):
        'Simple command prompt * Maybe can be changed to use a prompt lib for better functionallity'
        try:
            while self.lock==True:
                inp = input(node.prompt_str)
                command = inp.split()
                self.history.append(command)
                if (len(command))>=1:
                    if command[0] == 'help':
                        self.printhelp()
                    elif command[0] == 'clear':
                        print("\033c")      
                    elif command[0] == 'visible':
                        try:
                            node.Network.printvisible() 
                        except:
                            self.print_alert('Nothing to show')
                            pass
                    elif command[0] == 'info':
                        node.printinfo()
                    elif command[0] == 'network':
                        node.Network.printinfo() 
                    elif command[0] == 'battery':
                        node.Battery.printinfo()    
                    elif command[0] == 'buffer':
                        try:
                            node.Network.scheduler.print_jobs()
                        except:
                            self.print_alert("Not available with this router")
                    elif command[0] == 'backlog':
                        try:
                            print(node.Network.backlog)
                        except:
                            self.print_alert("Not available with this router")
                    elif command[0] == 'quit':
                        node.lock = False
                        node.shutdown()
                        sys.stdout.write('Quitting')
                        while True:
                            sys.stdout.write('.')
                            sys.stdout.flush()
                            time.sleep(1)
                    elif command[0] == 'msg':
                        node.Network.print_msg_table()
                    elif command[0] == 'monitor':
                        node.Network.monitor_mode = not node.Network.monitor_mode
                        if (node.Network.monitor_mode): 
                            self.print_alert("Monitor mode set to on")
                        elif (not node.Network.monitor_mode): 
                            self.print_alert("Monitor mode set to off")
                    else:
                        self.print_error("Invalid command!")
        except:
            traceback.print_exc()
            node.lock = False
            self.print_alert("Exiting!")

    def printhelp(self):
        'Prints help message'
        print()
        print("Routing agent")
        print()
        print("Interface commands: ")
        print()
        print("info      - Display general information about the node")
        print("network   - Display general information about the network")
        print("battery   - Display general information about the battery")
        print("visible   - Display the list of visible neighbours - EAGP Only")
        print("monitor   - Enable monitor mode")
        print("buffer    - Print buffer scheduler")
        print("clear     - Clear the display")
        print("help      - Diplay this help message")
        print("quit      - Exit the agent")
        print()


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

    def print_history(self,command,node):
        if command=='up':
            if len(self.history) > 0:
                try:
                    print(node.prompt+self.history[self.history_pos])
                except:
                    pass
            pass
        elif command=='down':
            pass