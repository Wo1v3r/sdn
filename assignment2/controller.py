import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.packet import arp, ethernet
from pox.lib.addresses import EthAddr
from hosts import clients, servers

log = core.getLogger()

clients_mac = list(map(lambda (_,__,mac,___): mac,clients))
clients_ip = list(map(lambda( _,ip,__,___): ip, clients))
servers_ip = list(map(lambda(_,ip,__,___): ip, servers))

load_balancer_mac = '00:00:00:00:00:10'

class Controller (EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)
        self.installed_clients = {}
        self.ipToMac = {}
        self.macToPort = {}

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
        
        log.info(self.macToPort)


    def _handle_PacketIn(self, event):
        packet = event.parsed
        self.macToPort [packet.src] = event.port

        if packet.type == packet.ARP_TYPE:
            log.info("ARP Packet type")

            self.ipToMac [str(packet.payload.protosrc)] =  packet.src

            log.info(self.ipToMac)

            if packet.payload.opcode == arp.REPLY:
                log.info( str(packet.payload.protosrc) + ' wants to reply')

                #server -> client : rewrite src as load balancer
                #client -> server : rewrite src as load balancer
                
                #nice to have: if server -> server : rewrite src as load balancer
                #nice to have: if client -> client : dont touch

                msg = of.ofp_packet_out()
                msg.data = event.ofp
                log.info(str(self.macToPort[packet.dst]))
                msg.actions.append( of.ofp_action_output( port = self.macToPort[packet.dst]) )

                event.connection.send( msg )
                
            if packet.payload.opcode == arp.REQUEST:
                #client -> server : rewrite src as load balancer V
                if str(packet.src) in clients_mac and str(packet.payload.protodst) in servers_ip:
                    log.info('A Client arp req server')
                    arp_reply = arp()
                    arp_reply.opcode = arp.REPLY


                    arp_reply.hwsrc = EthAddr(load_balancer_mac)
                    arp_reply.hwdst = packet.src

                    arp_reply.protosrc = packet.payload.protodst
                    arp_reply.protodst = packet.payload.protosrc

                    ether = ethernet()
                    ether.set_payload(arp_reply)
                    
                    ether.type = ethernet.ARP_TYPE
                    ether.dst = packet.src
                    ether.src = EthAddr(load_balancer_mac)
            
                    log.info('Faking ARP reply for client as loadbalancer')

                    msg = of.ofp_packet_out()
                    msg.data = ether.pack()

                    msg.actions.append( of.ofp_action_output( port = event.port ))
                    event.connection.send( msg )


                    
                elif str(packet.payload.protosrc) in servers_ip:
                    log.info('A Server arp req someone')
                    
                    arp_reply = arp()
                    arp_reply.opcode = arp.REPLY

                    arp_reply.hwsrc = EthAddr(load_balancer_mac)
                    arp_reply.hwdst = packet.src

                    arp_reply.protosrc = packet.payload.protodst
                    arp_reply.protodst = packet.payload.protosrc

                    ether = ethernet()
                    ether.set_payload(arp_reply)
                    
                    ether.type = ethernet.ARP_TYPE
                    ether.dst = packet.src
                    ether.src = EthAddr(load_balancer_mac)
            
                    log.info('Faking ARP reply for server as loadbalancer')

                    msg = of.ofp_packet_out()
                    msg.data = ether.pack()

                    msg.actions.append( of.ofp_action_output( port = event.port ))
                    event.connection.send( msg )

                else:
                    log.info('Flooding: wants to know who is: ' + str(packet.dst))
                    msg = of.ofp_packet_out()
                    msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
                    msg.data = event.ofp
                    event.connection.send(msg)
            
        elif packet.dst in self.macToPort or str(packet.dst) == load_balancer_mac:
            log.info("Sending non ARP packet")
            
            if str(packet.src) in clients_mac and str(packet.dst) == load_balancer_mac:
                #client -> server , choose random server and forward packet
                dstip = str(packet.payload.dstip)
                srcip = str(packet.payload.srcip)                                
                # By installing a rule with 10 sec timeout
                log.info('connecting ' + srcip + ' to ' + dstip +' through load balancer ')
                
                client_server = of.ofp_flow_mod()
                client_server.match.dl_src = packet.src
                client_server.match.dl_dst = load_balancer_mac
                client_server.actions.append(of.ofp_action_output(port = event.port))
                
                event.connection.send(client_server)
            
                # server_client = of.ofp_flow_mod()
                # server_client.match.dl_src = '00:00:00:00:00:05' 
                # server_client.match.dl_dst = load_balancer_mac
                # server_client.actions.append(of.ofp_action_output(port = event.port))
                
                # event.connection.send(server_client)      
            else:
                #client -> client
                msg = of.ofp_packet_out()
                msg.data = event.ofp                
                msg.actions.append( of.ofp_action_output( port = self.macToPort[packet.dst]) )
                event.connection.send( msg )




def launch():
    core.registerNew(Controller)
