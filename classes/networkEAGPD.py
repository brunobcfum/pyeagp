#!/usr/bin/env python3.7

""" 
Router class is part of a dissertation work about WSNs 
"""
__author__ = "Bruno Chianca Ferreira"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Bruno Chianca Ferreira"
__email__ = "brunobcf@gmail.com"

import socket, os, math, struct, sys, json, traceback, zlib, fcntl, threading
import time
from apscheduler.schedulers.background import BackgroundScheduler
from collections import deque

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
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.monitor_mode = False #when this is true a lot of messages polute the screen
        self.protocol_stats = [0,0,0,0,0,0] #created, forwarded, delivered, discarded, digest sent, request attended
        self.errors = [0,0,0]
        self.myip = ''
        #### Protocol specific ####################################################################
        self.ttl = 8
        self.fanout_max = 3
        self.tmax = tmax * Node.second  # Maximum time interval a node can wait until send a message (milliseconds)
        self.tnext = self.tmax # The time interval the local node will wait until forwarding current message (in milliseconds)
        self.bt_level = [] # Battery level in node i (in a range between 1 and 10, where 1 means that remains less than 10% of battery)
        self.v_bt = [] #A vector containing the energy level of all neighbour nodes ## NOT NEEDED IN THIS IMPLEMENTATION
        self.mode = "eager" #1 -> eager, 0 ->lazy Starts lazy, later check if should be changed to eager
        self.netRatio = 0 # ratio -> forwarded / discarded
        self.tSinkMax = 500 #max time sink without new message, after that stop simulation
        self.tSinkCurrent = 0 #current time with no new message
        self.packets = 0
        self.traffic = 0
        self.battery_percent_old = 0
        self.backlog = deque([],5000)
        self.history = deque([],1000)
        self.digest = deque([],1000)
        self.digests_received = deque([],5000)
        ##################### END OF DEFAULT SETTINGS ###########################################################
        self._setup() #Try to get settings from file
        self.t2 = threading.Thread(target=self._listener, args=())
        self.t2.start()
        self.scheduler.add_job(self._digest, 'interval', seconds = (self.tmax * 10) / 1000, id='digest')

    ######## PUBLIC ##############################################################################
    def awake_callback(self):
        'Callback function ran when the node wakes up'
        if (self.Node.role!="sink"):
            if len(self.visible) > 0: #only change state if it has any visible
                self._update_visible() #clean the list of visible
                self.tnext =self._calc_tnext()
                if self.Node.Battery.battery_percent != self.battery_percent_old:
                    self._update_mode()
                    self.battery_percent_old = self.Node.Battery.battery_percent
        else:
            self._checkNewMessage()

    def dispatch(self, payload):
        'Public method available for sending messages. '
        self._sender(payload)

    def shutdown(self):
        'Public method available for shuting down a node'
        self.t2.join(timeout=2)
        self.scheduler.shutdown()

    def printvisible(self):
        'Prints visible nodes'
        print("Visible neighbours at:" + str(self.Node.simulation_seconds) )
        print("===============================================================================")
        print("|IP\t\t|Last seen\t|Battery level")
        print("-------------------------------------------------------------------------------")
        for member in range(len(self.visible)):
            print ("|"+self.visible[member][0]+"\t|"+str(self.visible[member][1])+"\t\t|"+str(self.visible[member][2]))
        print("===============================================================================")

    def printinfo(self):
        'Prints general information about the network layer'
        print()
        print("EAGPD - Routing agent")
        print()
        #print("current value: \t\t{0:5.2f}".format(self.value))
        print("battery level: \t\t{0:5.2f} Joules".format(self.Node.Battery.battery_energy))
        print("battery level: \t\t{0:5.2f} %".format(self.Node.Battery.battery_percent))
        print("average level: \t\t{0:5.2f} 0-100".format(self.average))
        print("node tmax: \t\t" + str(self.tmax/self.Node.multiplier)+ " ms in virtual time")
        print("node tnext: \t\t" + str(self.tnext/self.Node.multiplier)+ " ms in virtual time")
        #print("local address: \t\t"+str(self.myip))
        print("node mode: \t\t" + str(self.mode))
        print("node ttl max: \t\t" + str(self.ttl))
        #print("udp port: \t\t"+str(self.port))
        if self.Node.role == 'mote':
            print("msgs created: \t\t"+str(self.protocol_stats[0]))
            print("msgs forwarded: \t"+str(self.protocol_stats[1]))
            print("msgs discarded: \t"+str(self.protocol_stats[3]))
            print("digests sent: \t\t"+str(self.protocol_stats[4]))
            print("digests buffer: \t"+str(len(self.digest)))
            print("request attended: \t"+str(self.protocol_stats[5]))
            print("msgs buffer: \t\t"+str(len(self.scheduler.get_jobs())))
        elif self.Node.role == 'sink':
            print("msgs delivered: \t"+str(self.protocol_stats[2]))
            print("starvation time: \t"+str(self.tSinkCurrent))
            print("starvation max: \t"+str(self.tSinkMax))
        print("Network ratio: \t\t"+str(self.netRatio))
        print("errors: \t\t" + str(self.errors[0]) + ','+ str(self.errors[1]) + ',' + str(self.errors[2]))
        print()
        print("Network ratio is just the number of discarded messages divided by")
        print("the number of created messages. A node with high ratio is busier.")
        print()

    ######## PRIVATE ##############################################################################
    def _listener(self):
        'This method opens a UDP socket to receive data. It runs in infinite loop as long as the node is up'
        addrinfo = socket.getaddrinfo(self.bcast_group, None)[1]
        listen_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM) #UDP
        listen_socket.bind(('', self.port))
        self.myip = self._get_ip('eth0')
        #self.myip = self._get_ip(str(self.Node.tag)+'-wlan0')
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

    def _sender(self, payload, fasttrack=False):
        'This method sends an epidemic message with the data read by the sensor'
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
        msg_id = zlib.crc32(str((self.Node.simulation_seconds+payload)).encode())
        self.messages_created.append([hex(msg_id),self.Node.simulation_seconds])
        if fasttrack:
            bytes_to_send = json.dumps([4 , hex(msg_id), self.Node.tag, 0, self.Node.simulation_seconds, self.ttl, self.Node.Battery.battery_percent,'',0, payload]).encode()
        else:
            bytes_to_send = json.dumps([2 , hex(msg_id), self.Node.tag, 0, self.Node.simulation_seconds, self.ttl, self.Node.Battery.battery_percent,'',0, payload]).encode()
        sender_socket.sendto(bytes_to_send, (addrinfo[4][0], self.port))
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start, self.Node.Battery.tx_time * self.Node.Battery.tx_current)
        sender_socket.close()

    def _packet_sender(self, packet, fasttrack=False):
        'This method sends an epidemic message with the data read by the sensor'
        start = time.monotonic_ns()/1000000
        addrinfo = socket.getaddrinfo(self.bcast_group, None)[1] 
        sender_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        if (self.net_trans=='SIXLOWPANLINK'):
            ttl_bin  = struct.pack('@i', 1) #ttl=1
            sender_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        elif (self.net_trans=='ADHOC'):
            sender_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if fasttrack:
            bytes_to_send = json.dumps([4 , packet[1], packet[2], packet[3], packet[4], self.ttl, self.Node.Battery.battery_percent,'',packet[8], packet[9]]).encode()
        else:
            bytes_to_send = json.dumps([2 , packet[1], packet[2], packet[3], packet[4], self.ttl, self.Node.Battery.battery_percent,'',packet[8], packet[9]]).encode()
        sender_socket.sendto(bytes_to_send, (addrinfo[4][0], self.port))
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start, self.Node.Battery.tx_time * self.Node.Battery.tx_current)
        sender_socket.close()

    def _packet_handler(self, packet, sender_ip):
        'When a message of type gossip is received from neighbours this method unpacks and handles it'
        start = time.monotonic_ns()/1000000
        packet[5] -= 1 #Dedutc TTL
        packet[8] += 1 #Increase hops
        if (packet[2] != self.Node.tag):
            if len(self.visible) > 0: #list no empty, check if already there
                not_there = 1
                for element in range(len(self.visible)):
                    if sender_ip == self.visible[element][0]: #if there...
                        self.visible[element][1] = self.Node.simulation_seconds # refresh timestamp
                        self.visible[element][2] = packet[6] # refresh battery level
                        not_there = 0
                        break
                if not_there:
                    self.visible.append([sender_ip, self.Node.simulation_seconds, packet[6]])
            else: #Empty neighbours list, add 
                self.visible.append([sender_ip, self.Node.simulation_seconds, packet[6]])
            if self.Node.role == "sink":
                self._sink(packet)
            else:
                self._node_message(packet)
                if packet[5] <= 0: #check if ttl is over
                    self.protocol_stats[3] +=1
                elif packet[7] != self.myip: #check if came from me before
                    packet[7] = sender_ip
                    if packet[0] == 3: #is it a request?
                        for id in packet[9]:
                            for message in self.backlog:
                                if id in message:
                                    #print(id + " id and message: " + str(message))
                                    self.protocol_stats[5] +=1
                                    self._packet_sender(message, fasttrack=False)
                                    self.backlog.remove(message)
                                    break
                    if (packet[0] == 1): #is it a digest?
                        if packet[1] not in self.digests_received:
                            self.digests_received.append(packet[1])
                            request = []
                            for id in packet[9]:
                                for message in self.history:
                                    if id in message:
                                        break
                                else:
                                    request.append(id)
                            if (len(request) > 0):
                                self._send_request(request)
                                if self.monitor_mode: print("sent a request with size: " + str(len(request)))
                            self._forwarder(packet)
                            return
                    if packet[0] == 4: #fasttrack, send it pronto
                        self._forwarder(packet)
                    else:
                        if self.mode == 'eager':
                            try:
                                self.scheduler.remove_job(packet[1])
                                self.protocol_stats[3] +=1
                            except:
                                self.scheduler.add_job(self._forwarder, 'interval', seconds = self.tnext/1000, id=packet[1], args=[packet])
                                pass
                        elif self.mode == 'lazy':
                            try:
                                self.scheduler.remove_job(packet[1])
                                self.protocol_stats[3] +=1
                                if packet[0] == 2:
                                    if packet[8] <= self.ttl:
                                        self.backlog.append(packet)
                                        self.digest.append(packet[1])
                            except:
                                self.scheduler.add_job(self._forwarder, 'interval', seconds = self.tnext/1000, id=packet[1], args=[packet])
                                pass
                else:
                    self.protocol_stats[3] +=1
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(0, start, self.Node.Battery.rx_current * self.Node.Battery.rx_time)
        self.Node.Battery.computational_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start)

    def _sink(self, packet):
        'Handles messages received at the sink'
        # This method does not use energy, only for simulation statistics
        if (packet[0] == 1):
            if packet[1] not in self.digests_received:
                self.digests_received.append(packet[1])
                request = []
                for id in packet[9]:
                    for message in self.messages_delivered:
                        if id in message:
                            break
                    else:
                        request.append(id)
                if (len(request) > 0):
                    self._send_request(request)
                    if self.monitor_mode: print("sent a request with size: " + str(len(request)))
                return
            else: return
        elif (packet[0] == 3):
            return
        if len(self.messages_delivered) > 0: 
            for element in range(len(self.messages_delivered)): #check if it's a new message
                if self.messages_delivered[element][0] == packet[1]: #we already delivered that one
                    self.messages_delivered[element][4] += 1 #increment counter
                    if (packet[8]>self.messages_delivered[element][5]): #calculate max and min hops
                        self.messages_delivered[element][5]=packet[8]
                    elif (packet[8]<self.messages_delivered[element][6]):
                        self.messages_delivered[element][6]=packet[8]
                    self.protocol_stats[2] += 1
                    not_delivered = False
                    break
                else: #new message
                    not_delivered = True
        else: #fresh list, add directly
            not_delivered = True
        if not_delivered:
            self.messages_delivered.append([packet[1],packet[2],packet[4],self.Node.simulation_seconds,1,packet[8],packet[8]]) #add with counter 1
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
            self.history.append(packet[1])
            self.messages.append([packet[1],packet[2],packet[4],self.Node.simulation_seconds,1,packet[8],packet[8]]) #add with counter 1

    def _forwarder(self, packet):
        'This method forwards a received gossip package to all neighbours'
        start = time.monotonic_ns()/1000000
        addrinfo = socket.getaddrinfo(self.bcast_group, None)[1] #getting the first one [0] is related to stream, [1] dgram and [2] raw
        #addrinfo[0] is the address family, which is same for stream dgram ow raw
        forwarder_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        if (self.net_trans=='SIXLOWPANLINK'):
            ttl_bin = struct.pack('@i', 1) #ttl=1
            forwarder_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        elif (self.net_trans=='ADHOC'):
            forwarder_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        bytes_to_send = json.dumps([packet[0] , packet[1], packet[2], packet[3], packet[4], packet[5], self.Node.Battery.battery_percent, packet[7], packet[8], packet[9]]).encode()
        forwarder_socket.sendto(bytes_to_send, (addrinfo[4][0], self.port))
        self.protocol_stats[1] += 1
        forwarder_socket.close()
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start, self.Node.Battery.tx_time * self.Node.Battery.tx_current)
        try:
            self.scheduler.remove_job(packet[1])
        except:
            if self.monitor_mode == True: print("FWD - Issue trying to remove fwd task")
            self.errors[2] += 1
            pass

    def _digest(self):
        start = time.monotonic_ns()/1000000
        if len(self.digest) < 1: #do nothing if there is no digest
            return
        addrinfo = socket.getaddrinfo(self.bcast_group, None)[1] 
        digest_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        if (self.net_trans=='SIXLOWPANLINK'):
            ttl_bin = struct.pack('@i', 1) #ttl=1
            digest_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        elif (self.net_trans=='ADHOC'):
            digest_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg_id = zlib.crc32(str((self.Node.simulation_seconds)).encode())
        bytes_to_send = json.dumps([1 , hex(msg_id), self.Node.tag, 0, self.Node.simulation_seconds, self.ttl, self.Node.Battery.battery_percent,'',0, list(self.digest)]).encode()
        self.digest.clear()
        digest_socket.sendto(bytes_to_send, (addrinfo[4][0], self.port))
        self.protocol_stats[4] += 1
        digest_socket.close()
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start, self.Node.Battery.tx_time * self.Node.Battery.tx_current)

    def _send_request(self, request):
        start = time.monotonic_ns()/1000000
        addrinfo = socket.getaddrinfo(self.bcast_group, None)[1] 
        request_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
        if (self.net_trans=='SIXLOWPANLINK'):
            ttl_bin = struct.pack('@i', 1) #ttl=1
            request_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
        elif (self.net_trans=='ADHOC'):
            request_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg_id = zlib.crc32(str((self.Node.simulation_seconds)).encode())
        bytes_to_send = json.dumps([3 , hex(msg_id), self.Node.tag, 0, self.Node.simulation_seconds, self.ttl, self.Node.Battery.battery_percent,'',0, request]).encode()
        request_socket.sendto(bytes_to_send, (addrinfo[4][0], self.port))
        #self.protocol_stats[4] += 1
        request_socket.close()
        self.Node.Battery.communication_energy += self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start, self.Node.Battery.tx_time * self.Node.Battery.tx_current)

    def _checkNewMessage(self):
        'Just to check if sink is still receiving messages, if not ends simulation'
        #this is for sink only
        if (self.tSinkCurrent > self.tSinkMax): #max time withtout new message. Shutdown simulation
            self.Node.lock = False

    def _update_visible(self):
        'Update the energy state for local cluster. Old nodes are removed and local average recalculated'
        start = time.monotonic_ns()/1000000
        for member in range(len(self.visible)):
            if (self.Node.simulation_seconds- self.visible[member][1] > self.visible_timeout):
                del self.visible[member]
                break
        self.average = 0
        self.n_vis = len(self.visible)
        self.bmax = self.Node.Battery.battery_percent
        self.bmin = self.Node.Battery.battery_percent
        for member in range(self.n_vis):
            self.average += self.visible[member][2]
            if self.visible[member][2] > self.bmax:
                self.bmax = self.visible[member][2] #when bmax is 0, this should always happen
            elif self.visible[member][2] < self.bmin:
                self.bmin = self.visible[member][2] #
        if self.n_vis > 0:
            self.average = round(self.average / (self.n_vis))
        else:
            self.average = self.Node.Battery.battery_percent
        self.Node.Battery.computational_energy +=self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start)

    def _update_mode(self):
        'Update eager/lazy push modes'
        start = time.monotonic_ns()/1000000
        try: 
            self.netRatio = self.protocol_stats[3] / self.protocol_stats[1]
        except:
            self.netRatio = 1
        if (self.Node.Battery.battery_percent >= self.average):
            self.mode = "eager"
        else:
            self.mode = "lazy"
        self.Node.Battery.computational_energy +=self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start)

    def _calc_tnext(self):
        'Calculate tnext for a eager node'
        start = time.monotonic_ns()/1000000
        self.tnext = self.tmax
        if self.mode == "eager":
            if (self.bmax != self.bmin):
                self.tnext = self.tmax - (self.tmax * (self.Node.Battery.battery_percent-self.bmin) / (self.bmax-self.bmin))
            if self.tnext == 0:
                self.tnext = 50
        self.Node.Battery.computational_energy +=self.Node.Battery.battery_drainer(self.Node.Battery.modemSleep_current, start)
        return self.tnext

    def _get_ip(self,iface = 'eth0'):
        'Gets ip address'
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
        'Initial setup'
        settings_file = open("settings.json","r").read()
        settings = json.loads(settings_file)
        self.tSinkMax = settings['sink_starvation'] 
        self.fanout_max = settings['fan_out_max']
        self.ttl = settings['ttl']




