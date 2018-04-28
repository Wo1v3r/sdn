import pox.openflow.libopenflow_01 as of
import random
from pox.core import core
from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.packet import arp, ethernet
from pox.lib.addresses import EthAddr, IPAddr
from hosts import clients, servers

log = core.getLogger()

clients_mac = list(map(lambda (_,__,mac,___): EthAddr(mac),clients))
clients_ip = list(map(lambda( _,ip,__,___): ip, clients))
servers_ip = list(map(lambda(_,ip,__,___): ip, servers))

LOAD_BALANCER_MAC = EthAddr('00:00:00:00:00:10')
LOAD_BALANCER_IP = IPAddr('10.0.0.10')

class Controller (EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)
        self.installed_clients = {}
        self.ipToMac = {}
        self.macToPort = {}
        # result list, symbols for the $place of host -> h5,h6,h7,h8
        self.results = [0,0,0,0]

    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.info("Connection up event for: " + dpid)
        log.info(servers_ip)

        log.info('Installing servers to be ready for load balancing')
        
        def installServer((name,ip,mac,port)):
            log.info('Installing ' + name)
            self.ipToMac[ip] = mac
            self.macToPort[mac] = port

        map(installServer, servers)

    def _handle_PacketIn(self, event):
        print('current results: ', self.results)
        packet = event.parsed
        self.macToPort [packet.src] = event.port

        if packet.type == packet.ARP_TYPE:
            log.info("ARP Packet type")
            log.info('from ' + str(packet.next.protosrc) + ' to ' + str(packet.next.protodst))
            self.ipToMac [str(packet.payload.protosrc)] =  packet.src

            #client -> server : rewrite src as load balancer V
            if packet.next.protodst == LOAD_BALANCER_IP:
                log.info('A Client arp req server')
                
                # Get the ARP request from packet
                arp_req = packet.next

                # Create ARP reply
                arp_rep = arp()
                arp_rep.opcode = arp.REPLY
                arp_rep.hwsrc = LOAD_BALANCER_MAC    
                arp_rep.hwdst = arp_req.hwsrc    
                arp_rep.protosrc = LOAD_BALANCER_IP
                arp_rep.protodst = arp_req.protosrc

                # Create the Ethernet packet
                ether = ethernet()
                ether.type = ethernet.ARP_TYPE
                ether.dst = packet.src
                ether.src = LOAD_BALANCER_MAC
                ether.set_payload(arp_rep)

                log.info('Faking ARP reply for client as loadbalancer')
                # Send the ARP reply to client
                msg = of.ofp_packet_out()
                msg.data = ether.pack()
                msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
                msg.in_port = event.port
                event.connection.send(msg)    
            
            elif packet.next.protodst in clients_ip:
                # flooding between clients
                log.info(' ' + str(packet.src) + ' Flooding: wants to know who is: ' + str(packet.dst))
                msg = of.ofp_packet_out()
                msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
                msg.data = event.ofp
                event.connection.send(msg)
            elif packet.dst not in clients_ip:
                msg = of.ofp_packet_out()
                log.info(packet.payload.protosrc)
                msg.actions.append(of.ofp_action_output(port = self.macToPort[self.ipToMac[str(packet.next.protodst)]]))
                msg.data = event.ofp
                msg.in_port = event.port
                event.connection.send(msg)  
            
        elif packet.type == packet.IP_TYPE:
            log.info("Sending non ARP packet")
            self.ipToMac [str(packet.next.srcip)] =  packet.src
            
            if packet.dst == LOAD_BALANCER_MAC:
                #client -> server , choose random server and create rule
                server_num = random.randint(0,3)
                self.results[server_num] = self.results[server_num] + 1
                server_ip = servers_ip[server_num]
                server_mac = self.ipToMac[server_ip]
                server_port = self.macToPort[server_mac]
                server_ip = IPAddr(server_ip)
                server_mac = EthAddr(server_mac)

                msg = of.ofp_flow_mod()
                msg.idle_timeout = 1
                msg.hard_timeout = 10
                msg.buffer_id = None

                msg.match.in_port = server_port
                msg.match.dl_src = server_mac
                msg.match.dl_dst = packet.src
                msg.match.dl_type = ethernet.IP_TYPE
                msg.match.nw_src = server_ip
                msg.match.nw_dst = packet.next.srcip

                msg.actions.append(of.ofp_action_nw_addr.set_src(LOAD_BALANCER_IP))
                msg.actions.append(of.ofp_action_dl_addr.set_src(LOAD_BALANCER_MAC))
                msg.actions.append(of.ofp_action_output(port = event.port))

                event.connection.send(msg)

                # install the forward rule from client to server + forward packet
                msg = of.ofp_flow_mod()
                msg.idle_timeout = 1
                msg.hard_timeout = 10
                msg.buffer_id = None
                msg.data = event.ofp

                msg.match.in_port = event.port
                msg.match.dl_src = packet.src
                msg.match.dl_dst = LOAD_BALANCER_MAC
                msg.match.dl_type = ethernet.IP_TYPE
                msg.match.nw_src = packet.next.srcip
                msg.match.nw_dst = LOAD_BALANCER_IP
                
                msg.actions.append(of.ofp_action_nw_addr.set_dst(server_ip))
                msg.actions.append(of.ofp_action_dl_addr.set_dst(server_mac))
                msg.actions.append(of.ofp_action_output(port = server_port))

                event.connection.send(msg)

                log.info("Installing %s with %s" % (packet.next.srcip, server_ip))
     
            elif EthAddr(packet.dst) in clients_mac:
                #client -> client
                if EthAddr(packet.dst) not in self.macToPort:
                    #flooding
                    msg = of.ofp_packet_out()
                    msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
                    msg.data = event.ofp
                    event.connection.send(msg)
                else:
                    #client already discovered
                    msg = of.ofp_flow_mod()
                    msg.idle_timeout = 10
                    msg.hard_timeout = 30
                    msg.match = of.ofp_match.from_packet(packet, event.port)
                    msg.actions.append(of.ofp_action_output(port = self.macToPort[EthAddr(packet.dst)]))
                    msg.data = event.ofp
                    msg.in_port = event.port
                    event.connection.send(msg)

def launch():
    core.registerNew(Controller)
