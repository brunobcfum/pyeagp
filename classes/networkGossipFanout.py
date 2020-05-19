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
        self.ttl = 16
        self.fanout_max = 3
        self.tmax = tmax * Node.second  # Maximum time interval a node can wait until send a message (milliseconds)
        self.tnext = self.tmax # The time interval the local node will wait until forwarding current message (in milliseconds)
        self.bt_level = [] # Battery level in node i (in a range between 1 and 10, where 1 means that remains less than 10% of battery)
        self.v_bt = [] #A vector containing the energy level of all neighbour nodes ## NOT NEEDED IN THIS IMPLEMENTATION
        self.mode = "GOSSIPFO" #
        self.netRatio = 0 # ratio -> forwarded / discarded
        self.tSinkMax = 500 #max time sink without new message, after that stop simulation
        self.tSinkCurrent = 0 #current time with no new message
        self.packets = 0
        self.traffic = 0
        self.battery_percent_old = 0
        ##################### END OF DEFAULT SETTINGS ###########################################################
        self._setup() #Try to get settings from file
        self.t2 = threading.Thread(target=self._listener, args=())
        self.t2.start()

    ############### Public methods ###########################
    def awake_callback(self):
        self._update_visible()
        try: 
            self.netRatio = self.protocol_stats[3] / self.protocol_stats[1]
        except:
            self.netRatio = 1
        if (self.Node.role=="sink"):
            self._checkNewMessage()

    def dispatch(self, payload):
        self._sender(payload)

    def shutdown(self):
        self.t2.join(timeout=2)
    
    ############### Private methods ##########################
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
            self._packet_handler(payload, sender_ip)
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
        bytes_to_send = json.dumps([2 , hex(msg_id), self.Node.tag, value, self.Node.simulation_seconds, self.ttl, '', [],0]).encode()
        sender_socket.sendto(bytes_to_send, (addrinfo[4][0], self.port))
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start, self.Node.Battery.tx_time * self.Node.Battery.tx_current)
        sender_socket.close()

    def _packet_handler(self, payload, sender_ip):
        'When a message of type gossip is received from neighbours this method unpacks and handles it'
        'This should be in routing layer'
        start = time.monotonic_ns()/1000000
        payload[5] -= 1
        payload[8] += 1
        if (payload[2] != self.Node.tag):
            if len(self.visible) > 0: #list no empty, check if already there
                not_there = 1
                for element in range(len(self.visible)):
                    if sender_ip == self.visible[element][0]: #if there...
                        self.visible[element][1] = self.Node.simulation_seconds # refresh timestamp
                        not_there = 0
                        break
                if not_there:
                    self.visible.append([sender_ip, self.Node.simulation_seconds, 0])
            else: #Empty neighbours list, add 
                self.visible.append([sender_ip, self.Node.simulation_seconds, 0])
            if self.Node.role == "sink":
                self._sink(payload)
            else:
                self._node_message(payload)
                if payload[5] <= 0:
                    self.protocol_stats[3] +=1
                elif payload[6] != self.myip:
                    if (self.myip in payload[7]) or (len(payload[7])==0):
                        payload[6] = sender_ip
                        self._forwarder(payload)
                else:
                    self.protocol_stats[3] +=1
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(0, start, self.Node.Battery.rx_current * self.Node.Battery.rx_time)
        self.Node.Battery.computational_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start)

    def _sink(self, payload):
        # This method does not use energy, only for simulation statistics
        if len(self.messages_delivered) > 0: 
            for element in range(len(self.messages_delivered)): #check if it's a new message
                if self.messages_delivered[element][0] == payload[1]: #we already delivered that one
                    self.messages_delivered[element][4] += 1 #increment counter
                    if (payload[8]>self.messages_delivered[element][5]): #calculate max and min hops
                        self.messages_delivered[element][5]=payload[8]
                    elif (payload[8]<self.messages_delivered[element][6]):
                        self.messages_delivered[element][6]=payload[8]
                    self.protocol_stats[2] += 1
                    not_delivered = False
                    break
                else: #new message
                    not_delivered = True
        else: #fresh list, add directly
            not_delivered = True
            #print("I'm a sink and got a message to dispatch")
        if not_delivered:
            self.messages_delivered.append([payload[1],payload[2],payload[4],self.Node.simulation_seconds,1,payload[8],payload[8]]) #add with counter 1
            self.protocol_stats[2] += 1
            self.tSinkCurrent = 0

    def _node_message(self, packet):
        if len(self.messages) > 0: 
            for element in range(len(self.messages)): #check if it's a new message
                if self.messages[element][0] == packet[1]: #we already delivered that one
                    self.messages[element][4] += 1 #increment counter
                    if (packet[8]>self.messages[element][5]): #calculate max and min hops
                        self.messages[element][5]=packet[8]
                    elif (packet[8]<self.messages[element][6]):
                        self.messages[element][6]=packet[8]
                    not_delivered = False
                    break
                else: #new message
                    not_delivered = True
        else: #fresh list, add directly
            not_delivered = True
        if not_delivered:
            self.messages.append([packet[1],packet[2],packet[4],self.Node.simulation_seconds,1,packet[8],packet[8]]) #add with counter 1

    def _forwarder(self, msg):
        'This method forwards a received gossip package to all neighbours'
        'This should be in routing layer'
        start = time.monotonic_ns()/1000000
        msg[7] = []
        addrinfo = socket.getaddrinfo(self.bcast_group, None)[1] #getting the first one [0] is related to stream, [1] dgram and [2] raw
        #addrinfo[0] is the address family, which is same for stream dgram ow raw
        forwarder_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        if (self.net_trans=='SIXLOWPANLINK'):
            ttl_bin = struct.pack('@i', 1) #ttl=1
            forwarder_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        elif (self.net_trans=='ADHOC'):
            forwarder_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if len(self.visible) <= self.fanout_max:
            for node in self.visible:
                msg[7].append(node[0])
        elif len(self.visible) > self.fanout_max:
            fout = random.sample(self.visible, k=self.fanout_max)
            for node in fout:
                msg[7].append(node[0])
        bytes_to_send = json.dumps(msg).encode()
        forwarder_socket.sendto(bytes_to_send, (addrinfo[4][0], self.port))
        self.protocol_stats[1] += 1
        forwarder_socket.close()
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start, self.Node.Battery.tx_time * self.Node.Battery.tx_current)

    def _checkNewMessage(self):
        #this is for sink only
        if (self.tSinkCurrent > self.tSinkMax): #max time withtout new message. Shutdown simulation
            self.Node.lock = False

    def _update_visible(self):
        start = time.monotonic_ns()/1000000
        for member in range(len(self.visible)):
            if (self.Node.simulation_seconds- self.visible[member][1] > self.visible_timeout):
                del self.visible[member]
                break
        self.Node.Battery.computational_energy +=self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start)
     
    def printinfo(self):
        'Prints general information about the node'
        print()
        print("GOSSIP - Routing agent")
        print()
        print("battery level: \t\t{0:5.2f} Joules".format(self.Node.Battery.battery_energy))
        print("battery level: \t\t{0:5.2f} %".format(self.Node.Battery.battery_percent))
        print("local address: \t\t"+str(self.myip))
        print("udp port: \t\t"+str(self.port))
        print("fanout: \t\t"+str(self.fanout_max))
        print("default ttl: \t\t"+str(self.ttl))
        if self.Node.role == 'mote':
            print("msgs created: \t\t"+str(self.protocol_stats[0]))
            print("msgs forwarded: \t"+str(self.protocol_stats[1]))
            print("msgs discarded: \t"+str(self.protocol_stats[3]))
        elif self.Node.role == 'sink':
            print("msgs delivered: \t"+str(self.protocol_stats[2]))
            print("starvation time: \t"+str(self.tSinkCurrent))
            print("starvation max: \t"+str(self.tSinkMax))
        print("Network ratio: \t\t"+str(self.netRatio))
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

    def printvisible(self):
        print("Visible neighbours at:" + str(self.Node.simulation_seconds) )
        print("===============================================================================")
        print("|IP\t\t|Last seen\t|")
        print("-------------------------------------------------------------------------------")
        for member in range(len(self.visible)):
            print ("|"+self.visible[member][0]+"\t|"+str(self.visible[member][1])+"\t\t|")
        print("===============================================================================")
    

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
        self.fanout_max = settings['fan_out_max']
        self.ttl = settings['ttl']

