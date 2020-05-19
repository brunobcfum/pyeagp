#!/usr/bin/env python3.7

""" 
Router class is part of a dissertation work about WSNs 
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

import socket, os, math, struct, sys, json, traceback, zlib, fcntl, threading, time, random

class Network():

    def __init__(self, Node, Battery, port=56123, tmax = 100, net_trans = 'ADHOC'):
        'Initializes the properties of the Node object'
        #### SENSOR ###############################################################################
        self.Node = Node
        self.visible = [] #our visibble neighbours
        self.messages_created = [] #messages created by each node
        self.messages_delivered = [] #messages delivered at the sink
        self.messages = []
        self.average = 0
        self.visible_timeout = 3 * (Node.sleeptime / 1000) #timeout when visible neighbours should be removed from list in ms
        #### NETWORK ##############################################################################
        self.net_trans = net_trans #adhoc or sixLoWPANLink
        #print(self.net_trans)
        if self.net_trans == 'ADHOC':
            self.bcast_group = '10.0.0.255' #broadcast ip address
        elif self.net_trans == 'SIXLOWPANLINK':
            self.bcast_group = 'ff02::1'
        self.port = port # UDP port
        self.max_packet = 65535 #max packet size to listen
        #### UTILITIES ############################################################################
        self.monitor_mode = False #when this is true a lot of messages polute the screen
        self.protocol_stats = [0,0,0,0] #created, forwarded, delivered, discarded
        self.errors = [0,0,0]
        self.myip = ''
        #### Protocol specific ####################################################################
        if self.Node.role == 'sink':
            self.cost = 0
            self.state = 'ADV'
        else:
            self.cost = 100000000
            self.state = 'BACKOFF'
        self.backoff = 1000
        self.boc = 5 #backoff constant
        self.backoff_timer = 0
        self.adv_counter = 2
        # this is here just for compatibility
        self.tnext = 100000000
        self.tmax = tmax * self.Node.second
        self.tSinkCurrent = 0
        self.tSinkMax = 30 * self.Node.sleep_s
        self.visible = []
        self.mode = "MCFA"
        self.netRatio = 0
        self.packets = 0
        self.traffic = 0
        self.ttl = 16
        ##################### END OF DEFAULT SETTINGS ###########################################################
        self._setup() #Try to get settings from file
        self.t2 = threading.Thread(target=self._listener, args=())
        self.t2.start()

    ############### Public methods ###########################
    def awake_callback(self):
        try: 
            self.netRatio = self.protocol_stats[3] / self.protocol_stats[1]
        except:
            self.netRatio = 1
        if (self.state=="ADV"):
            self._adv()
        elif (self.state=="BACKOFF"):
            if (self.Node.simulation_seconds-self.backoff_timer > self.backoff):
                self.print_alert("Going to ADV")
                print(self.Node.prompt_str)
                self.state = "ADV"
        elif (self.state=="RUNNING"):
            if (self.Node.role == "sink"):
                self._checkNewMessage()

    def dispatch(self, payload):
        if (self.state=="RUNNING"):
            self._sender(payload)

    def shutdown(self):
        self.t2.join(timeout=2)
    
    ############### Private methods ##########################

    def _adv(self):
        'Sends a bradcast message to advertize itself ot the neighbours'
        start = time.monotonic_ns()/1000000
        #this adv is like a radar ping, trying to find other friends in the ether
        addrinfo = socket.getaddrinfo(self.bcast_group, None)[1] 
        #getting the first one [0] is related to stream, [1] dgram and [2] raw
        #addrinfo[0] is the address family, which is same for stream dgram ow raw
        adv_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        adv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if (self.net_trans=='SIXLOWPANLINK'):
            ttl_bin = struct.pack('@i', 1) #ttl=1
            adv_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        bytes_to_send = json.dumps([1 , self.Node.tag, self.cost]).encode()
        adv_socket.sendto(bytes_to_send, (self.bcast_group, self.port))
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start, self.Node.Battery.tx_time * self.Node.Battery.tx_current)
        adv_socket.close()
        if (self.adv_counter == 0) and (self.state == "ADV"):
            self.print_alert("Going to RUNNING")
            print(self.Node.prompt_str)
            self.state = "RUNNING"
        else:
            self.adv_counter -= 1

    def _adv_handler(self, payload, sender_ip):
        'When a beacon is received from a neighbour this method opens the packet and handles it'
        start = time.monotonic_ns()/1000000
        if (payload[1] != self.Node.tag):
            if (self.cost) > payload[2] + 1:
                self.cost = payload[2] + 1
                self.backoff = self.boc * self.cost
                self.backoff_timer = self.Node.simulation_seconds
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(0, start, self.Node.Battery.rx_current * self.Node.Battery.rx_time)
        self.Node.Battery.computational_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start)

    def _listener(self):
        'This method opens a UDP socket to receive data. It runs in infinite loop as long as the node is up'
        addrinfo = socket.getaddrinfo(self.bcast_group, None)[1]
        listen_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM) #UDP
        listen_socket.bind(('', self.port))
        self.myip = self._get_ip('eth0')
        if (self.net_trans=='SIXLOWPANLINK'):
            group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
            mreq = group_bin + struct.pack('@I', 0)
            listen_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
        while self.Node.lock: #this infinity loop handles the received packets
            payload, sender = listen_socket.recvfrom(self.max_packet)
            payload = json.loads(payload.decode())
            sender_ip = str(sender[0])
            self.packets += 1
            if (payload[0]==1): #we got a adv!
                if self.monitor_mode: print("I am in state:" + self.state + " and got a ADV")
                if (self.state == "BACKOFF"):
                    self._adv_handler(payload, sender_ip)
            elif (payload[0]==2): #we got a data!
                if self.monitor_mode: 
                    print("I am in state:" + self.state + " and got a DATA")
                if (self.state == "RUNNING"):
                    self._data_handler(payload, sender_ip)
        listen_socket.close()

    def _sender(self, value):
        'This method sends an epidemid message with the data read by the sensor'
        start = time.monotonic_ns()/1000000
        addrinfo = socket.getaddrinfo(self.bcast_group, None)[1] 
        #getting the first one [0] is related to stream, [1] dgram and [2] raw
        #addrinfo[0] is the address family, which is same for stream dgram ow raw
        sender_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        if (self.net_trans=='SIXLOWPANLINK'):
            ttl_bin  = struct.pack('@i', 1) #ttl=1
            sender_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        elif (self.net_trans=='ADHOC'):
            sender_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg_id = zlib.crc32(str((self.Node.simulation_seconds+value)).encode())
        self.messages_created.append([hex(msg_id),self.Node.simulation_seconds])
        bytes_to_send = json.dumps([2 , hex(msg_id), self.Node.tag, value, self.Node.simulation_seconds, 0, self.cost]).encode()
        sender_socket.sendto(bytes_to_send, (addrinfo[4][0], self.port))
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start, self.Node.Battery.tx_time * self.Node.Battery.tx_current)
        sender_socket.close()

    def _data_handler(self, payload, sender_ip):
        payload[5] += 1 # adds one hop
        'When a message of type gossip is received from neighbours this method unpacks and handles it'
        start = time.monotonic_ns()/1000000
        if (payload[2] != self.Node.tag):
            if (self.Node.role == "sink"):
                self._sink(payload)
            else:
                self._node_message(payload)
                if(payload[5]+self.cost == payload[6]):
                    self._forwarder(payload)
                    if self.monitor_mode:
                        print(time.asctime(time.localtime())+ " Got a data: "+payload[1])
                else:
                    self.protocol_stats[3] += 1
                    if self.monitor_mode:
                        print(time.asctime(time.localtime())+ " Got a bad data: "+str(payload))
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(0, start, self.Node.Battery.rx_current * self.Node.Battery.rx_time)
        self.Node.Battery.computational_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start)

    def _sink(self, payload):
        'This should be in app layer'
        # This method does not use energy, only for simulation statistics
        if len(self.messages_delivered) > 0: 
            for element in range(len(self.messages_delivered)): #check if it's a new message
                if self.messages_delivered[element][0] == payload[1]: #we already delivered that one
                    self.messages_delivered[element][4] += 1 #increment counter
                    if (payload[5]>self.messages_delivered[element][5]): #calculate max and min hops
                        self.messages_delivered[element][5]=payload[5]
                    elif (payload[5]<self.messages_delivered[element][6]):
                        self.messages_delivered[element][6]=payload[5]
                    self.protocol_stats[2] += 1
                    not_delivered = False
                    break
                else: #new message
                    not_delivered = True
        else: #fresh list, add directly
            not_delivered = True
            #print("I'm a sink and got a message to dispatch")
        if not_delivered:
            self.messages_delivered.append([payload[1],payload[2],payload[4],self.Node.simulation_seconds,1,payload[5],payload[5]]) #add with counter 1
            self.protocol_stats[2] += 1
            self.tSinkCurrent = 0

    def _node_message(self, packet):
        if len(self.messages) > 0: 
            for element in range(len(self.messages)): #check if it's a new message
                if self.messages[element][0] == packet[1]: #we already delivered that one
                    self.messages[element][4] += 1 #increment counter
                    if (packet[5]>self.messages[element][5]): #calculate max and min hops
                        self.messages[element][5]=packet[5]
                    elif (packet[5]<self.messages[element][6]):
                        self.messages[element][6]=packet[5]
                    not_delivered = False
                    break
                else: #new message
                    not_delivered = True
        else: #fresh list, add directly
            not_delivered = True
        if not_delivered:
            self.messages.append([packet[1],packet[2],packet[4],self.Node.simulation_seconds,1,packet[5],packet[5]]) #add with counter 1

    def _forwarder(self, msg):
        'This method forwards a received gossip package to all neighbours'
        'This should be in routing layer'
        start = time.monotonic_ns()/1000000
        addrinfo = socket.getaddrinfo(self.bcast_group, None)[1] #getting the first one [0] is related to stream, [1] dgram and [2] raw
        #addrinfo[0] is the address family, which is same for stream dgram ow raw
        forwarder_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        if (self.net_trans=='SIXLOWPANLINK'):
            ttl_bin = struct.pack('@i', 1) #ttl=1
            forwarder_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        elif (self.net_trans=='ADHOC'):
            forwarder_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        bytes_to_send = json.dumps([2 , msg[1], msg[2], msg[3], msg[4], msg[5], msg[6]]).encode()
        forwarder_socket.sendto(bytes_to_send, (addrinfo[4][0], self.port))
        self.protocol_stats[1] += 1
        forwarder_socket.close()
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start, self.Node.Battery.tx_time * self.Node.Battery.tx_current)

    def _checkNewMessage(self):
        #this is for sink only
        if (self.tSinkCurrent > self.tSinkMax): #max time withtout new message. Shutdown simulation
            self.Node.lock = False

    def printinfo(self):
        'Prints general information about the node'
        print()
        print("MCFA - Routing agent")
        print()
        print("node state:\t\t"+self.state)
        print("battery level: \t\t{0:5.2f} Joules".format(self.Node.Battery.battery_energy))
        print("battery level: \t\t{0:5.2f} %".format(self.Node.Battery.battery_percent))
        print("local address: \t\t"+str(self.myip))
        print("udp port: \t\t"+str(self.port))
        print("backoff: \t\t" + str(self.backoff/self.Node.multiplier)+ " ms in virtual time")
        print("backoff time: \t\t" + str(self.backoff_timer/self.Node.multiplier)+ " ms in virtual time")
        if self.Node.role == 'mote':
            print("msgs created: \t\t"+str(self.protocol_stats[0]))
            print("msgs forwarded: \t"+str(self.protocol_stats[1]))
            print("msgs discarded: \t"+str(self.protocol_stats[3]))
        elif self.Node.role == 'sink':
            print("msgs delivered: \t"+str(self.protocol_stats[2]))
            print("starvation time: \t"+str(self.tSinkCurrent))
            print("starvation max: \t"+str(self.tSinkMax))
        print("Network ratio: \t\t"+str(self.netRatio))
        print("My cost: \t\t"+str(self.cost))
        print()
        print("Network ratio is just the number of discarded messages divided by")
        print("the number of created messages. A node with high ratio is busier.")
        print()

    def print_msg_table(self):
        print("Message table")
        print("=========================================================")
        print("|                     Message ID                        |")
        print("---------------------------------------------------------")
        for member in range(len(self.messages_created)):
            print ("| "+self.messages_created[member][0]+" \t\t|")
        print("=========================================================")

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

    def _get_ip(self,iface = 'eth0'):
        'This should be in routing layer'
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockfd = sock.fileno()
        SIOCGIFADDR = 0x8915
        ifreq = struct.pack('16sH14s', iface.encode('utf-8'), socket.AF_INET, b'\x00'*14)
        try:
            res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
        except:
            traceback.print_exc()
            return None
        ip = struct.unpack('16sH2x4s8x', res)[2]
        return socket.inet_ntoa(ip)

    def _setup(self):
        settings_file = open("settings.json","r").read()
        settings = json.loads(settings_file)
        self.tSinkMax = settings['sink_starvation'] 
        self.ttl = settings['ttl']

